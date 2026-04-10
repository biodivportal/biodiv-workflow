// BiodivPortal Enrichment Workflow
//
// Enriches herbarium records (Belege_aus_D) by:
// (1) Annotating species names via the BiodivPortal Annotator API
// (2) Classifying habitat/locality text via the Land Taxonomy Classifier
// (3) Merging both outputs into a single enriched CSV
//
// Pre-convert the source file once before running:
//   python bin/convert_xlsx.py --input assets/Belege_aus_D_2.csv \
//       --output assets/Belege_aus_D.csv --skip-empty-land
//
// Usage:
//   nextflow run main.nf --input assets/Belege_aus_D.csv --outdir results/


// ---------------------------------------------------------------------------
// Process: Annotate species names via BiodivPortal Annotator API
// Input:  tuple(id, text_biodiv)  — FullNameCache (scientific species name)
// Output: <id>.biodiv.json
// ---------------------------------------------------------------------------
process BIODIV_ANNOTATE {
    tag "${sample_id}"
    container "python:3.11-slim"
    shell '/bin/bash', '-euo', 'pipefail'

    input:
    tuple val(sample_id), val(text)

    output:
    tuple val(sample_id), path("${sample_id}.biodiv.json"), emit: annotations

    script:
    def apikey_arg     = params.biodivportal_apikey     ? "--apikey '${params.biodivportal_apikey}'"         : ""
    def ontologies_arg = params.biodivportal_ontologies ? "--ontologies '${params.biodivportal_ontologies}'" : ""
    def safe_text      = text.replaceAll("'", "\\'")
    """
    python3 ${projectDir}/bin/call_annotator.py \
        --id   '${sample_id}' \
        --text '${safe_text}' \
        --url  '${params.biodivportal_url}' \
        ${apikey_arg} \
        ${ontologies_arg} \
        --output '${sample_id}.biodiv.json'
    """
}


// ---------------------------------------------------------------------------
// Process: Classify habitat text via local Land Taxonomy Classifier
// Input:  tuple(id, text_land)  — FundortUNdOeko or Locality
// Output: <id>.land.json
// ---------------------------------------------------------------------------
process LAND_CLASSIFY {
    tag "${sample_id}"
    container "python:3.11-slim"
    shell '/bin/bash', '-euo', 'pipefail'

    input:
    tuple val(sample_id), val(text)

    output:
    tuple val(sample_id), path("${sample_id}.land.json"), emit: classifications

    script:
    def safe_text = text.replaceAll("'", "\\'")
    """
    python3 ${projectDir}/bin/call_land_taxonomy.py \
        --id    '${sample_id}' \
        --text  '${safe_text}' \
        --url   '${params.land_classifier_url}' \
        --top-k ${params.land_classifier_top_k} \
        --model '${params.land_classifier_model}' \
        --output '${sample_id}.land.json'
    """
}


// ---------------------------------------------------------------------------
// Process: Merge per-record JSON results back into one enriched CSV
// ---------------------------------------------------------------------------
process MERGE_RESULTS {
    container "python:3.11-slim"
    shell '/bin/bash', '-euo', 'pipefail'
    publishDir params.outdir, mode: 'copy'

    input:
    path original_csv
    path biodiv_jsons
    path land_jsons

    output:
    path 'enriched_dataset.csv', emit: enriched

    script:
    def max_arg = params.max_records ? "--max-rows ${params.max_records}" : ""
    """
    python3 ${projectDir}/bin/merge_results.py \
        --input      '${original_csv}' \
        --sep        ',' \
        --biodiv-dir . \
        --land-dir   . \
        --id-column  '${params.id_column}' \
        ${max_arg} \
        --output     'enriched_dataset.csv'
    """
}


// ---------------------------------------------------------------------------
// Completion handler
// ---------------------------------------------------------------------------
workflow.onComplete {
    def msg = """\
        Workflow execution summary
        --------------------------
        Pipeline    : ${workflow.scriptName}
        Run         : ${workflow.runName}
        Commandline : ${workflow.commandLine}
        Start       : ${workflow.start}
        Completed   : ${workflow.complete}
        Duration    : ${workflow.duration}
        Success     : ${workflow.success ? 'OK' : 'FAILED'}
        workDir     : ${workflow.workDir}
        Exit status : ${workflow.exitStatus}
        Error       : ${workflow.errorMessage ?: '-'}
        Container   : ${workflow.containerEngine ?: 'none'}
        Nextflow    : ${nextflow.version}
        """.stripIndent()

    if (params.email?.trim()) {
        sendMail(
            to:      params.email,
            from:    params.mailfrom,
            subject: "BiodivPortal Enrichment Workflow: ${workflow.success ? 'completed' : 'FAILED'}",
            body:    msg
        )
    }
}


// ---------------------------------------------------------------------------
// Process: parse input CSV using Python (handles quoted commas correctly)
// ---------------------------------------------------------------------------
process PARSE_INPUT {
    container "python:3.11-slim"

    input:
    path csv_file

    output:
    path 'records.tsv', emit: records

    script:
    def max_arg = params.max_records ? "--max-rows ${params.max_records}" : ""
    """
    python3 ${projectDir}/bin/parse_input.py \
        --input      '${csv_file}' \
        --id-col     '${params.id_column}' \
        --land-col   '${params.land_text_column}' \
        --biodiv-col '${params.biodiv_text_column}' \
        ${max_arg} \
        --output     records.tsv
    """
}


// ---------------------------------------------------------------------------
// Main workflow
// ---------------------------------------------------------------------------
workflow {

    // Parse CSV with Python (avoids Nextflow splitCsv column-shift bug on quoted commas)
    PARSE_INPUT(Channel.fromPath(params.input, checkIfExists: true))

    PARSE_INPUT.out.records
        .splitCsv(header: true, sep: '\t')
        .map { row -> tuple(row.id, row.text_land ?: "", row.text_biodiv ?: "") }
        .set { limited_ch }

    // Route each record to the right service
    limited_ch
        .multiMap { id, text_land, text_biodiv ->
            for_land:   tuple(id, text_land)
            for_biodiv: tuple(id, text_biodiv)
        }
        .set { ch }

    // Run annotation and classification in parallel
    BIODIV_ANNOTATE(ch.for_biodiv)
    LAND_CLASSIFY(ch.for_land)

    // Merge results
    MERGE_RESULTS(
        Channel.fromPath(params.input),
        BIODIV_ANNOTATE.out.annotations.map { id, f -> f }.collect(),
        LAND_CLASSIFY.out.classifications.map { id, f -> f }.collect()
    )
}
