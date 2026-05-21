# Project 7 - Maintainers Copilot

Repo: https://github.com/hibahzm/maintainers-copilot

Tag: v0.1.0-week7

Dataset: `pandas-dev/pandas` closed issues, 10,012 train / 2,145 val / 2,145 test

Classification - Classical: F1=0.8465 | Fine-tuned: F1=0.8647 | LLM: F1=0.8671

Deployment choice: `first-distilbert-freeze4` (`distilbert-base-uncased`) - because it is effectively tied with OpenAI on the balanced comparison set while avoiding per-call cost and external API dependency.

Embedding model: `intfloat/e5-small-v2` - chosen because it reached recall@10=1.0000 and MRR@10=1.0000 on the dense embedding comparison while staying small enough for the stack.

RAG - hit@5=1.0000 | MRR@10=0.9533 | Faithfulness=not scored | Answer relevancy=not scored

Long-term memory type: semantic

Tracing backend: Langfuse - chosen because it is built for LLM conversations, tool calls, token usage, and trace trees.

Widget bundle size: 62.93 KB JS gzipped; 65.21 KB total gzipped assets

LLM: OpenAI `gpt-4o-mini`

README contains: `ARCH.md`, `DECISIONS.md`, `RUNBOOK.md`, `EVALS.md`, `SECURITY.md`

Note: the committed eval evidence contains retrieval metrics, but no completed answer-quality scoring run for faithfulness or answer relevancy. `evals/eval_thresholds.yaml` defines a faithfulness target of 0.85, but that is a threshold, not an achieved metric.
