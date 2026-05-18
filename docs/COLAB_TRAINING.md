# Colab Notebook Workflow

Use this when you want the **whole data-prep + first-training sequence to run inside Google Colab** so your local machine does not need to store the raw dataset or model artifacts.

If you do **not** want to clone the repo inside Colab, use the ready-made notebook:

```text
notebooks/maintainers_copilot_week7_colab.ipynb
```

That notebook contains the same fetch, split, inspect, and training logic inline so you can upload it directly to Colab and run it cell by cell.

The design stays the same:

- the **repository** owns the scripts, configs, and decisions;
- **Colab** runs those scripts in a notebook session and supplies GPU compute when training begins.

The standalone notebook mirrors the repository code for convenience. If we later change the canonical pipeline, we should update both together rather than letting them drift.

## Do we need the data on the laptop?

No. If local disk is limited, fetch and build the dataset inside Colab. The generated files can live in:

- the temporary Colab VM for a one-off experiment, or
- Google Drive if you want them to survive after the runtime disconnects.

You only need to bring outputs back into the repo when we decide which files belong in version control or artifact storage.

## Do we need a GPU?

| Task | GPU needed? |
| --- | --- |
| clone repo | no |
| fetch GitHub issues | no |
| build train/val/test splits | no |
| inspect split report | no |
| fine-tune DistilBERT | yes, recommended |

CPU training is possible, but for the transformer run a GPU is the sensible choice.

## Colab runtime setup

In Colab:

1. Open a new notebook.
2. Set **Runtime → Change runtime type → T4 GPU**.
3. Run the cells below in order.

## Cell 1 — Clone the repository

```bash
!git clone <YOUR_REPO_URL> maintainers-copilot
%cd maintainers-copilot
```

If the repo is private, use your normal GitHub authentication path in Colab before cloning.

## Cell 2 — Install the training dependencies

```bash
!pip install -e "model_server[train]"
```

## Cell 3 — Optional: mount Google Drive for persistence

Use this if you do not want the generated dataset and artifacts to disappear when Colab resets.

```python
from google.colab import drive
drive.mount("/content/drive")
```

Optional destination folders:

```bash
!mkdir -p /content/drive/MyDrive/maintainers-copilot/data
!mkdir -p /content/drive/MyDrive/maintainers-copilot/artifacts
```

If you prefer the simplest first run, skip Drive and keep everything in the Colab VM.

## Cell 4 — Fetch the Week 7 dataset

```bash
!python -m scripts.dataset.fetch_issues
```

This fetches closed issues from the fixed source repository:

```text
fastapi/fastapi
```

and writes:

```text
data/raw_issues.jsonl
```

If GitHub rate limits become a problem, set a `GITHUB_TOKEN` in the notebook environment and rerun the same command.

## Cell 5 — Build the classifier splits

```bash
!python -m scripts.dataset.build_splits
```

This writes:

```text
data/train.jsonl
data/val.jsonl
data/test.jsonl
data/split_report.json
```

The splitter preserves chronological order, keeps the test set newer than train, and rejects splits that lose any target label.

## Cell 6 — Inspect the split report before training

```python
import json

with open("data/split_report.json", encoding="utf-8") as f:
    report = json.load(f)

report
```

Check:

- every split contains `bug`, `feature`, `docs`, `question`;
- the test date range is newer than the training range;
- no label is so tiny that training would be misleading.

Do not train blindly before reading this.

## Cell 7 — Optional: copy generated data to Drive

If Drive is mounted:

```bash
!cp data/raw_issues.jsonl /content/drive/MyDrive/maintainers-copilot/data/
!cp data/train.jsonl data/val.jsonl data/test.jsonl data/split_report.json /content/drive/MyDrive/maintainers-copilot/data/
```

## Cell 8 — Log into Weights & Biases

```python
import wandb
wandb.login()
```

The configured project name is:

```text
maintainers-copilot-week7
```

## Cell 9 — Run the first fine-tuning experiment

```bash
!python -m model_server.classifier.train \
  --train-path data/train.jsonl \
  --val-path data/val.jsonl \
  --run-name first-distilbert-freeze4
```

## Cell 10 — Inspect outputs

```bash
!find artifacts/classifier/first-distilbert-freeze4 -maxdepth 2 -type f | sort
!cat artifacts/classifier/first-distilbert-freeze4/run_manifest.json
!cat artifacts/classifier/first-distilbert-freeze4/metrics.json
```

Expected outputs:

- `run_manifest.json` — exact config, dataset hashes, label IDs, logger metadata
- `metrics.json` — final validation metrics
- `model/` — saved tokenizer + classifier weights
- `checkpoints/` — Hugging Face training checkpoints

## Cell 11 — Optional: copy artifacts to Drive

If Drive is mounted:

```bash
!cp -r artifacts/classifier/first-distilbert-freeze4 /content/drive/MyDrive/maintainers-copilot/artifacts/
```

## What not to do in the notebook

Do not:

- rewrite fetch or split logic in ad hoc notebook cells,
- hand-edit labels in Colab,
- silently change hyperparameters there without updating repo code first,
- let the notebook become the only place where the workflow exists.

Colab is the cockpit. The repository remains the aircraft.
