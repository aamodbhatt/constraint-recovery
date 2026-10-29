# Checkable explanations for impossible requests

Some edit failures can be explained by a small arithmetic witness rather than a solver status alone. The preflight runs **after label/font fitting**, so it reasons about the node sizes actually passed to layout. A separate checker verifies the witness before the CLI saves it.

```sh
# This request intentionally exits with status 2 and writes no new SVG:
constraint-recovery edit examples/pipeline.svg --flow vertical --height 200 \
  --output artifacts/impossible.svg

# Check the saved arithmetic without invoking a layout solver:
constraint-recovery check-witness artifacts/impossible.failure.json
```

The supplied chain needs at least `64 + 24 + 64 + 24 + 64 + 2×16 = 272` units of height, exceeding the requested 200. The [saved witness](demo/impossible.failure.json) records the relevant node/edge IDs, required height, available height, shortfall and fitted graph. Increasing the height to that lower bound removes this particular contradiction; it is not a general promise that all other constraints will then be feasible.

## Supported witnesses

Let `p_v` be the top/left coordinate of node `v`, `s_v > 0` its fitted extent along the requested flow axis, `g ≥ 0` the gap, `m` the padding and `L` the canvas extent. The flow inequalities are

`p_v ≥ p_u + s_u + g` for every directed edge `u → v`,

with `m ≤ p_v ≤ L − m − s_v`.

1. **Positive flow cycle.** Summing around a cycle cancels every position, giving `0 ≥ Σ(s_u + g) > 0`. The witness identifies the cycle and verifies each referenced edge and the positive sum. A cycle is allowed when flow is `free`; it is the requested consistent geometric flow that creates the contradiction.
2. **Flow span.** Along a path, telescoping gives `L ≥ 2m + Σs_v + (k−1)g`. On a DAG, dynamic programming finds the longest such path. The checker only needs to establish the reported path and its arithmetic; it does not need to trust the dynamic program or prove maximality.
3. **Single-node canvas bound.** A fitted width/height exceeds its corresponding padded canvas extent.
4. **Area bound.** The sum of fitted rectangle areas exceeds the padded canvas area. Gaps can only make packing harder, so this remains a valid necessary condition while ignoring them.

A SHA-256 digest binds the witness to the supplied canvas, node sizes, directed graph, flow, gap and padding. The independent checker verifies the referenced inequalities and numbers; it does not call the witness generator or a solver. The saved graph is the subject of the certificate. Recovery correctness and author intent are separate questions.

The tests also compare flow-witness detection against independently formulated linear-program feasibility on 100 seeded small graphs. That checks the flow subproblem, not full two-dimensional placement or routing.

## Limits

These witnesses are not minimum unsatisfiable cores or minimum repairs. More than one contradiction may exist; the first supported witness is returned. Rectangle-packing infeasibility, limited routing ports, numerical limits and timeout failures can still have no witness. **No witness does not mean feasible.** The tool never silently removes a recovered relationship to make an edit succeed. Failure reports are separate `.failure.json` files; as with pre-existing SVG outputs, check the command exit status because older artifacts can remain at the same destination.
