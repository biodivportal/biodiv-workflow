# BiodivPortal Enrichment Workflow

A [Nextflow](https://www.nextflow.io/) workflow that enriches the **Belege_aus_D** herbarium dataset (or any compatible CSV) by calling two biodiversity services in parallel and merging the results into a single enriched CSV.

---

## What This Workflow Does

```
Belege_aus_D.csv  (HerbariumID, Locality, FullNameCache, …)
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
 BIODIV_ANNOTATE                         LAND_CLASSIFY
 text = FullNameCache                    text = Locality
 → ontology class annotations            → CORINE Land Cover categories
        │                                      │
        └─────────────────┬────────────────────┘
                          ▼
                  MERGE_RESULTS
                  → enriched_dataset.csv
```

Each record is processed with **different text per service**:

| Service | Column | Content |
|---|---|---|
| **BiodivPortal Annotator** | `FullNameCache` | Scientific species name |
| **Land Taxonomy Classifier** | `Locality` | Collection site / habitat description |

Both calls run **in parallel** per record.

---

## Project Structure

```
biodiv-workflow/
├── main.nf                          # Workflow: PARSE_INPUT → BIODIV_ANNOTATE + LAND_CLASSIFY → MERGE_RESULTS
├── nextflow.config                  # Parameters and execution profiles
├── nextflow_schema.json             # nf-core parameter schema
├── INSTALL.md                       # Step-by-step installation guide
├── README.md                        # This file
│
├── bin/
│   ├── parse_input.py               # Safely parses input CSV → TSV for Nextflow
│   ├── call_annotator.py            # Calls BiodivPortal Annotator API
│   ├── call_land_taxonomy.py        # Calls Land Taxonomy Classifier API
│   ├── merge_results.py             # Merges per-row JSON results → enriched CSV
│   └── convert_xlsx.py              # One-time utility: flattens Belege_aus_D_2.csv source format
│
└── assets/
    ├── Belege_aus_D_2.csv           # Original source file (semicolon-delimited, ~109k records)
    ├── Belege_aus_D.csv             # Pipeline-ready CSV (produced by convert_xlsx.py)
    └── test_20.csv                  # 20-row test subset (same format as Belege_aus_D.csv)
```

---

## Preparing the Input

The pipeline reads the **Belege_aus_D.csv** directly using the original column names. No renaming is needed.

Required columns:

| Column | Description |
|---|---|
| `HerbariumID` | Unique record identifier |
| `Locality` | Collection site description — used by the Land Taxonomy Classifier |
| `FullNameCache` | Scientific species name — used by the BiodivPortal Annotator |

The source file (`Belege_aus_D_2.csv`) has an unusual format (semicolon-delimited outer CSV with full CSV strings packed into column 1). Convert it once with:

```bash
python bin/convert_xlsx.py \
    --input  assets/Belege_aus_D_2.csv \
    --output assets/Belege_aus_D.csv
```

This produces a standard comma-delimited CSV with the original 23 column names intact.

---

## Quick Start

> **Before running**, complete [INSTALL.md](INSTALL.md) and start the **land-taxonomy-classifier** service.

### 1. Start the local classifier (separate terminal)

```bash
cd land-taxonomy-classifier
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Smoke-test with 5 records

```bash
nextflow run main.nf -profile test
```

Results are written to `test_results/enriched_dataset.csv`.

### 3. Full run

```bash
nextflow run main.nf \
    --input assets/Belege_aus_D.csv \
    --outdir results/ \
    --biodivportal_apikey YOUR_KEY
```

---

## Output Format

`enriched_dataset.csv` contains all original input columns plus:

| New Column | Description |
|---|---|
| `biodiv_annotation_count` | Number of ontology annotations found |
| `biodiv_top_classes` | Top-3 matched class labels (semicolon-separated) |
| `biodiv_top_ontologies` | Top-3 matched ontology acronyms |
| `land_top_code` | CORINE Land Cover code of the best match |
| `land_top_name` | Name of the best land cover category |
| `land_top_confidence` | Confidence score (0.0 – 1.0) |
| `land_top_reasoning` | LLM explanation for the classification |
| `land_all_classifications` | Full JSON with all top-k results |
| `annotation_error` | `True` if the annotator call failed |
| `classification_error` | `True` if the classifier call failed |

---

## Configuration

All parameters can be set in `nextflow.config` or passed on the command line.

| Parameter | Default | Description |
|---|---|---|
| `--input` | *(required)* | Path to input CSV |
| `--outdir` | `results` | Output directory |
| `--id_column` | `HerbariumID` | ID column name |
| `--land_text_column` | `Locality` | Text column for Land Taxonomy Classifier |
| `--biodiv_text_column` | `FullNameCache` | Text column for BiodivPortal Annotator |
| `--max_records` | *(all)* | Stop after N records (useful for testing) |
| `--biodivportal_url` | `https://data.biodivportal.gfbio.org` | BiodivPortal base URL |
| `--biodivportal_apikey` | *(empty)* | BiodivPortal API key |
| `--biodivportal_ontologies` | *(empty)* | Restrict to specific ontologies |
| `--land_classifier_url` | `http://127.0.0.1:8000` | Land classifier base URL |
| `--land_classifier_top_k` | `5` | Number of classifications to return |
| `--land_classifier_model` | `gpt-4o-mini` | OpenAI model for the classifier |
| `--email` | *(empty)* | Email address for completion notification |

---

## Execution Profiles

| Profile | Description |
|---|---|
| *(default)* | Local execution without Docker |
| `docker` | Local execution using Docker containers |
| `singularity` | Execution using Singularity containers |
| `test` | 5-record test run using `assets/test_20.csv` |

```bash
nextflow run main.nf -profile test                    # quick smoke-test
nextflow run main.nf -profile docker --input ...      # with Docker
nextflow run main.nf --input assets/Belege_aus_D.csv  # full run, no container
```

---

## Services Used

### BiodivPortal Annotator
- **URL:** https://data.biodivportal.gfbio.org
- **Endpoint:** `GET /annotator?text=<text>&apikey=<key>&include=prefLabel`
- **Input text:** `FullNameCache` — scientific species name
- **API key:** Register free at https://biodivportal.gfbio.org/account

### Land Taxonomy Classifier
- **Repository:** https://github.com/biodivportal/land-taxonomy-classifier
- **Endpoint:** `POST /classify` with `{"text": "...", "top_k": 5}`
- **Input text:** `Locality` — collection site / habitat description
- **Requirements:** Local installation + OpenAI API key (see [INSTALL.md](INSTALL.md))

---

## Requirements

- Nextflow ≥ 23.04
- Java 17+
- Python 3.10+
- OpenAI API key (for the land-taxonomy-classifier)
- BiodivPortal API key (register free at biodivportal.gfbio.org/account)
- Docker or Singularity (optional, for container profiles)

See [INSTALL.md](INSTALL.md) for complete setup instructions.
