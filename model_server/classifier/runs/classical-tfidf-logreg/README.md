# classical-tfidf-logreg

Classical baseline evidence for the Week 7 classifier comparison track.

Run command:

```bash
python -m model_server.classifier.train_tfidf_logreg
```

Committed evidence files:

```text
model_server/classifier/runs/classical-tfidf-logreg/run_manifest.json
model_server/classifier/runs/classical-tfidf-logreg/metrics.json
model_server/classifier/runs/classical-tfidf-logreg/classification_report.json
```

Summary:

| Split | Accuracy | Macro F1 | Weighted F1 |
| --- | ---: | ---: | ---: |
| Validation | `0.7911` | `0.7414` | `0.7885` |
| Test | `0.9445` | `0.8847` | `0.9433` |

This baseline uses TF-IDF word features plus balanced Logistic Regression over the exact same `train.jsonl`, `val.jsonl`, and `test.jsonl` files as the transformer track. It commits only small evidence files, not binary model artifacts.
