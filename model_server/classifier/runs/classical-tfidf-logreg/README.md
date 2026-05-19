# classical-tfidf-logreg

Landing zone for the classical baseline in the Week 7 classifier comparison track.

Run from the repository root after installing the model-server training dependencies:

```bash
python -m model_server.classifier.train_tfidf_logreg
```

Expected small evidence files:

```text
model_server/classifier/runs/classical-tfidf-logreg/run_manifest.json
model_server/classifier/runs/classical-tfidf-logreg/metrics.json
model_server/classifier/runs/classical-tfidf-logreg/classification_report.json
```

This baseline uses TF-IDF word features plus Logistic Regression over the exact same `train.jsonl`, `val.jsonl`, and `test.jsonl` files as the transformer run. It should not write model weights or binary artifacts into Git.
