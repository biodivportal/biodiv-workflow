# BiodivPortal Enrichment Workflow

A [Nextflow](https://www.nextflow.io/) workflow that enriches the **Belege_aus_D** herbarium dataset (or any compatible CSV) by calling two biodiversity services in parallel and merging the results into a single enriched CSV.

---

## What This Workflow Does

```
Belege_aus_D.csv  (id, text_land, text_biodiv, …)
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
 BIODIV_ANNOTATE                         LAND_CLASSIFY
 text = text_biodiv (FullNameCache)      text = text_land (FundortUNdOeko / Locality)
 → ontology class annotations            → CORINE Land Cover categories
        │                                      │
        └─────────────────┬────────────────────┘
                          ▼
                  MERGE_RESULTS
                  → enriched_dataset.csv
```

Each record is processed with **different text per service**:

| Service | Text column | Content |
|---|---|---|
| **BiodivPortal Annotator** | `text_biodiv` | `FullNameCache` — scientific species name |
| **Land Taxonomy Classifier** | `text_land` | `FundortUNdOeko` (ecological description) or `Locality` as fallback |

Both calls run **in parallel** per record.

---

## Project Structure

```
biodiv-workflow/
├── main.nf                          # Main workflow definition
├── nextflow.config                  # Parameters and execution profiles
├── INSTALL.md                       # Step-by-step installation guide
├── README.md                        # This file
│
├── modules/
│   └── local/
│       ├── biodiv_annotate/
│       │   └── main.nf              # BIODIV_ANNOTATE process
│       └── land_classify/
│           └── main.nf              # LAND_CLASSIFY process
│
├── bin/
│   ├── convert_xlsx.py              # One-time utility: converts source file → pipeline CSV
│   ├── call_annotator.py            # Calls BiodivPortal Annotator API
│   ├── call_land_taxonomy.py        # Calls Land Taxonomy Classifier API
│   └── merge_results.py             # Merges per-row JSON results → enriched CSV
│
└── assets/
    ├── Belege_aus_D_2.csv           # Original source file (semicolon-delimited, ~109k records)
    ├── Belege_aus_D.csv             # Pipeline-ready CSV (produced by convert_xlsx.py)
    ├── test_20.csv                  # 20-row test subset
    └── example_input.csv            # Minimal generic example
```

---

## Preparing the Input

The pipeline expects a **comma-delimited CSV** with at minimum these columns:

| Column | Description |
|---|---|
| `id` | Unique record identifier |
| `text_land` | Habitat/locality text for the Land Taxonomy Classifier |
| `text_biodiv` | Species name text for the BiodivPortal Annotator |

Convert the original source file once with:

```bash
pip install openpyxl   # only needed if converting from xlsx
python bin/convert_xlsx.py \
    --input  assets/Belege_aus_D_2.csv \
    --output assets/Belege_aus_D.csv \
    --skip-empty-land
```

The converter maps source columns as follows:

| Output column | Source column | Notes |
|---|---|---|
| `id` | `HerbariumID` | Unique specimen identifier |
| `text_land` | `FundortUNdOeko` or `Locality` | FundortUNdOeko preferred when non-empty |
| `text_biodiv` | `FullNameCache` | Scientific species name |
| `locality` | `Locality` | Raw collection site string |
| `fundort` | `FundortUNdOeko` | Ecological description |
| `species` | `FullNameCache` | (same as text_biodiv, kept for reference) |
| `family` | `Family` | Plant family |
| `country` | `Country` | |
| `latitude` | `Latitude` | |
| `longitude` | `Longitude` | |
| `barcode` | `Barcode` | |
| `stable_uri` | `StableURI` | Persistent specimen URI |

---

## Quick Start

> **Before running**, complete [INSTALL.md](INSTALL.md) and start the **land-taxonomy-classifier** service locally.

### 1. Start the local classifier (separate terminal)

```bash
cd land-taxonomy-classifier
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Smoke-test with 20 records

```bash
nextflow run main.nf \
    --input assets/test_20.csv \
    --outdir results_test/
```

### 3. Smoke-test with 50 records from the full dataset

```bash
nextflow run main.nf -profile belege_test
```

### 4. Full run

```bash
nextflow run main.nf -profile belege
```

### 5. Check the output

```bash
cat results/enriched_dataset.csv
```

---

## Output Format

`enriched_dataset.csv` contains all input columns plus:

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
| `--id_column` | `id` | ID column name |
| `--land_text_column` | `text_land` | Text column for Land Taxonomy Classifier |
| `--biodiv_text_column` | `text_biodiv` | Text column for BiodivPortal Annotator |
| `--max_records` | *(all)* | Stop after N records (useful for testing) |
| `--python_bin` | `python3` | Python interpreter path |
| `--biodivportal_url` | `https://data.biodivportal.gfbio.org` | BiodivPortal base URL |
| `--biodivportal_apikey` | *(empty)* | BiodivPortal API key |
| `--biodivportal_ontologies` | *(empty)* | Restrict to specific ontologies |
| `--land_classifier_url` | `http://127.0.0.1:8000` | Land classifier base URL |
| `--land_classifier_top_k` | `5` | Number of classifications to return |
| `--land_classifier_model` | `gpt-4o-mini` | OpenAI model for the classifier |

---

## Execution Profiles

| Profile | Description |
|---|---|
| `standard` | Local execution without Docker (default) |
| `docker` | Local execution using Docker containers |
| `slurm` | HPC cluster with SLURM scheduler |
| `belege` | Full Belege_aus_D run (all ~109k records) |
| `belege_test` | Quick test: first 50 records from Belege_aus_D |
| `test` | Minimal test using `example_input.csv` |

```bash
nextflow run main.nf -profile belege_test   # 50 records, fast check
nextflow run main.nf -profile belege        # full dataset
nextflow run main.nf -profile test          # generic example CSV
```

---

## Services Used

### BiodivPortal Annotator
- **URL:** https://data.biodivportal.gfbio.org
- **Endpoint:** `GET /annotator?text=<text>&apikey=<key>`
- **Input text:** `text_biodiv` — scientific species name (`FullNameCache`)
- **Registration:** Free API key at https://biodivportal.gfbio.org/

### Land Taxonomy Classifier
- **Repository:** https://github.com/biodivportal/land-taxonomy-classifier
- **Endpoint:** `POST /classify` with `{"text": "...", "top_k": 5}`
- **Input text:** `text_land` — habitat/locality description (`FundortUNdOeko` or `Locality`)
- **Requirements:** Local installation + OpenAI API key (see [INSTALL.md](INSTALL.md))

---

## Requirements

- Nextflow ≥ 23.04
- Java 17+
- Python 3.10+
- `openpyxl` only needed for one-time xlsx conversion (`pip install openpyxl`)
- OpenAI API key (for the land-taxonomy-classifier)
- Docker (optional, for `-profile docker`)

See [INSTALL.md](INSTALL.md) for complete setup instructions.
