# first-distilbert-freeze4-test-200

Landing zone for evaluating the saved DistilBERT classifier on the 200-row balanced comparison subset.

Run from Colab after the saved model exists in Drive:

```bash
python -m model_server.classifier.evaluate_distilbert \
  --model-dir /content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/model \
  --test-path /content/drive/MyDrive/maintainers-copilot/data/test_200_balanced.jsonl \
  --output-dir /content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4-test-200
```

Bring back:

```text
model_server/classifier/runs/first-distilbert-freeze4-test-200/test_metrics.json
model_server/classifier/runs/first-distilbert-freeze4-test-200/classification_report.json
```
