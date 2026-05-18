# Data Layout

- Week 7 source repository: `fastapi/fastapi`
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

The fetcher is fixed to closed issues from `fastapi/fastapi` by default. The splitter keeps chronological order, searches for cutoffs that preserve the overall label mix as closely as possible, and rejects any split that cannot contain all four target labels.
