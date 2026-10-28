# Endpoint attachment ranker

`attachment-ranker.json` is a small, inspectable conditional-logistic model trained locally on synthetic noisy endpoint scenes. It is not a language model or a neural network, and does not infer scientific meaning.

Each observation contains an endpoint, a visible connector direction pointing toward the candidate owner, and six possible rectangular nodes. Nine geometric features rank candidates. Supervision comes from the scene generator's selected owner, not from the inference heuristic.

Reproduce:

```sh
PYTHONPATH=src python benchmarks/learn_attachments.py
```

The script uses distinct train, validation and test seeds and holds the staggered scene family out of training and threshold selection. It chooses an empirical abstention threshold on validation data. Softmax scores are uncalibrated; zero observed accepted errors is not a reliability guarantee, especially under distribution shift. Calibration error is reported.

Enable explicitly:

```sh
constraint-recovery recover examples/pipeline.svg \
  --endpoint-model models/attachment-ranker.json \
  --output artifacts/learned-recovery.json
```

The geometric recovery path remains the default. Low-score or distant predictions are rejected; invalid or directionless observations also abstain. Model JSON is validated and loaded without pickle or executable deserialization.

Current result: the learned ranker improves on nearest-boundary matching but ties a stronger tangent-aware heuristic on both the in-family and held-out-family tests. **These results do not establish a need for learning.** See `results/attachment-learning.json` and `docs/phase1-findings.md`.
