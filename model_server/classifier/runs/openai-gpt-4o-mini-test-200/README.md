# openai-gpt-4o-mini-test-200

Landing zone for the OpenAI LLM baseline evaluated on the 200-row balanced comparison subset.

Run command:

```bash
OPENAI_API_KEY=... python -m model_server.classifier.evaluate_openai_llm
```

Recommended pilot before the 200-example run:

```bash
OPENAI_API_KEY=... python -m model_server.classifier.evaluate_openai_llm --limit 50 --run-dir model_server/classifier/runs/openai-gpt-4o-mini-test-200-pilot --run-name openai-gpt-4o-mini-test-200-pilot
```

Default full comparison inputs:

```text
data/test_200_balanced.jsonl
batch size: 20
model: gpt-4o-mini
```

Expected evidence files:

```text
model_server/classifier/runs/openai-gpt-4o-mini-test-200/run_manifest.json
model_server/classifier/runs/openai-gpt-4o-mini-test-200/metrics.json
model_server/classifier/runs/openai-gpt-4o-mini-test-200/classification_report.json
```

`predictions.jsonl` is useful for debugging/resume. Commit it only if review stays clean; otherwise keep it in Drive and commit the three evidence files above.

Do not commit API keys.
