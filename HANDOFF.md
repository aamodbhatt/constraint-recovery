# Saved checkpoint — 2026-10-30

Repository: `aamodbhatt/constraint-recovery`, branch `main`.
Latest feature checkpoint: `c6e329b5a78b8e8796eafe4245c565b8448dae3f` (source-bound annotation previews). A following checkpoint strengthens the public-state audit and saves this handoff; consult `git log` for its exact revision.

## User objective and operating constraints

Build a substantial applied-AI/research tool with inspectable mathematics and a credible GitHub/demo story. Recover structural constraints from scientific SVGs and preserve accepted relationships through edits. Do not present classical routing/layout, scripted labels, or a fixture demonstration as research novelty, independent ground truth or a learned advantage.

The user authorized autonomous work and pushes, with a stop guard at 5% remaining usage, and explicitly authorized continuing into a new usage window after a reset. Check live usage on continuation. Historical latest reading during this save: 86% of the five-hour window used, 14% weekly used. These are historical values, not current availability. No reset credit was consumed manually.

No Runpod/cloud resource was started and no GPU credit spent. The small endpoint pilot still ties a strong tangent-aware heuristic. Its training is trivial on CPU. GPU work needs a measured bottleneck and a bounded experiment.

A question about who can independently annotate a few figures was sent during this work; no answer had arrived at save time. Do not invent human labels or call agent review independent. The next study needs actual separate reviewers and an unseen source-paper holdout.

## New substantive results

### Native author-published SVG development pilot

- Froze five original SVG files from two Distill article repositories, source revisions, Git blobs, SHA-256 hashes, attribution, agent annotations and edit requests before extending the adapter. Kept all five failures in the initial checkpoint. This is a purposive development set, not representative or held out.
- Three 2016 Olah/Carter RNN figures are CC BY 2.0; two 2021 Daigavane/Ravindran/Aggarwal GNN figures are CC BY 4.0. Original source bytes remain unchanged in `data/native-pilot/original`. See `data/native-pilot/ATTRIBUTION.md` and `data/native-pilot-selection.json`.
- Added explicit reviewed markerless shafts/separately drawn end heads, preserving their relative anchors and head artwork, and whole-connector rigid moves preserving curves and markers. Mid-marker rerouting, unresolved context and unsupported head rotations remain refused.
- **3/5 complete two-move sequences; 6/10 planned moves accepted; eight attempted moves; three checked out-of-canvas refusals on supported sequences.** The external-memory figure remains blocked by protected unresolved context; the graph-tasks figure by mid-marker rerouting. Unsupported refusals are not feasibility proofs.
- First-move direct controls: node-only accepts 0/5; a stronger translation rule also carrying equal-motion connectors accepts 1/5, tying the editor on that case. These are small deterministic controls, not comparisons with expert users or current AI diagram editors.
- `results/native-pilot-initial.json` retains initial failures; `results/native-pilot-visibility.json` retains the earlier shared-route checkpoint; `results/native-pilot.json` records the latest fixed requests, source/annotation hashes and implementation-file hashes. Hashes are reproducibility bindings, not authenticity attestations.

### Mathematics and independent shaft checks

- `channel.py` constructs bounded ordered orthogonal tracks for 2–32 compatible parallel connectors. Port incidence yields precedence inequalities; a DAG topological order and longest-path ranks allocate tracks. Cycles, duplicate columns, insufficient capacity or obstacles decline this candidate and retain visibility routing as fallback.
- `edge_check.py` reads actual serialized segments independently of the planner and detects contacts/shared segments outside the accepted endpoint envelopes. A global two-million segment-pair budget refuses incomplete checks. It does not cover stroke/head extents, unchanged edges, self contacts or topology hidden inside endpoint envelopes.
- Same native seven-link source and two fixed moves: independent visibility routing has **8 then 9 contacting shaft pairs**; ordered tracks have **0 then 0**. Both modes complete both edits. This is a classical routing refinement and a local separation result, not a novel algorithm or full topology certificate.
- `docs/channel-routing.md` documents inequalities, classical references and scope; `results/parallel-routing.json` retains both modes.

### Annotation comparison and independent review tools

- Five unlabelled review pages start with no objects, roles or relationships. Advanced imported shaft/head assumptions are displayed and retained on download. Review metadata is never promoted from agent to human.
- New `compare-annotations` command: exact source/inventory matching; visible joint/individual primitive coverage; role agreement on the confirmed joint domain; ID-invariant adjusted Rand index and variation of information; full-part IoU linear assignment; relation comparisons only when endpoints have exact part/role grounding; unknown/missing positives are not false negatives or ground truth.
- Portable comparison view shows the same source in both panes, selectable part envelopes, unmatched objects, a common crop and disclosure of unscorable relations/resource limitations.
- Public demonstration uses **scripted perturbations of one authored fixture**, not two independent annotators: renamed IDs ARI1; split card/labels ARI28/33 with role agreement0.8; leaving the decoder unknown yields conditional ARI1 at only7/10 joint coverage. No real human agreement estimate exists.
- See `docs/annotation-comparison.md`, `results/annotation-comparison-fixtures.json` and `docs/demo/annotation-comparison.html`.

### Preview repair and published-byte audit

- A pixel regression exposed stretched annotation previews for SVGs lacking explicit dimensions. Repaired measurement with opt-in `--snapshot`: a bounded PNG from the same disabled-script/offline browser viewport, source/image hashes, CSS dimensions and pixel dimensions. Annotation/comparison validates those supplied bindings and uses the snapshot. Explicitly sized, stylesheet-free sources retain a legacy inert SVG-image fallback; ambiguous sizing without a snapshot now refuses with a remeasurement instruction.
- Regenerated all five public native review pages and the comparison demo. Native pixel probes on two implicit-size sources and the existing styled-fixture probe pass. No independent human labels were collected with the older pages. Few pixel probes are regressions, not a rendering certificate.
- Regenerated all **19 private reconstructed-SVG review pages** with snapshots under ignored `.cache`. The missing twentieth source remains missing. `artifacts/geometry-snapshot-audit.json` and `artifacts/annotation-snapshot-audit.json` retain this local rebuild; zero annotations were created. Do not redistribute mixed-rights cache contents.
- `published_examples_check.cjs` freshly measures the **eight SVG files actually distributed** in the native workspace, checks bound reports/histories, immutable original agent annotations, styles, poses, attachments, full reconstructed derived states and parallel-contact observations. This avoids assuming regenerated artifacts equal public downloads. See `results/published-examples-check.json`.

## Provenance correction: keep the two external tracks separate

The original SciDiagramRevision development prefix is **19 available reconstructed figures from20 rows**, not proven original author-written SVGs. Its paper describes an LLM-assisted vector reconstruction pipeline in section3: <https://arxiv.org/html/2607.15272v1>. Original source-paper rights are mixed; the first five source papers checked carried arXiv nonexclusive licenses. Full sources/text/measurements remain private.

The original track still has **0/19 complete-figure editing support**. Browser geometry measures1,429 primitives and511 text envelopes,134 inside multiple non-background rectangles; two secondary resources are blocked. The native pilot's3/5 result does not replace this denominator.

## Existing foundation retained

Strict SVG recovery and reviewed corrections; CPU MILP placement with L1 displacement; fitted text and branch insertion; source-bound graphs; reusable repeated-edit state; independent size/area/flow-cycle/span witnesses; endpoint review; source-preserving static SVG adapter; visibility-grid routing; rich compound rigid moves with affine ancestry, text and symbol instances; fresh browser pose/style/attachment verification; responsive sequence workspace and redesigned README.

Synthetic results remain diagnostics: layout30/30 vs fixed placement20/30; routing6/6 feasible authored cases vs templates1/6; sequence reuse/fresh recovery/strip/ELK repair each30/30 feasible moves, ELK-only12 steps before overflow. No reuse or learned advantage follows from these ties.

## Validation and reproduction

Latest local suite: **219 passing Python tests**. Includes annotation metric edge cases, source binding/coverage, routing families, independent segment contacts, malformed snapshot/digest/size failures and conservative SVG guards. Browser annotation, native editing, damaged-candidate rejection, native workspace/mobile/pixel probes, comparison controls and all eight public SVG exports pass locally. A wheel builds and its new modules/browser assets import in isolation.

Feature CI: <https://github.com/aamodbhatt/constraint-recovery/actions/runs/40946373419> for `c6e329b`; check its live conclusion and the following commit's run before claiming final CI success. Earlier comparison checkpoint `bf0accf` passed all four jobs in40943787354.

```sh
.venv/bin/python -m pytest -q
PYTHON=.venv/bin/python node benchmarks/browser_check.cjs
PYTHON=.venv/bin/python node benchmarks/compound_check.cjs
PYTHON=.venv/bin/python node benchmarks/native_pilot_check.cjs
PYTHON=.venv/bin/python node benchmarks/compare_parallel_routing.cjs
PYTHON=.venv/bin/python node benchmarks/published_examples_check.cjs
PYTHON=.venv/bin/python node benchmarks/native_presentation_check.cjs
PYTHON=.venv/bin/python node benchmarks/annotation_comparison_check.cjs
```

Use the repository `.venv`; Node is on PATH. Optional Node dependencies are pinned (ELK0.12.1, Playwright1.62.1). In subprocess wheel tests use `Path(sys.executable).absolute()`, not `resolve()` which follows the venv symlink and loses its dependencies.

Regenerate public annotation previews before labeling:

```sh
PYTHON=.venv/bin/python node benchmarks/measure_native_pilot.cjs
.venv/bin/python benchmarks/build_native_pilot_demo.py
node benchmarks/measure_svg.cjs examples/compound.svg artifacts/comparison-geometry.json --snapshot
.venv/bin/python benchmarks/build_annotation_comparison.py
```

Private reconstructed-SVG review packet:

```sh
node benchmarks/measure_external.cjs --rows 20 --snapshot --output artifacts/geometry-snapshot-audit.json
.venv/bin/python benchmarks/build_external_annotations.py --rows 20 --output artifacts/annotation-snapshot-audit.json
```

Do not commit `.cache`, full private measurements or unlicensed external screenshots. Public Distill artwork retains separate attribution/CC licenses; project MIT terms do not override them. Snapshot hashes validate supplied evidence, not semantic fidelity or identity.

## Read first / next substantive gate

Read `README.md`, `ROADMAP.md`, `docs/native-pilot.md`, `docs/channel-routing.md`, `docs/annotation-comparison.md`, `docs/compound-editing.md`, `docs/research-plan.md` and `data/README.md`.

1. Obtain independent role/object/relation labels using the unlabelled packet. Have reviewers label an overlapping subset separately before inspecting each other's or agent labels. Retain ambiguity and quantify coverage before agreement.
2. Freeze an unseen, rights-checked source-paper holdout and requests before adapter changes; keep all figures/revisions from a paper in one split. Current native figures are CI regressions and cannot become an untouched holdout retroactively.
3. Evaluate actual recovery/calibration and edit validity under independent labels and stronger controls. Broaden edge topology checks beyond the existing same-endpoint parallel groups; do not turn warning absence into a global proof.
4. Train contextual role/relationship models only after labels/splits are fixed. Justify GPU spending with a measured local bottleneck. Draft research claims only after the held-out evidence warrants them.

Local demo entry points: `docs/demo/native-pilot/index.html`, `docs/demo/native-pilot/review/index.html`, `docs/demo/annotation-comparison.html` and `docs/demo/sequence/index.html`. A local server on127.0.0.1:8765 may still be running. HTML views also open locally.
