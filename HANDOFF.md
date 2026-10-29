# Saved checkpoint — 2026-10-29

Repository: `aamodbhatt/constraint-recovery`, branch `main`.
Code checkpoint: `4acf7bb1fbf3d3b092c40aa2859fc422ef5735f1`.

## User objective and operating constraints

Build a substantial applied-AI/research tool with real mathematics and a credible GitHub/demo story. The selected project recovers inspectable structural constraints from existing scientific SVGs and preserves accepted relationships through edits. Do not claim that constraint layout or AI diagram editing is new, that a learned advantage has been established, or that a paper is ready.

The user authorized ongoing work and pushes, with a stop guard at 5% remaining usage. During this run the five-hour window reset before that threshold. A clarification about continuing into the new window was offered; with no response, the current tested checkpoint was completed and this handoff saved. Recheck live usage on continuation; do not assume the historical values remain current. No reset credit was consumed manually.

Cloud GPU work was authorized after a sizeable local checkpoint, subject to a measured need and bounded experiment. **No cloud resource was started and no GPU credit spent.** The existing endpoint pilot trains in a fraction of a second on CPU. Do not provision a GPU just because the infrastructure checkpoint is now large.

## What is implemented

- Strict SVG recovery, reviewed graph corrections, CPU MILP placement, fitted text, explicit branch insertion, serialization/re-import checks and portable reports.
- Opt-in `--source-preserving` static subset: CSS cascade/inheritance, positive uniform transforms, nonzero viewBox origins and quadratic/cubic connector recovery. Original definitions, source hierarchy and paint survive supported edits. Curves are rerouted as line segments. This is not arbitrary SVG editing.
- A non-rendering `inspect` inventory for rejected figures.
- A shared orthogonal visibility-grid router with center ports, eight-unit clearance, bend-aware Dijkstra search and explicit budgets. The old templates remain available.
- Independently checkable witnesses for oversized nodes, rectangle area, positive flow cycles and excessive flow-path spans. `check-witness` does not invoke a solver.
- Local endpoint `review`, source-hash-bound attachment choices and explicit override evidence.
- SHA-256-bound reusable graph sidecars. Output sidecars bind to the newly written SVG, and reviewed graphs can resolve ambiguous ownership before automatic inference. Legacy unbound graphs remain accepted with a warning.
- Repeated-edit diagnostics with reuse, fresh recovery, direct attributes, topological strip, ELK and ELK-plus-repair controls, plus a portable walkthrough.
- Offline browser geometry for text, transforms and referenced instances, with source scripts disabled and secondary file/network requests blocked.
- Compound-object `annotate` workflow: original source in an image context, primitive click/lasso/checklist selection, pan/zoom, explicit roles and relations, unknown/ambiguous status, JSON download/resume, source binding and coverage validation.
- Version 2 annotation schema and an explicitly scripted **agent-reviewed** authored fixture. No external human labels were created.

## Validation and results

- Latest local Python suite: **143 passing tests**.
- Browser integration passes review/download/edit, source-ID collisions, inert source text, 24-unit font scaling and text containment, affine/rotation/use measurements, blocked source scripts and requests, compound grouping/download/resume, click/lasso/zoom, and an independent pixel check of the coordinate projection.
- Python wheel built successfully; the annotation HTML template is included as package data.
- The final code CI run is [40878142485](https://github.com/aamodbhatt/constraint-recovery/actions/runs/40878142485). Check its final status rather than assuming this note proves it passed. Earlier checkpoints were green on Python 3.11/3.12, ELK and browser jobs.
- Original 30-case synthetic layout benchmark: solver 30/30, fixed-placement baseline 20/30.
- Paired routing diagnostic: visibility solves six feasible authored cases; templates solve one with the same clearance. Both reject the blocked seventh case.
- Sequence pilot: reuse, fresh recovery, topological strip and ELK repair all complete 30/30 feasible steps across five sequences and reject five final impossible requests. ELK-only completes 12 steps before fixed-canvas overflow. This is a small synthetic diagnostic; it does not establish a reuse or learned advantage.
- Synthetic endpoint ranker ties the stronger tangent-aware heuristic. Softmax scores are uncalibrated and zero observed accepted errors is not a correctness guarantee.
- External development prefix: 20 published test rows, 19 available SVGs and one missing source. **Complete-figure editing support remains 0/19.** Browser geometry measures all 1,429 primitives, including 511 text envelopes; 134 text envelopes lie inside multiple non-background rectangle envelopes. Two secondary resources are blocked.
- Nineteen private, unlabelled compound-annotation views were built. **Zero external annotations or independent human ground-truth claims were created.** A built view is not an editing or rendering-fidelity result.

## Reproduce locally

Use the repository `.venv` because the SVG extra is installed there. Node is available through the host PATH. Optional JavaScript dependencies are pinned: ELK 0.12.1 and Playwright 1.62.1.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python benchmarks/run.py --output artifacts/benchmark.json
.venv/bin/python benchmarks/compare_routing.py --output artifacts/routing.json
.venv/bin/python benchmarks/run_sequences.py --elk --output artifacts/sequences.json
PYTHON=.venv/bin/python node benchmarks/browser_check.cjs
```

For a fresh environment, follow README installation including `pip install -e '.[test,svg]'`, `npm ci --ignore-scripts` and `npx playwright install chromium`. CI repeats the core suite and integration checks. The JSON Schema contract is checked through the test extra.

Private external data already exists locally:

```sh
.venv/bin/python benchmarks/audit_external.py --rows 20 --extended --inventory \
  --cache-dir .cache/external --offline --output artifacts/audit.json
node benchmarks/measure_external.cjs --rows 20 --output artifacts/geometry-audit.json
.venv/bin/python benchmarks/build_external_annotations.py --rows 20 \
  --output artifacts/annotation-view-audit.json
```

`.cache/external/` stores source responses; `.cache/browser-geometry/` stores complete geometry; `.cache/annotation-views/` stores annotation pages and SVG copies. These are ignored. **Do not commit them.** Upstream rights vary by source paper. Public demos and screenshots use authored MIT-licensed examples only.

## Files to read first

- `README.md` and `ROADMAP.md`: executable scope and remaining milestones.
- `docs/research-plan.md`: hypotheses, stronger controls, split policy and research gate.
- `docs/compound-annotation.md`, `data/README.md`, `data/annotation-v2.schema.json`: annotation protocol and limitations.
- `docs/source-preserving.md`, `docs/routing.md`, `docs/conflict-witnesses.md`: mathematics and implementation limits.
- `docs/edit-sequences.md`: positive results and important ties with simple baselines.
- `results/`: complete diagnostic records and explicit denominators.

Local demos: `docs/demo/sequence/index.html`, `docs/demo/attachment-review.html`, `docs/demo/primitive-annotation.html` and `docs/demo/styled-portrait.html`. A simple server on 127.0.0.1:8765 may still be running; verify availability before relying on it. The HTML tools also work as local files.

## Next substantive work

1. Obtain independent role/object/relation annotations and retain ambiguity. The current prefix is development data, not a fresh test set. Keep different figures/revisions from the same source paper together in any split. Do not count agent-generated fixture labels as human truth.
2. Implement a conservative source-preserving **compound-node adapter** from measured primitives and reviewed version 2 objects. The annotation format is not yet an editing adapter. Begin with rigid translations and protected unselected artwork on authored rich fixtures. Preserve source hierarchy/styles, avoid reparenting that changes CSS, and independently remeasure the serialized SVG. Explicitly reject shared parts, unresolved effects or unsupported arrow constructions.
3. Demonstrate actual editing coverage on a rights-checked external subset before adding another learned model or a larger demo layer.
4. Train a small contextual role/relation model only after splits/labels are fixed, and compare with tangent-aware geometry and source metadata. Use a measured bottleneck to justify any GPU experiment.

An edit request is not evidence that the true source graph makes the requested layout feasible. Do not remove graph hypotheses or relationships merely to make an edit succeed. A genuine cycle may require an honest refusal. No novelty, human-intent or pixel-level guarantee is established by the current checker.
