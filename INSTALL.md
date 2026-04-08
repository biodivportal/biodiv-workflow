# Installation Guide

This guide walks you through setting up everything needed to run the **BiodivPortal Enrichment Workflow** on **Windows with WSL2**.

---

## Prerequisites Overview

| Component | Purpose |
|---|---|
| WSL2 (Ubuntu) | Linux environment on Windows |
| Java 17+ | Required by Nextflow |
| Nextflow | Workflow engine |
| nf-core tools | Pipeline utilities and linting |
| Docker Desktop | Containerised process execution |
| Python 3.10+ | Required by the local classifier service |
| OpenAI API key | Used by the land-taxonomy-classifier |

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

Verify the installation:

```bash
java -version
# Expected output: openjdk version "17.x.x" ...
```

---

## Step 3 — Install Nextflow

```bash
# Download Nextflow launcher
curl -s https://get.nextflow.io | bash

# Make it executable and move to your PATH
chmod +x nextflow
sudo mv nextflow /usr/local/bin/

# Verify
nextflow -version
```

You should see something like `nextflow version 24.x.x`.

---

## Step 4 — Install nf-core Tools

nf-core tools require Python 3.8+. Ubuntu 22.04 ships with Python 3.10, so we can install directly:

```bash
sudo apt install -y python3-pip python3-venv

# Install nf-core
pip3 install nf-core --break-system-packages

# Verify
nf-core --version
```

---

## Step 5 — Install Docker Desktop (Windows side)

1. Download **Docker Desktop for Windows** from https://www.docker.com/products/docker-desktop/
2. During installation, ensure **"Use WSL 2 based engine"** is checked.
3. After install, open Docker Desktop → Settings → Resources → WSL Integration → Enable your Ubuntu distro.
4. Back in your WSL2 terminal, verify:

```bash
docker run hello-world
```

> **Note:** Docker Desktop must be running in Windows whenever you run the workflow.

---

## Step 6 — Install Python Dependencies for the Local Classifier

The `land-taxonomy-classifier` service runs locally as a FastAPI application.

```bash
# Clone the repository
git clone https://github.com/biodivportal/land-taxonomy-classifier.git
cd land-taxonomy-classifier

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

Now open `.env` and add your OpenAI API key:

```bash
nano .env
# Set: OPENAI_API_KEY=sk-...your-key-here...
```

---

## Step 7 — Start the Local Classifier Service

The classifier must be running before you execute the workflow. Open a **separate terminal** in WSL2:

```bash
cd land-taxonomy-classifier
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You can verify it is running by visiting: http://127.0.0.1:8000

---

## Step 8 — Clone This Workflow

In a new WSL2 terminal:

```bash
git clone https://github.com/YOUR_ORG/biodiv-workflow.git
cd biodiv-workflow
```

Or simply copy this folder to your WSL2 home directory.

---

## Step 9 — Configure the Workflow

Open `nextflow.config` and set your **BiodivPortal API key** (if required):

```bash
nano nextflow.config
```

Set the parameter:

```groovy
params.biodivportal_apikey = 'YOUR_API_KEY_HERE'
```

You can obtain a free API key by registering at https://biodivportal.gfbio.org/

---

## Step 10 — Run the Workflow

Prepare your input file (see `assets/example_input.csv` for format), then run:

```bash
nextflow run main.nf \
    --input assets/example_input.csv \
    --outdir results/
```

Results will be written to `results/enriched_dataset.csv`.

---

## Troubleshooting

**`docker: command not found`**
Make sure Docker Desktop is running in Windows and WSL integration is enabled in Docker Desktop settings.

**`nextflow: command not found`**
Ensure `/usr/local/bin` is in your PATH: `echo $PATH`

**`Connection refused` when calling the local classifier**
Make sure the uvicorn server is running in a separate terminal window.

**OpenAI API errors in the classifier**
Check your `.env` file inside the `land-taxonomy-classifier` folder has a valid `OPENAI_API_KEY`.
