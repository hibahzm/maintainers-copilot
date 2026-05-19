# Data Layout

- Week 7 source repository: `pandas-dev/pandas`
- Issue state: `closed`

- `raw_issues.jsonl` — source issues fetched from GitHub
- `train.jsonl` — model training split
- `val.jsonl` — validation split
- `test.jsonl` — strictly newer examples than the training split
- `split_report.json` — generated counts, label mix, and date ranges for the current split set

## Dataset scripts

Run from the repository root:

```bash
python -m scripts.dataset.fetch_issues
python -m scripts.dataset.build_splits
```

The fetcher is fixed to closed issues from `pandas-dev/pandas` by default. The splitter keeps the test split chronological, then builds deterministic stratified train/validation splits inside the older pool.

## Bringing corrected Colab files back

The checked-in JSONL files may start as empty placeholders. After the corrected Colab dataset run, replace them with the real files from Drive:

```text
/content/drive/MyDrive/maintainers-copilot/data/raw_issues.jsonl -> data/raw_issues.jsonl
/content/drive/MyDrive/maintainers-copilot/data/train.jsonl      -> data/train.jsonl
/content/drive/MyDrive/maintainers-copilot/data/val.jsonl        -> data/val.jsonl
/content/drive/MyDrive/maintainers-copilot/data/test.jsonl       -> data/test.jsonl
/content/drive/MyDrive/maintainers-copilot/data/split_report.json -> data/split_report.json
```

Keep large model folders out of `data/`; only dataset inputs and split reports belong here.
