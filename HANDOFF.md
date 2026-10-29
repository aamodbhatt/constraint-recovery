# Saved checkpoint — 2026-10-29

Repository: `aamodbhatt/constraint-recovery`, branch `main`.
Latest checkpoint includes the README/workspace redesign and reviewed compound-node editing adapter. Consult `git log` for the precise code revision.

## User objective and operating constraints

Build a substantial applied-AI/research tool with real mathematics and a credible GitHub/demo story. The selected project recovers inspectable structural constraints from existing scientific SVGs and preserves accepted relationships through edits. Do not claim that constraint layout or AI diagram editing is new, that a learned advantage has been established, or that a paper is ready.

The user authorized ongoing work and pushes, with a stop guard at 5% remaining usage. The user explicitly answered **Continue working into the new usage window** after the earlier reset. Continue under that authorization while monitoring live usage; save, push and halt when 5% remains. Recheck usage on continuation rather than relying on historical values. No reset credit was consumed manually.

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
- Reviewed `edit-compound` rigid translations of rich node artwork: affine ancestors, text, circles and symbol instances; original relative connector anchors; conservative obstacles; independently checked serialized segments and fresh browser poses/styles. Original annotation review stays immutable in derived hash-bound state. [Exact scope](docs/compound-editing.md).
- Redesigned README and responsive sequence workspace, with desktop/mobile/rejected-request visual checks. Authored examples only; no public external-source redistribution.

## Validation and results

- Latest local Python suite: **160 passing tests**.
- Compound browser diagnostic passes two consecutive edits on rotated/bold/use artwork, review retention and hash binding, rejection without overwriting an earlier SVG, and rejection of a CSS selector activated by inserted transforms. Saved in `results/compound-integration.json`. This is an authored agent-reviewed fixture, not independent ground truth or external accuracy.
- Browser integration passes review/download/edit, source-ID collisions, inert source text, 24-unit font scaling and text containment, affine/rotation/use measurements, blocked source scripts and requests, compound grouping/download/resume, click/lasso/zoom, and an independent pixel check of the coordinate projection.
- Python wheel built successfully; browser bridge assets and the annotation HTML template are included as package data.
- Compound checkpoint `dc097ee` passed all four CI jobs in [40890725634](https://github.com/aamodbhatt/constraint-recovery/actions/runs/40890725634). Check the newest run for subsequent diagnostic additions; older green runs do not validate newer code.
- The expanded diagnostic rejects freshly measured damaged text, gradient definitions, rigid poses and detached endpoints; skew/nonuniform and reflected parent variants pass. The packaged wheel completes a browser-backed edit when run with the SVG extra installed. Presentation smoke checks are portable in `benchmarks/presentation_check.cjs` and run in CI.
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
PYTHON=.venv/bin/python node benchmarks/compound_check.cjs
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
2. Evaluate the implemented conservative **compound-node adapter** on independently reviewed examples and a rights-checked external subset. Current support is explicit rigid moves only; no automatic layout, relabeling, resizing, multipart arrow-label groups, moving containers or arbitrary SVG. Follow the documented source/style/pose verification boundary rather than relaxing checks just to obtain success.
3. Demonstrate actual external editing coverage and track failures before adding another learned model or a larger demo layer. Broad external complete-figure editing remains 0/19; the authored adapter fixture does not change that denominator.
4. Train a small contextual role/relation model only after splits/labels are fixed, and compare with tangent-aware geometry and source metadata. Use a measured bottleneck to justify any GPU experiment.

An edit request is not evidence that the true source graph makes the requested layout feasible. Do not remove graph hypotheses or relationships merely to make an edit succeed. A genuine cycle may require an honest refusal. No novelty, human-intent or pixel-level guarantee is established by the current checker.
