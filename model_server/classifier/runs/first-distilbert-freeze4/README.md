# first-distilbert-freeze4

First corrected four-class DistilBERT fine-tuning run from Colab.

Committed evidence:

```text
model_server/classifier/runs/first-distilbert-freeze4/run_manifest.json
model_server/classifier/runs/first-distilbert-freeze4/metrics.json
```

Additional committed test evidence:

```text
model_server/classifier/runs/first-distilbert-freeze4/test_metrics.json
model_server/classifier/runs/first-distilbert-freeze4/classification_report.json
model_server/classifier/runs/first-distilbert-freeze4/model_artifact_fingerprint.json
```

Validation metrics from `metrics.json`:

| Metric | Value |
| --- | ---: |
| Macro F1 | `0.7422` |
| Accuracy | `0.8135` |
| Eval loss | `0.5508` |

Dataset hashes are recorded in `run_manifest.json` and summarized in `model_server/classifier/model_card.md`.
The saved model directory SHA-256 is recorded in `model_artifact_fingerprint.json`:

```text
45790f41e45d707aada1b76e87e4b6919e51ea357c40bc1f30a444fe34a6f67a
```

Do not copy the run's `model/` or `checkpoints/` directories into Git. Those stay in Drive for now, and later move behind the project's artifact-storage boundary.

Test metrics from `test_metrics.json`:

| Metric | Value |
| --- | ---: |
| Macro F1 | `0.9000` |
| Accuracy | `0.9534` |
| Weighted F1 | `0.9517` |
| Examples/sec | `70.2` |

Compared with the classical baseline on the same test split, DistilBERT is slightly stronger on accuracy and macro-F1, but much slower at inference.
