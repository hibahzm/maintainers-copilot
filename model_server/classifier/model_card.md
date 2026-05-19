# Classifier Model Card

## Status
First corrected four-class fine-tuning run completed from Colab.

This is the first encoder model result, not yet the final deployment choice. It must still be compared against the classical ML baseline and the LLM baseline on the same 200-row balanced comparison subset.

## Architecture
- Model family: `distilbert-base-uncased`
- Task head: four-way sequence classification
- Labels: `bug / feature / docs / question`
- Freeze policy: lower 4 DistilBERT encoder blocks frozen; top 2 blocks and classifier head trainable
- Run name: `first-distilbert-freeze4`

## Dataset
- Source repository: `pandas-dev/pandas`
- Issue state: closed issues
- Total raw records reported by split pipeline: `25,289`
- Total normalized records: `14,302`
- Dropped records:
  - ambiguous multi-target label: `244`
  - no supported target label: `10,743`
- Split policy:
  - test split is a strictly newer temporal holdout
  - validation split is deterministic and stratified inside the older train/validation pool

| Split | Examples | Bug | Feature | Docs | Question | Date range |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Train | 10,012 | 5,240 | 2,023 | 1,500 | 1,249 | 2010-09-29 → 2023-05-30 |
| Validation | 2,145 | 1,123 | 433 | 321 | 268 | 2010-10-12 → 2023-05-23 |
| Test | 2,145 | 1,344 | 330 | 393 | 78 | 2023-05-30 → 2026-05-09 |
| Balanced 200 | 200 | 50 | 50 | 50 | 50 | 2023-06-02 → 2026-04-22 |

### Dataset hashes

| File | SHA-256 |
| --- | --- |
| `data/train.jsonl` | `24dd7452cbdff5f01158a9db52f3a63c4bc0a14e1984771a72144729e0973320` |
| `data/val.jsonl` | `7888030eae31a4fd881d87a16c2c01d337d701094f11993c6483170b3583b797` |
| `data/test.jsonl` | `aa52b95e4479c495e352bfe23ee3eb3ed75a9ac77bce7c72026971ccb5f744de` |
| `data/test_200_balanced.jsonl` | `a14faed71a97718cd421fbd84f2ed4d584c3b13f275971fd2b1945429be88f2a` |
| `data/split_report.json` | `abbf85e030b9a8aa88ac565a34e2fab77d217a2c017dabaf189031f37a3f0645` |

The raw issue snapshot is not checked into this repo handoff because of local disk constraints. The corrected train/validation/test files and split report are committed here; the raw source snapshot should remain in Drive or later MinIO for full reproducibility.

## Hyperparameters
- Max length: `384`
- Learning rate: `2e-5`
- Train batch size: `16`
- Eval batch size: `32`
- Epochs: `3`
- Weight decay: `0.01`
- Warmup ratio: `0.1`
- Seed: `42`
- Logger: Weights & Biases project `maintainers-copilot-week7`

## DistilBERT validation metrics

| Metric | Value |
| --- | ---: |
| Macro F1 | `0.7422` |
| Accuracy | `0.8135` |
| Eval loss | `0.5508` |
| Eval samples/sec | `82.148` |

## DistilBERT test metrics

Run: `first-distilbert-freeze4` evaluated on `data/test.jsonl`

| Metric | Value |
| --- | ---: |
| Accuracy | `0.9534` |
| Macro F1 | `0.9000` |
| Weighted F1 | `0.9517` |
| Examples/sec | `70.2` |
| Device | `cuda` |

Test per-class F1:

| Label | F1 |
| --- | ---: |
| Bug | `0.9684` |
| Feature | `0.9512` |
| Docs | `0.9363` |
| Question | `0.7442` |

## Comparison track status

| Track | Implementation | Evidence status |
| --- | --- | --- |
| Fine-tuned transformer | `distilbert-base-uncased`, freeze lower 4 layers | validation macro-F1 `0.7422`, test macro-F1 `0.9000` |
| Classical ML baseline | TF-IDF word n-grams + Logistic Regression | validation macro-F1 `0.7414`, test macro-F1 `0.8847` |
| LLM baseline | OpenAI `gpt-4o-mini` + Structured Outputs | code/notebook added; metrics pending |

The classical baseline evidence files are committed under `model_server/classifier/runs/classical-tfidf-logreg/`.

## Classical baseline metrics

Run: `classical-tfidf-logreg`

| Split | Accuracy | Macro F1 | Weighted F1 | Examples/sec |
| --- | ---: | ---: | ---: | ---: |
| Validation | `0.7911` | `0.7414` | `0.7885` | `2122.6` |
| Test | `0.9445` | `0.8847` | `0.9433` | `1312.1` |

Test per-class F1:

| Label | F1 |
| --- | ---: |
| Bug | `0.9633` |
| Feature | `0.9224` |
| Docs | `0.9377` |
| Question | `0.7153` |

Note: both DistilBERT and the classical baseline already have full temporal-test metrics. The fair three-way comparison now uses `data/test_200_balanced.jsonl` so the OpenAI baseline can be measured without sending all 2,145 test rows.

## Artifact policy

Committed evidence:

- `model_server/classifier/runs/first-distilbert-freeze4/run_manifest.json`
- `model_server/classifier/runs/first-distilbert-freeze4/metrics.json`
- `model_server/classifier/runs/first-distilbert-freeze4/test_metrics.json`
- `model_server/classifier/runs/first-distilbert-freeze4/classification_report.json`
- `model_server/classifier/runs/classical-tfidf-logreg/run_manifest.json`
- `model_server/classifier/runs/classical-tfidf-logreg/metrics.json`
- `model_server/classifier/runs/classical-tfidf-logreg/classification_report.json`

Not committed:

- model weights
- tokenizer binaries
- Hugging Face checkpoints

Large model artifacts stay in Google Drive for now and should move to MinIO when artifact storage is wired into the stack.
