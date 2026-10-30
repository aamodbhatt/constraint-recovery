# Blinded recovery against source-declared bindings

The source-reference pipeline now runs locally on CPU. It extracts predictions from visible primitive geometry, freezes them, and then loads a separate source graph for scoring. No manual annotator, model API or cloud GPU is required for this checkpoint.

The [protocol](../data/source-recovery-protocol.json) was committed in `cec8489` before the pipeline outcomes were measured. The two original examples were already inspected during source discovery: this remains a development probe, not an untouched holdout. [Saved report](../results/source-recovery.json).

## Data separation

```text
Pinned original SVG
  ├─ known DTD normalization → offline source render
  ├─ graph/semantic metadata removal → offline blinded render
  │    → numeric primitive observations → separate predictor process
  │    → frozen prediction bytes + hash
  └─ source-declared graph + restricted exporter mapping
       → separately bound reference → scorer
```

Blinding removes the embedded authoring graph, nonvisual metadata, scripts, semantic data attributes and external navigation links. IDs/classes are replaced with opaque names; functional fragment references are rewritten. Stylesheet selector rewriting is outside scope and causes refusal. Unknown DTDs remain refused; only the known legacy SVG1.1 declaration is removed and logged. Existing editor safety guards are unchanged.

A browser with source scripts disabled and secondary requests blocked measures both variants. Full viewport RGBA pixels must match exactly within that browser. Blocked resources prevent a scored intact-artwork case even when both variants show the same missing image. This checks local rendering preservation, not semantic fidelity, source authenticity or cross-browser identity.

The predictor receives only a strict JSON whitelist: canvas size, shuffled opaque primitive IDs, shape tags, numeric bounds/path endpoints/tangents and paint/closure booleans. It receives no graph, source/semantic IDs, classes, text, hierarchy, original SVG or filename. It runs in a separate directory containing its observations and output. **This is an auditable input boundary, not an adversarial OS sandbox.** A different untrusted model would need stronger process controls.

## Reference grounding without prediction guesses

The scorer uses a narrow flat draw.io exporter contract, based on source cell order and painted shaft/head/node blocks. It supports absolute rectangular/rounded-rectangle and rhombus vertices, explicit block end heads and optional label groups. Every node's browser envelope must match its source dimensions, and all node positions must agree under one common translation within0.2 units. Unaccounted drawing elements, missing/invisible parts, nested/relative vertices or unknown styles refuse complete grounding.

An edge's identity comes from that export trace, not from the node chosen by the predictor. Source/target bindings come from the stored source graph. The head must be at the terminal end of the measured shaft. The contract is deliberately restricted; a graph stored in an SVG is not sufficient by itself to prove that every visible mark has been correctly grounded.

Source declarations are reference evidence, not independently verified human intent. General semantic direction, latent alignments, grouping and composition outside the encoded graph are not evaluated. HTML labels remain visible and unmodified, but this read-only pipeline does not make them editable.

## Fixed geometry baselines

Closed visible primitives at least16 units wide and12 high form node candidates; stroked, unfilled, open paths/lines longer than2 units form shaft candidates. No oracle boxes or candidate node list is supplied.

For candidate envelope `B` with width `w` and height `h`, and endpoint `p`:

```text
nearest-boundary score = distance(p, boundary(B)) / sqrt(w*h)
tangent-aware score    = nearest-boundary score + 0.25 * (1 - alignment)
alignment              = cosine(outward endpoint tangent, center(B) - p)
```

Outside a rectangle, distance is Euclidean distance to its closest point; inside, it is distance to the closest face. Equal best scores within1e-9 abstain. Axis-aligned envelopes approximate the boundaries of shaped nodes. Scores/margins are geometric rankings, not calibrated probabilities. These are classical controls; no model is fitted here.

## First result: retain the failure and the tie

| Selected development source | Outcome |
|---|---|
| Published lamp flowchart |6/6 reference vertices and5/5 shafts grounded and detected; both baselines recover10/10 endpoint bindings and5/5 complete pairs |
| Connection-method tutorial |Unscored: four secondary image resources are blocked; its source graph also declares no edges |

Only **1/2 selected figures is scored**. A10/10 conditional result on one small figure is not a population accuracy estimate, a learned advantage or a representative benchmark. The original five-source native editing pilot and19-source reconstruction audit retain their separate denominators.

The [offline CI fixture](../examples/source-reference.svg) is authored for this project. It tests the workflow; its2/2 endpoint result is not external performance. CI does not download or redistribute the external examples.

## Falsification checks

- Changing a hidden source binding changes the reference while preserving the blinded SVG, numeric observations and prediction bytes exactly.
- Reversing the observation list preserves endpoint decisions.
- A deliberately incorrect endpoint reduces the scorer's correct-endpoint and complete-pair counts. Modified diagnostic predictions are excluded from reported performance.
- Source/paint pose disagreement, misplaced heads, unmeasured parts, semantic fields in the numeric contract and mismatched observation hashes are rejected.
- Full rendered RGBA comparison reports zero changed pixels for the scored flowchart and the authored fixture in the local browser.

Hashes bind the supplied experiment artifacts; they do not authenticate an arbitrary external file or prove a self-reported human identity.

## Reproduce

```sh
# Acquire the pinned sources once; use --ca-file when required by the host:
.venv/bin/python benchmarks/audit_source_oracles.py
# Run the external development probes from their private cache:
PYTHON=.venv/bin/python node benchmarks/run_source_recovery.cjs
# Offline authored workflow regression used in CI:
PYTHON=.venv/bin/python node benchmarks/source_recovery_check.cjs
.venv/bin/python -m pytest -q
```

Complete original/blinded artwork, measurements, private grounding and predictions remain under ignored `.cache/` and `artifacts/`. Public reports contain hashes, counts and outcomes. The source-recovery worker is separate from the SVG editing adapter; it neither exports edited diagrams nor expands editing compatibility.

The next experiment needs a larger, predeclared source-program pool and an unseen authoring-origin split. Broaden grounding while retaining every exclusion, then compare recovery and correction budgets. Runpod becomes useful only after that data pipeline and a local model expose a measurable training or inference bottleneck, with a bounded cost/stop plan. No GPU resource or credit has been used.
