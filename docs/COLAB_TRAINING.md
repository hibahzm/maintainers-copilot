# Colab Training Handoff

This note exists so the first GPU run uses the repository's real pipeline instead of becoming a second, notebook-only implementation.

## When to use this

Use Colab only after:

1. `data/raw_issues.jsonl` has been fetched,
2. `data/train.jsonl` and `data/val.jsonl` have been generated,
3. `data/split_report.json` has been inspected,
4. the label mix is acceptable enough to begin the first experiment.

Until those files exist, there is nothing honest to fine-tune.

## What Colab does

Colab provides GPU compute for the first encoder run. It does **not** own:

- data fetching,
- label mapping,
- split logic,
- training source code,
- model-card source text.

Those remain in the repository.

## First-run sequence

In a fresh Colab notebook:

```bash
!git clone <YOUR_REPO_URL> maintainers-copilot
%cd maintainers-copilot
!pip install -e "model_server[train]"
```

If the dataset files are already committed or uploaded into the repo workspace, verify they exist:

```bash
!ls data/train.jsonl data/val.jsonl data/split_report.json
```

Start the first logged run:

```bash
!python -m model_server.classifier.train \
  --train-path data/train.jsonl \
  --val-path data/val.jsonl \
  --run-name first-distilbert-freeze4
```

## Expected outputs

The run writes under:

```text
artifacts/classifier/first-distilbert-freeze4/
```

Expected contents:

- `run_manifest.json` — exact config, dataset hashes, label IDs, logger metadata
- `metrics.json` — final validation metrics
- `model/` — saved tokenizer + classifier weights
- `checkpoints/` — Hugging Face training checkpoints

Those files are the evidence used later to finish the model card and defend the classifier choice in `DECISIONS.md`.

## Logger setup

The first run is configured for Weights & Biases. Before launching training in Colab, authenticate once in the notebook:

```python
import wandb
wandb.login()
```

The project name is fixed in code as:

```text
maintainers-copilot-week7
```

## What not to do in Colab

Do not:

- rewrite the split logic in notebook cells,
- hand-edit labels there,
- silently change hyperparameters there without updating repo code first,
- treat notebook output as the only copy of the experiment.

If the experiment changes, change the repository code first. Colab should execute the project, not fork it.
