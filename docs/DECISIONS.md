# Decisions

Every durable architectural decision should eventually be backed by a measurable reason. Until we have measurements, decisions are marked as **proposed** rather than pretending certainty.

| ID | Decision | Status | Number / Evidence to collect |
| --- | --- | --- | --- |
| D-001 | Split API, services, repositories, and infra into separate layers | proposed | compare unit-test setup cost and dependency fan-out after first 5 features |
| D-002 | Keep model inference in a separate service | proposed | compare API cold-start time and memory footprint with/without ML runtime |
| D-003 | Require redaction before traces/logs | accepted | target: 0 known secret leaks in audit samples |
| D-004 | Keep test split newer than train split | accepted | target: evaluate temporal generalization, not shuffled leakage |
| D-005 | Use `uv` for Python dependency management | accepted | target: one reproducible install flow per Python service |
| D-006 | Keep a `pyproject.toml` beside each Python-service Dockerfile | accepted | target: each image builds from a self-contained service context |
| D-007 | Manage PostgreSQL schema changes only through Alembic revisions | accepted | target: 0 manual schema drift between environments |
| D-008 | Separate Pydantic API schemas from framework-agnostic domain models | accepted | target: transport changes do not leak into core workflows |
| D-009 | Inject services into routers with FastAPI `Depends` | accepted | target: routers stay thin and test doubles can be swapped cleanly |
| D-010 | Use closed issues from `pandas-dev/pandas` as the Week 7 dataset source | accepted | target: one stable repo source across the whole project |
| D-011 | Introduce the Alembic baseline during foundation work, before feature tables evolve | accepted | target: every PostgreSQL schema object enters through migrations |
| D-012 | Use online Google Colab later as the execution surface for heavy experiments, not as the source of truth | accepted | target: training can be reproduced from repository code and committed configs |
| D-013 | Keep `memory.embedding` dimension-unconstrained until the embedding model is chosen | accepted | target: vector dimension follows measured model choice, not a guess |
| D-014 | Use the classifier target vocabulary `bug / feature / docs / question` | accepted | target: code, docs, data splits, and evals use one assignment-aligned label set |
| D-015 | Use Langfuse as the tracing backend | accepted | target: one Friday demo trace tree includes request root, tool call, retrieval span, token counts, latency, and an error path |
| D-016 | Start classifier fine-tuning with DistilBERT and freeze its lower 4 encoder blocks | accepted for first run | validation macro-F1 `0.7422`, full-test macro-F1 `0.9000`, 200-row macro-F1 `0.8647` |
| D-017 | Use a newer temporal test holdout plus deterministic stratified validation | accepted | target: preserve future-like test evaluation while keeping all four labels measurable during model selection |
| D-018 | Keep large classifier artifacts outside Git and commit only small run evidence | accepted | `run_manifest.json` and `metrics.json` are committed; model weights/checkpoints stay in Drive until MinIO is wired |
| D-019 | Use TF-IDF + Logistic Regression as the classical classifier baseline | accepted for comparison | validation macro-F1 `0.7414`, test macro-F1 `0.8847`, vocabulary size `50,000` |
| D-020 | Use OpenAI `gpt-4o-mini` as the LLM classifier baseline | accepted for comparison | 200-row macro-F1 `0.8671`; estimated run cost `$0.0179`; 95,571 total tokens |
| D-021 | Use a deterministic 200-row balanced comparison subset for the three-way classifier comparison | accepted | 50 examples per class; SHA-256 `a14faed71a97718cd421fbd84f2ed4d584c3b13f275971fd2b1945429be88f2a` |

## Classifier target vocabulary

The Week 7 classifier predicts exactly four target labels:

- `bug`
- `feature`
- `docs`
- `question`

Use `docs`, not `documentation`, in code, datasets, prompts, metrics, and reports so the repository matches the project brief and downstream evals only have one canonical label name.

## Week 7 label mapping

The chosen repository has a clean near-match for the assignment vocabulary:

| Source label in `pandas-dev/pandas` | Classifier target |
| --- | --- |
| `bug` | `bug` |
| `enhancement` | `feature` |
| `docs` | `docs` |
| `usage question` | `question` |

Issues with none of those labels are excluded from classifier training. Issues with more than one target label are also excluded rather than forcing a misleading single-label target into the training data.

## Split policy

The assignment requires the **test** split to be strictly newer than train. We satisfy that with a temporal holdout that prioritizes the requested holdout size first and uses class-distribution drift only as a tie-breaker, so the test set stays large enough to evaluate meaningfully. Validation is then sampled deterministically and stratified from the older train/validation pool so sparse labels remain present during model selection instead of making validation impossible when a class disappears from one recent time window.

## Tracing backend

Use **Langfuse** for the project trace UI.

Why it fits this assignment:

- it is built for LLM conversations, tool calls, token accounting, and trace trees rather than only generic HTTP spans;
- it keeps the required Compose stack lean instead of adding another local observability service;
- it gives us a concrete Friday demo surface for one full conversation, including retrieval and failure branches.

The application still keeps request IDs and trace IDs in its own infra layer so logs, user-facing errors, and future Langfuse spans can join on the same identifiers instead of coupling the whole codebase to one provider.

## First fine-tuning experiment

The first encoder run is intentionally modest:

- base model: `distilbert-base-uncased`
- task: four-way issue classification
- freeze policy: lower 4 encoder blocks frozen; top 2 blocks plus classifier head trainable
- logger: Weights & Biases
- run name: `first-distilbert-freeze4`

The first corrected four-class Colab run completed with validation macro-F1 `0.7422` and validation accuracy `0.8135`. The later test evaluation on the temporal holdout produced test macro-F1 `0.9000` and test accuracy `0.9534`. On the balanced 200-row comparison subset, DistilBERT reached macro-F1 `0.8647`, essentially tied with OpenAI but without external API cost.

Evidence files:

- `model_server/classifier/runs/first-distilbert-freeze4/run_manifest.json`
- `model_server/classifier/runs/first-distilbert-freeze4/metrics.json`

Large model weights and checkpoints remain outside Git.

## Classical baseline

The classical comparison track uses TF-IDF word features with unigrams and bigrams, capped at `50,000` features, feeding a balanced Logistic Regression classifier. This gives the project a fast, cheap, explainable baseline before we defend a heavier transformer or LLM path.

The baseline uses the same `data/train.jsonl`, `data/val.jsonl`, and `data/test.jsonl` files as the transformer run. Its committed Colab evidence reports validation macro-F1 `0.7414` and test macro-F1 `0.8847`. This is strong enough to make the baseline non-trivial: the deployment decision must explain why any heavier model is worth more operational complexity than this fast baseline.

## OpenAI LLM baseline

The LLM comparison track uses OpenAI `gpt-4o-mini` with the Responses API and Structured Outputs. The baseline prompt receives only the issue title/body, not the GitHub labels, and returns a strict JSON object with `label`, `confidence`, and `rationale`. The JSON schema constrains `label` to exactly `bug`, `feature`, `docs`, or `question`, and the evaluator still validates the parsed label before scoring.

The notebook starts with a 50-example pilot to avoid accidental spend. The final comparison runs with `FINAL_RUN = True` on `data/test_200_balanced.jsonl`, a deterministic 200-row subset sampled from the full temporal test split. DistilBERT and TF-IDF keep their full-test evidence, but the fair three-way comparison uses this same smaller subset for all three models.



## 200-row classifier comparison results

All three classifier tracks have now been evaluated on `data/test_200_balanced.jsonl`, the same 200 examples sampled from the temporal test split.

| Track | Accuracy | Macro F1 | Weighted F1 | Throughput / cost note |
| --- | ---: | ---: | ---: | --- |
| DistilBERT freeze-4 | `0.8650` | `0.8647` | `0.8647` | `1.61` examples/sec on CPU in this Colab eval |
| TF-IDF + Logistic Regression | `0.8450` | `0.8465` | `0.8465` | `2577.4` examples/sec; cheapest local baseline |
| OpenAI `gpt-4o-mini` | `0.8650` | `0.8671` | `0.8671` | `0.80` examples/sec; estimated cost `$0.0179` for 200 examples |

OpenAI is narrowly strongest on macro-F1 on this balanced slice, but the margin over DistilBERT is tiny (`0.0024`) and it is much slower/cost-bearing. TF-IDF is weaker but dramatically faster and simpler. The next decision is the deployment choice, not more training.

## Balanced 200-row classifier comparison subset

The full temporal test split remains `data/test.jsonl` with 2,145 examples. Because the OpenAI baseline has direct token cost, the three-way comparison uses `data/test_200_balanced.jsonl`: 50 examples from each target class, sampled deterministically with seed `42` from the full test split.

This is not a new training split and not a replacement for full-test evidence. It is the shared, affordable comparison surface for DistilBERT, TF-IDF, and OpenAI. The later 25-example golden set remains separate and human-reviewed.
