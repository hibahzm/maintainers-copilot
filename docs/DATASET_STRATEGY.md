# Dataset Strategy

## Recommendation for v1

Start with **our own GitHub-issue dataset**, collected from a small set of public repositories whose issue labels roughly map to the categories we want the app to predict:

- `bug`
- `feature`
- `question`
- `documentation`

Why this shape:

1. It matches the product we are building better than a generic text-classification dataset.
2. It lets us preserve the original issue fields we may later need for RAG, audits, and error analysis.
3. It keeps the labeling story explainable: the first weak labels come from repository labels, then we hand-clean the eval set.

## Suggested process

1. **Define the label map first**  
   Example: `enhancement -> feature`, `docs -> documentation`, `type: bug -> bug`.

2. **Fetch raw issues from GitHub**  
   Save the untouched API payload-derived records in `data/raw_issues.jsonl`.

3. **Normalize and clean locally in repo scripts**  
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

4. **Split by time, not random shuffle**  
   Keep `test.jsonl` strictly newer than training data so evaluation better resembles future incoming issues.

5. **Hand-curate the gold sets**  
   `evals/golden_classification.json` should stay small, clean, and human-reviewed even if training data is larger and weakly labeled.

6. **Use Colab only for heavy experiments**  
   Training/fine-tuning can happen in Colab, but the source-of-truth scripts, schemas, and output format should live in this repository so the work is reproducible outside one notebook.

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
