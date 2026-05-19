# Evaluations

## Planned evaluation suites

- issue classification quality against `evals/golden_classification.json`
- RAG retrieval and answer quality against `evals/golden_rag.json`
- CI thresholds from `evals/eval_thresholds.yaml`

The first classification golden set now lives in `evals/golden_classification.json`. It contains 25 synthetic, hand-curated issue examples with expected labels and rationales. It is intentionally separate from `data/train.jsonl`, `data/test.jsonl`, and `data/test_200_balanced.jsonl`.


## Classification golden set

`evals/golden_classification.json` contains 25 reviewable examples:

- 7 `bug`
- 6 `feature`
- 6 `docs`
- 6 `question`

Run the eval after the model server is serving `/classify`:

```bash
python -m evals.run_classification_eval \
  --endpoint http://localhost:8001/classify \
  --output evals/classification_eval_results.json
```

`classification_eval_results.json` is generated evidence and should be committed only when we intentionally record an eval run.
