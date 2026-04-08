#!/usr/bin/env nextflow

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    biodiv-workflow
    ---------------
    Enriches the Belege_aus_D herbarium CSV by:
      1. Annotating each record with the BiodivPortal Annotator API
         (uses FullNameCache — species name — as annotation text)
      2. Classifying each record with the local Land Taxonomy Classifier
         (uses FundortUNdOeko or Locality — habitat text — as classification text)
      3. Merging both outputs back into an enriched CSV

    Usage:
        nextflow run main.nf --input assets/Belege_aus_D.csv --outdir results/

    Quick smoke-test (first 100 rows only):
        nextflow run main.nf --input assets/Belege_aus_D.csv \\
            --max_records 100 --outdir results_test/

    Pre-convert the source file first (one-time step):
        python bin/convert_xlsx.py \\
            --input  assets/Belege_aus_D_2.csv \\
            --output assets/Belege_aus_D.csv \\
            --skip-empty-land
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

nextflow.enable.dsl = 2

// ----------------------------------------------------------------------------
// Import modules
// ----------------------------------------------------------------------------
include { BIODIV_ANNOTATE } from './modules/local/biodiv_annotate/main'
include { LAND_CLASSIFY   } from './modules/local/land_classify/main'

// ----------------------------------------------------------------------------
// Print pipeline header
// ----------------------------------------------------------------------------
log.info """
    ╔══════════════════════════════════════════╗
    ║       BiodivPortal Enrichment Workflow   ║
    ║       (Belege_aus_D herbarium records)   ║
    ╚══════════════════════════════════════════╝
    input            : ${params.input}
    outdir           : ${params.outdir}
    id_column        : ${params.id_column}
    land_text_column : ${params.land_text_column}
    biodiv_text_col  : ${params.biodiv_text_column}
    max_records      : ${params.max_records ?: 'all'}
    annotator        : ${params.biodivportal_url}
    classifier       : ${params.land_classifier_url}
    ──────────────────────────────────────────
""".stripIndent()

// ----------------------------------------------------------------------------
// Validate required parameters
// ----------------------------------------------------------------------------
if (!params.input) {
    error "ERROR: Please provide an input CSV with --input <path/to/file.csv>"
}

// ----------------------------------------------------------------------------
// Main workflow
// ----------------------------------------------------------------------------
workflow {

    // --- Step 1: Parse CSV rows → (id, text_land, text_biodiv) channel ---
    Channel.fromPath(params.input, checkIfExists: true)
        .splitCsv(header: true, sep: ',', strip: true)
        .map { row ->
            def id          = row[params.id_column]?.trim()
            def text_land   = row[params.land_text_column]?.trim()
            def text_biodiv = row[params.biodiv_text_column]?.trim()

            if (!id) {
                log.warn "Skipping row with missing '${params.id_column}': ${row}"
                return null
            }
            // Allow empty texts — services will return graceful errors
            return tuple(id, text_land ?: "", text_biodiv ?: "")
        }
        .filter { it != null }
        .set { records_ch }

    // Apply optional row limit (useful for testing)
    def limited_ch = params.max_records
        ? records_ch.take(params.max_records as int)
        : records_ch

    // --- Step 2: Split into separate channels per service ---
    limited_ch
        .multiMap { id, text_land, text_biodiv ->
            for_land:   tuple(id, text_land)
            for_biodiv: tuple(id, text_biodiv)
        }
        .set { split_ch }

    // --- Step 3: Run annotation and classification in parallel ---
    BIODIV_ANNOTATE(split_ch.for_biodiv)
    LAND_CLASSIFY(split_ch.for_land)

    // --- Step 4: Merge per-row JSONs back into one enriched CSV ---
    // Pass --max-rows so merge_results.py only reads the rows that were
    // actually processed (prevents 109k empty rows when max_records is set).
    MERGE_RESULTS(
        Channel.fromPath(params.input),
        BIODIV_ANNOTATE.out.annotations.map { id, f -> f }.collect(),
        LAND_CLASSIFY.out.classifications.map { id, f -> f }.collect()
    )
}

// ----------------------------------------------------------------------------
// Process: merge all per-row JSON files into one enriched CSV
// ----------------------------------------------------------------------------
process MERGE_RESULTS {

    publishDir "${params.outdir}", mode: 'copy'

    input:
    path original_csv
    path biodiv_jsons
    path land_jsons

    output:
    path 'enriched_dataset.csv', emit: enriched

    script:
    def max_arg = params.max_records ? "--max-rows ${params.max_records}" : ""
    """
    ${params.python_bin} ${projectDir}/bin/merge_results.py \\
        --input      '${original_csv}' \\
        --sep        ',' \\
        --biodiv-dir . \\
        --land-dir   . \\
        --id-column  '${params.id_column}' \\
        ${max_arg} \\
        --output     'enriched_dataset.csv'
    """
}
