/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    MODULE: BIODIV_ANNOTATE
    Calls the BiodivPortal Annotator REST API for a single record.
    Input:  tuple(id, text_biodiv)   — text_biodiv = FullNameCache (species name)
    Output: tuple(id, *.biodiv.json)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

process BIODIV_ANNOTATE {

    tag "$sample_id"
    label 'process_single'

    input:
    tuple val(sample_id), val(text)

    output:
    tuple val(sample_id), path("${sample_id}.biodiv.json"), emit: annotations

    script:
    def apikey_arg     = params.biodivportal_apikey     ? "--apikey '${params.biodivportal_apikey}'"         : ""
    def ontologies_arg = params.biodivportal_ontologies ? "--ontologies '${params.biodivportal_ontologies}'" : ""
    """
    ${params.python_bin} ${projectDir}/bin/call_annotator.py \\
        --id   '${sample_id}' \\
        --text '${text.replaceAll("'", "\\\\'")}' \\
        --url  '${params.biodivportal_url}' \\
        ${apikey_arg} \\
        ${ontologies_arg} \\
        --output '${sample_id}.biodiv.json'
    """
}
