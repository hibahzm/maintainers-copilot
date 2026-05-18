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
| D-010 | Use closed issues from `fastapi/fastapi` as the Week 7 dataset source | accepted | target: one stable repo source across the whole project |
| D-011 | Introduce the Alembic baseline during foundation work, before feature tables evolve | accepted | target: every PostgreSQL schema object enters through migrations |
| D-012 | Use online Google Colab later as the execution surface for heavy experiments, not as the source of truth | accepted | target: training can be reproduced from repository code and committed configs |
| D-013 | Keep `memory.embedding` dimension-unconstrained until the embedding model is chosen | accepted | target: vector dimension follows measured model choice, not a guess |
| D-014 | Use the classifier target vocabulary `bug / feature / docs / question` | accepted | target: code, docs, data splits, and evals use one assignment-aligned label set |

## Classifier target vocabulary

The Week 7 classifier predicts exactly four target labels:

- `bug`
- `feature`
- `docs`
- `question`

Use `docs`, not `documentation`, in code, datasets, prompts, metrics, and reports so the repository matches the project brief and downstream evals only have one canonical label name.
