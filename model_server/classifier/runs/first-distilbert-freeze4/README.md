# first-distilbert-freeze4

Landing zone for the first corrected four-class DistilBERT fine-tuning run from Colab.

Copy these files from Google Drive into this directory:

```text
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/run_manifest.json
/content/drive/MyDrive/maintainers-copilot/artifacts/first-distilbert-freeze4/metrics.json
```

Final repo paths should be:

```text
model_server/classifier/runs/first-distilbert-freeze4/run_manifest.json
model_server/classifier/runs/first-distilbert-freeze4/metrics.json
```

Do not copy the run's `model/` or `checkpoints/` directories into Git. Those stay in Drive for now, and later move behind the project's artifact-storage boundary.
