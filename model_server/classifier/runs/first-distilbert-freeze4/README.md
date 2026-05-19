# first-distilbert-freeze4

First corrected four-class DistilBERT fine-tuning run from Colab.

Committed evidence:

```text
model_server/classifier/runs/first-distilbert-freeze4/run_manifest.json
model_server/classifier/runs/first-distilbert-freeze4/metrics.json
```

Validation metrics from `metrics.json`:

| Metric | Value |
| --- | ---: |
| Macro F1 | `0.7422` |
| Accuracy | `0.8135` |
| Eval loss | `0.5508` |

Dataset hashes are recorded in `run_manifest.json` and summarized in `model_server/classifier/model_card.md`.

Do not copy the run's `model/` or `checkpoints/` directories into Git. Those stay in Drive for now, and later move behind the project's artifact-storage boundary.
