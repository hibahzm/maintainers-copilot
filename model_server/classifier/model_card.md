# Classifier Model Card

## Architecture
- First experiment family: `distilbert-base-uncased`
- Task head: four-way sequence classification
- Labels: `bug / feature / docs / question`
- Freeze policy: lower 4 DistilBERT encoder blocks frozen; top 2 blocks and classifier head trainable
- Status: planned first run, not yet trained

## Dataset
- Training data hash: _TBD_
- Validation data hash: _TBD_
- Test split rule: strictly newer timestamps than train

## Hyperparameters
- Max length: `384`
- Learning rate: `2e-5`
- Train batch size: `16`
- Eval batch size: `32`
- Epochs: `3`
- Weight decay: `0.01`
- Warmup ratio: `0.1`
- Seed: `42`

## Metrics
| Metric | Value |
| --- | --- |
| Macro F1 | TBD |
| Accuracy | TBD |
