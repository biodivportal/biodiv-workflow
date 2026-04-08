/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    MODULE: LAND_CLASSIFY
    Calls the local Land Taxonomy Classifier FastAPI service for a single record.
    Input:  tuple(id, text_land)   — text_land = FundortUNdOeko or Locality
    Output: tuple(id, *.land.json)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

process LAND_CLASSIFY {

    tag "$sample_id"
    label 'process_single'

    input:
    tuple val(sample_id), val(text)

    output:
    tuple val(sample_id), path("${sample_id}.land.json"), emit: classifications

    script:
    """
    ${params.python_bin} ${projectDir}/bin/call_land_taxonomy.py \\
        --id    '${sample_id}' \\
        --text  '${text.replaceAll("'", "\\\\'")}' \\
        --url   '${params.land_classifier_url}' \\
        --top-k ${params.land_classifier_top_k} \\
        --model '${params.land_classifier_model}' \\
        --output '${sample_id}.land.json'
    """
}
