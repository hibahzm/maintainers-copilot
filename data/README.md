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


## Current corrected split snapshot

The corrected Colab split files currently committed here contain:

| Split | Rows | Label counts |
| --- | ---: | --- |
| `train.jsonl` | 10,012 | bug 5,240; feature 2,023; docs 1,500; question 1,249 |
| `val.jsonl` | 2,145 | bug 1,123; feature 433; docs 321; question 268 |
| `test.jsonl` | 2,145 | bug 1,344; feature 330; docs 393; question 78 |

`raw_issues.jsonl` may remain a zero-byte placeholder in low-space checkouts. Preserve the raw source snapshot in Drive or MinIO, but do not block local model-card and comparison work on copying it into the repo.


## 200-row balanced comparison subset

`test_200_balanced.jsonl` is a deterministic, balanced slice sampled from the full temporal `test.jsonl` split. It contains 200 examples total: 50 `bug`, 50 `feature`, 50 `docs`, and 50 `question`.

This file does **not** replace `test.jsonl`. It exists so DistilBERT, TF-IDF, and OpenAI `gpt-4o-mini` can be compared on the exact same examples without paying to send all 2,145 test rows to the LLM.

Regenerate it from the repo root with:

```bash
python -m scripts.dataset.build_comparison_subset
```

The generation report is `test_200_balanced_report.json`. Copy both files to Drive before running the 200-example Colab evaluations:

```text
data/test_200_balanced.jsonl        -> /content/drive/MyDrive/maintainers-copilot/data/test_200_balanced.jsonl
data/test_200_balanced_report.json -> /content/drive/MyDrive/maintainers-copilot/data/test_200_balanced_report.json
```
