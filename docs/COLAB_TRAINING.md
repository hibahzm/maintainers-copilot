# Colab Notebook Workflow

Use this when you want the **whole data-prep + first-training sequence to run inside Google Colab** so your local machine does not need to store the raw dataset or model artifacts.

If you do **not** want to clone the repo inside Colab, use the ready-made notebooks as separate tracks:

```text
notebooks/maintainers_copilot_week7_colab.ipynb      # dataset + DistilBERT fine-tuning track
notebooks/tfidf_logreg_baseline_colab.ipynb          # classical TF-IDF + Logistic Regression track
notebooks/llm_openai_baseline_colab.ipynb            # OpenAI LLM baseline track
```

Keep these notebooks separate. The DistilBERT notebook fetches/builds the dataset and trains the transformer. The TF-IDF and OpenAI notebooks assume the corrected `train.jsonl`, `val.jsonl`, and `test_200_balanced.jsonl` already exist in Drive, then write only their own baseline evidence files.

The design stays the same:

- the **repository** owns the scripts, configs, and decisions;
- **Colab** runs those scripts in a notebook session and supplies GPU compute when training begins.

The standalone notebooks mirror the repository code for convenience. If we later change the canonical pipeline, we should update the matching notebook too rather than letting them drift.

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
pandas-dev/pandas
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
!python -m model_server.classifier.train_distilbert \
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

## Cell 12 — Evaluate saved DistilBERT on the 200-row comparison subset

The DistilBERT notebook now ends with a standalone comparison-evaluation section. Run it after the model has been copied to Drive at:

```text
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/model/
```

It evaluates:

```text
/content/drive/MyDrive/maintainers-copilot/data/test_200_balanced.jsonl
```

and writes:

```text
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4-test-200/test_metrics.json
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4-test-200/classification_report.json
```

## 200-row comparison subset

The full temporal `test.jsonl` stays in the repo and remains useful evidence for cheap local models. For the fair three-way comparison with OpenAI, use the smaller balanced file:

```text
/content/drive/MyDrive/maintainers-copilot/data/test_200_balanced.jsonl
```

It contains 200 examples: 50 `bug`, 50 `feature`, 50 `docs`, and 50 `question`. It is generated from the full `test.jsonl`, not from train/validation.

Before running the comparison notebooks, make sure these files are in Drive:

```text
/content/drive/MyDrive/maintainers-copilot/data/train.jsonl
/content/drive/MyDrive/maintainers-copilot/data/val.jsonl
/content/drive/MyDrive/maintainers-copilot/data/test_200_balanced.jsonl
/content/drive/MyDrive/maintainers-copilot/data/test_200_balanced_report.json
```

## DistilBERT 200-row comparison evaluation

Use the final standalone evaluation section in:

```text
notebooks/maintainers_copilot_week7_colab.ipynb
```

It loads the existing saved model from:

```text
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/model/
```

and writes the 200-row comparison evidence to:

```text
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4-test-200/test_metrics.json
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4-test-200/classification_report.json
```

## Separate classical baseline notebook

Use this notebook after the corrected split files and `test_200_balanced.jsonl` are already in Drive:

```text
notebooks/tfidf_logreg_baseline_colab.ipynb
```

It writes:

```text
/content/drive/MyDrive/maintainers-copilot/artifacts/classical-tfidf-logreg-test-200/run_manifest.json
/content/drive/MyDrive/maintainers-copilot/artifacts/classical-tfidf-logreg-test-200/metrics.json
/content/drive/MyDrive/maintainers-copilot/artifacts/classical-tfidf-logreg-test-200/classification_report.json
```

## Separate OpenAI LLM baseline notebook

Use this notebook after `test_200_balanced.jsonl` is in Drive and your OpenAI API key is available in Colab Secrets as `OPENAI_API_KEY`:

```text
notebooks/llm_openai_baseline_colab.ipynb
```

It starts with a 50-example pilot by default. For the final comparison, set `FINAL_RUN = True` so it evaluates all 200 balanced examples. Requests are batched with `BATCH_SIZE = 20`, so the final run is about 10 OpenAI requests.

The final run writes:

```text
/content/drive/MyDrive/maintainers-copilot/artifacts/openai-gpt-4o-mini-test-200/run_manifest.json
/content/drive/MyDrive/maintainers-copilot/artifacts/openai-gpt-4o-mini-test-200/metrics.json
/content/drive/MyDrive/maintainers-copilot/artifacts/openai-gpt-4o-mini-test-200/classification_report.json
```

## After a successful corrected run

Bring back the corrected dataset files and the small run evidence. Use this exact placement:

| Colab / Drive source | Repo destination | Commit? |
| --- | --- | --- |
| `/content/drive/MyDrive/maintainers-copilot/data/raw_issues.jsonl` | `data/raw_issues.jsonl` | yes, if size is acceptable |
| `/content/drive/MyDrive/maintainers-copilot/data/train.jsonl` | `data/train.jsonl` | yes |
| `/content/drive/MyDrive/maintainers-copilot/data/val.jsonl` | `data/val.jsonl` | yes |
| `/content/drive/MyDrive/maintainers-copilot/data/test.jsonl` | `data/test.jsonl` | yes |
| `/content/drive/MyDrive/maintainers-copilot/data/split_report.json` | `data/split_report.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/data/test_200_balanced.jsonl` | `data/test_200_balanced.jsonl` | yes |
| `/content/drive/MyDrive/maintainers-copilot/data/test_200_balanced_report.json` | `data/test_200_balanced_report.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/run_manifest.json` | `model_server/classifier/runs/first-distilbert-freeze4/run_manifest.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/metrics.json` | `model_server/classifier/runs/first-distilbert-freeze4/metrics.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/model/` | keep in Drive | no |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/checkpoints/` | keep in Drive | no |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4-test-200/test_metrics.json` | `model_server/classifier/runs/first-distilbert-freeze4-test-200/test_metrics.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4-test-200/classification_report.json` | `model_server/classifier/runs/first-distilbert-freeze4-test-200/classification_report.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/classical-tfidf-logreg-test-200/run_manifest.json` | `model_server/classifier/runs/classical-tfidf-logreg-test-200/run_manifest.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/classical-tfidf-logreg-test-200/metrics.json` | `model_server/classifier/runs/classical-tfidf-logreg-test-200/metrics.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/classical-tfidf-logreg-test-200/classification_report.json` | `model_server/classifier/runs/classical-tfidf-logreg-test-200/classification_report.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/openai-gpt-4o-mini-test-200/run_manifest.json` | `model_server/classifier/runs/openai-gpt-4o-mini-test-200/run_manifest.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/openai-gpt-4o-mini-test-200/metrics.json` | `model_server/classifier/runs/openai-gpt-4o-mini-test-200/metrics.json` | yes |
| `/content/drive/MyDrive/maintainers-copilot/artifacts/openai-gpt-4o-mini-test-200/classification_report.json` | `model_server/classifier/runs/openai-gpt-4o-mini-test-200/classification_report.json` | yes |

If local disk is tight, prioritize `test_200_balanced.jsonl`, `test_200_balanced_report.json`, and the small `run_manifest.json` / `metrics.json` / `classification_report.json` evidence files. The raw issue snapshot is still useful for reproducibility, but the model weights and checkpoints must stay out of Git.

After those files are copied in, update the classifier model card and decisions from the committed evidence files, not from memory.

Until MinIO is wired in Step 2, Google Drive is an acceptable temporary holding area for the large model artifacts. The final architecture should store the chosen artifact or manifest in MinIO rather than in the repository.

## What not to do in the notebook

Do not:

- rewrite fetch or split logic in ad hoc notebook cells,
- hand-edit labels in Colab,
- silently change hyperparameters there without updating repo code first,
- let the notebook become the only place where the workflow exists.

Colab is the cockpit. The repository remains the aircraft.
