# Classifier Run Evidence

This folder is for **small, reviewable evidence files** from classifier training runs.

Commit these when a run becomes part of the project record:

- `run_manifest.json` — exact training config, dataset hashes, labels, seed, and artifact metadata
- `metrics.json` — validation/test metrics exported by the training job
- `classification_report.json` — per-class precision/recall/F1 for baseline comparison runs
- compact derived summaries, if needed, such as `confusion_matrix.json`

Do **not** commit large training outputs here:

- `model/`
- `checkpoints/`
- tokenizer weight files
- binary artifacts

Until MinIO artifact storage is wired into the stack, keep large model files in Google Drive and copy only the small evidence files back into this directory.
