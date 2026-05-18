# Dataset Strategy

## Week 7 dataset choice

Use **closed issues from one repository only**:

- source repository: `fastapi/fastapi`
- issue state: `closed`
- rule: keep using this same repository for the whole project

This follows the Week 7 brief directly: pick one repo once, then live with that choice.

## Target labels

FastAPI is a good fit because its issue labels already map cleanly to the categories we want the app to predict:

- `bug`
- `feature`
- `docs`
- `question`

The current mapping is intentionally one-to-one:

| FastAPI label | Target |
| --- | --- |
| `bug` | `bug` |
| `feature` | `feature` |
| `docs` | `docs` |
| `question` | `question` |

## Why this repo

1. It matches the product we are building better than a generic text-classification dataset.
2. It is large, mature, Python-based, and close to the domain of our own app.
3. Its labels are unusually convenient for the classifier we plan to build.
4. It lets us preserve the original issue fields we may later need for RAG, audits, and error analysis.
5. It keeps the labeling story explainable: the first weak labels come from repository labels, then we hand-clean the eval set.

## Suggested process

1. **Fix the source before writing code**  
   All Week 7 dataset scripts should default to `fastapi/fastapi` and `state=closed`.

2. **Confirm the label map**  
   Start from FastAPI labels and map only the labels we intentionally support.

3. **Fetch raw closed issues from GitHub**  
   Save the untouched API payload-derived records in `data/raw_issues.jsonl`.

4. **Normalize and clean locally in repo scripts**  
   Produce model-ready records with stable fields such as:

   ```json
   {
     "id": "repo#123",
     "repo": "owner/name",
     "title": "...",
     "body": "...",
     "labels": ["bug"],
     "target": "bug",
     "created_at": "2025-01-10T12:00:00Z"
   }
   ```

5. **Split by time, not random shuffle**  
   Keep `test.jsonl` strictly newer than training data so evaluation better resembles future incoming issues. The split builder searches chronological cutoffs that preserve the overall class mix as closely as possible while keeping all four labels represented.

6. **Check class balance before training**  
   Count examples per target label. If one label dominates, document the imbalance and decide on sampling before training.

7. **Hand-curate the gold sets**  
   `evals/golden_classification.json` should stay small, clean, and human-reviewed even if training data is larger and weakly labeled.

8. **Use online Google Colab as the notebook execution surface when local space is tight**  
   The user may run fetching, splitting, inspection, and GPU training from one Colab notebook so the raw data and artifacts do not need to live on the laptop. The important boundary is that the repository still defines the scripts, schemas, evals, prompts, and training configuration; Colab executes them rather than replacing them.

## Where Colab belongs

Use Colab for:

- running the repo's fetch and split scripts when local disk is constrained
- the first encoder fine-tuning run
- later retraining experiments if local hardware is too slow
- optional embedding-model experiments if GPU acceleration helps

The concrete notebook flow now lives in `docs/COLAB_TRAINING.md`.

Do **not** make Colab the home of:

- custom GitHub-fetch logic
- custom data-cleaning logic
- hand-edited label mapping
- notebook-only train/val/test split logic
- golden-set definitions
- model-card source text

Those belong in the repository. Colab should execute our pipeline, not replace it.

## Why JSONL instead of CSV?

Use JSONL for the canonical dataset files because one issue naturally contains nested data:

- multiple labels
- optional metadata
- long free-text bodies
- future fields like comments, assignees, or retrieved chunks

JSONL stores one full JSON object per line, so it is append-friendly, streamable, and does not force nested fields into fragile string encodings. CSV is still useful later for quick inspection or spreadsheet-style exports, but it is a weaker source-of-truth format for this data model.

## When CSV is still fine

CSV is perfectly reasonable for:

- a small manual review export
- a quick confusion-matrix companion file
- sharing a flat slice with someone who wants Excel

It is just not the best primary format once an issue stops being a flat row.
