# Milestones

## M0 — executable local baseline

- [x] Strict supported SVG import and explicit graph recovery.
- [x] Reviewed relationship corrections through JSON.
- [x] Relabeling, font-size changes, canvas changes and optional flow layout.
- [x] CPU mixed-integer placement and obstacle-aware candidate routing.
- [x] Export/re-import validation and machine-readable evidence.
- [x] Reproducible synthetic comparison and adversarial failure tests.
- [x] CLI and local HTML inspection report.

## M1 — research-grade data and evaluation

First pilot delivered: [phase findings](docs/phase1-findings.md). This milestone remains incomplete: the external compatibility audit is not a gold relationship test set.

- Annotate a real, licensed SVG subset and document unsupported input frequency.
- [x] Add an opt-in source-bound importer/exporter for static CSS, uniform transforms and Bezier connectors; preserve source definitions and hierarchy. [Scope and audit](docs/source-preserving.md). External complete-figure support remains 0/19 available development SVGs.
- Separate text-to-node, endpoint, containment, alignment and ordering targets.
- [x] Add explicit branch insertion while preserving existing node/edge identities and protected labels.
- Build independent relationship annotations; avoid scoring inferred rules against themselves.
  - [x] Resumable compound-object annotation UI, source-bound version 2 records, explicit unknown/ambiguous labels, primitive coverage and structural/provenance validation.
  - [ ] Obtain independently reviewed external labels; the authored agent-reviewed workflow fixture is not that dataset.
  - [x] Coverage-aware comparison/adjudication tool with permutation-invariant grouping, full-part matching and explicit unscorable relationships; scripted diagnostics do not establish human agreement. [Workflow](docs/annotation-comparison.md).
  - [x] Reviewed rigid compound-node adapter with affine pose preservation, original attachment offsets, derived-state provenance and fresh browser verification on an authored rich fixture. [Scope](docs/compound-editing.md).
  - [ ] Establish actual external compound-edit coverage and unsupported-case denominators.
    - [x] Fixed five-figure author-published development pilot, retained initial failures, explicit agent-reviewed assumptions and direct-edit controls: 3/5 two-move sequences pass; unresolved context and mid-marker rerouting remain declined. [Results and limits](docs/native-pilot.md).
    - [ ] Independent human review and an untouched authoring-origin holdout; crossing/shared-segment safety beyond node envelopes.
- Add strong heuristics + ELK and direct source-editing baselines.
  - [x] Tangent-aware endpoint heuristic and a pinned ELK layout configuration.
  - [ ] Direct source-editing baseline and independent real-diagram labels.
- Evaluate edit sequences, style/composition holdouts and impossible requests.
  - [x] First fail-stop sequence pilot with fresh recovery, reuse, topological-strip, ELK and ELK-repair controls. [Findings](docs/edit-sequences.md). Reuse has no completion advantage on these motifs.
  - [ ] Independently annotated external sequences and held-out composition/style evaluation.
- [x] Replace finite routing candidates with a bounded orthogonal visibility-grid router; retain four center ports and explicit clearance/search limits. [Paired diagnostic](docs/routing.md).
- Add browser-measured font geometry and rendered visual regression coverage.
  - [x] Add real-browser checks for inverse font scaling, text containment and the interactive attachment-review workflow on authored examples.
  - [ ] Expand rendered checks to external figures and use measured glyph bounds during layout.
- Add ambiguity review and minimal conflicting-constraint explanations.
  - [x] Independent arithmetic witnesses for positive flow cycles, path-span, node-size and area bounds. [Scope](docs/conflict-witnesses.md).
  - [ ] Minimum conflicting sets/repairs and container/role ambiguity review.
  - [x] Add local endpoint review with candidate evidence and source-bound override manifests. This is not yet general container/role review or an independently annotated dataset.

## M2 — learned recovery on local hardware

First component delivered: conditional-logistic endpoint ownership, trained on synthetic scenes with opt-in runtime use. It ties the stronger geometric rule, so there is no established learned advantage yet.

- Generate layouts from known programs, including intentional vs incidental alignments.
- Train a compact relation model with documented features and held-out generator families.
- Compare learned recovery with M0 and oracle constraints.
- Measure calibration and when the model should abstain or ask for a relation correction.
- Report genuine external SVG errors, rather than only clean generated chains.

## Cloud GPU gate

The user has authorized moving to cloud GPUs after a sizeable local checkpoint. No cloud resources are needed or started for M0.

Before spending credits, establish a reproducible data split, a local learned baseline, a measured accuracy or training bottleneck, and a bounded experiment specifying hardware, estimated cost, stop conditions and saved outputs. Use the GPU only if it addresses that measured bottleneck. Maintain the user's remaining credit budget; the earlier $200 Runpod balance is historical context, not a verified current balance or authorization to spend it all.

## Handoff

Run the commands in README.md before making new claims. Next work should address the zero-support external audit: broader, non-destructive SVG ingestion and independently reviewed relationships. The first local learned model is available, but ties a strong rule. Do not market synthetic results as comparison with contemporary AI diagram editors. No GPU bottleneck has been demonstrated.
