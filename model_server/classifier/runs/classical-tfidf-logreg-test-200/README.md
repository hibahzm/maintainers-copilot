# classical-tfidf-logreg-test-200

Landing zone for the TF-IDF + Logistic Regression baseline evaluated on the 200-row balanced comparison subset.

Run from Colab:

```bash
python -m model_server.classifier.train_tfidf_logreg \
  --train-path /content/drive/MyDrive/maintainers-copilot/data/train.jsonl \
  --val-path /content/drive/MyDrive/maintainers-copilot/data/val.jsonl \
  --test-path /content/drive/MyDrive/maintainers-copilot/data/test_200_balanced.jsonl \
  --run-dir /content/drive/MyDrive/maintainers-copilot/artifacts/classical-tfidf-logreg-test-200 \
  --run-name classical-tfidf-logreg-test-200
```

Bring back:

```text
model_server/classifier/runs/classical-tfidf-logreg-test-200/run_manifest.json
model_server/classifier/runs/classical-tfidf-logreg-test-200/metrics.json
model_server/classifier/runs/classical-tfidf-logreg-test-200/classification_report.json
```
