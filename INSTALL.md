# Installation Guide

This guide walks you through setting up everything needed to run the **BiodivPortal Enrichment Workflow** on **Windows with WSL2**.

---

## Prerequisites Overview

| Component | Purpose |
|---|---|
| WSL2 (Ubuntu) | Linux environment on Windows |
| Java 17+ | Required by Nextflow |
| Nextflow | Workflow engine |
| Python 3.10+ | Required by the local classifier service |
| OpenAI API key | Used by the land-taxonomy-classifier |
| BiodivPortal API key | Used by the BiodivPortal Annotator |

---

## Step 1 — Enable WSL2 and Install Ubuntu

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This installs WSL2 with Ubuntu by default. Restart your computer when prompted.

After restart, open the **Ubuntu** app from the Start menu and create your Unix username and password.

Update the system packages:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 2 — Install Java 17

Nextflow requires Java 17 or later.

```bash
sudo apt install -y openjdk-17-jdk
```

Verify:

```bash
java -version
# Expected: openjdk version "17.x.x" ...
```

---

## Step 3 — Install Nextflow

```bash
curl -s https://get.nextflow.io | bash
chmod +x nextflow
sudo mv nextflow /usr/local/bin/

nextflow -version
```

---

## Step 4 — Install the Land Taxonomy Classifier

The `land-taxonomy-classifier` runs locally as a FastAPI service.

```bash
git clone https://github.com/biodivportal/land-taxonomy-classifier.git
cd land-taxonomy-classifier

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Open `.env` and add your OpenAI API key:

```bash
nano .env
# Set: OPENAI_API_KEY=sk-...your-key-here...
```

---

## Step 5 — Start the Local Classifier Service

The classifier must be running before you execute the workflow. Open a **separate terminal**:

```bash
cd land-taxonomy-classifier
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Verify it is running: http://127.0.0.1:8000

---

## Step 6 — Clone This Workflow

```bash
git clone https://github.com/biodivportal/biodiv-workflow.git
cd biodiv-workflow
```

---

## Step 7 — Provide the Input Data File

The input file `Belege_aus_D.csv` is **not included in this repository** and must be provided separately.

WSL2 can access Windows files via `/mnt/c/`. For example:

| Windows path | WSL2 path |
|---|---|
| `C:\Users\janfi\Downloads\Belege_aus_D_2.csv` | `/mnt/c/Users/janfi/Downloads/Belege_aus_D_2.csv` |

Copy the source file into the `assets/` folder, then convert it once:

```bash
cp /mnt/c/Users/janfi/Downloads/Belege_aus_D_2.csv assets/
python bin/convert_xlsx.py \
    --input  assets/Belege_aus_D_2.csv \
    --output assets/Belege_aus_D.csv
```

---

## Step 8 — Configure the Workflow

Open `nextflow.config` and set your **BiodivPortal API key**:

```bash
nano nextflow.config
```

Set:

```groovy
biodivportal_apikey = "your-api-key-here"
```

Get a free API key at https://biodivportal.gfbio.org/account

---

## Step 9 — Run the Workflow

Smoke-test with 5 records:

```bash
nextflow run main.nf -profile test
```

Full run:

```bash
nextflow run main.nf \
    --input assets/Belege_aus_D.csv \
    --outdir results/
```

Results are written to `results/enriched_dataset.csv`.

---

## Optional: Docker

If you prefer containerised execution, install [Docker Desktop](https://www.docker.com/products/docker-desktop/), enable WSL2 integration in Docker Desktop settings, then run:

```bash
nextflow run main.nf -profile docker --input assets/Belege_aus_D.csv --outdir results/
```

---

## Troubleshooting

**`Connection refused` when calling the local classifier**
Make sure the uvicorn server is running in a separate terminal (Step 5).

**BiodivPortal returns 401**
Set `biodivportal_apikey` in `nextflow.config` or pass `--biodivportal_apikey YOUR_KEY`.

**`nextflow: command not found`**
Ensure `/usr/local/bin` is in your PATH: `echo $PATH`

**OpenAI API errors in the classifier**
Check your `.env` file inside `land-taxonomy-classifier/` has a valid `OPENAI_API_KEY`.

**Docker permission denied**
Run `sudo usermod -aG docker $USER`, then close and reopen your WSL2 terminal.
