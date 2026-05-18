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
