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
- Separate text-to-node, endpoint, containment, alignment and ordering targets.
- [x] Add explicit branch insertion while preserving existing node/edge identities and protected labels.
- Build independent relationship annotations; avoid scoring inferred rules against themselves.
- Add strong heuristics + ELK and direct source-editing baselines.
  - [x] Tangent-aware endpoint heuristic and a pinned ELK layout configuration.
  - [ ] Direct source-editing baseline and independent real-diagram labels.
- Evaluate edit sequences, style/composition holdouts and impossible requests.
- Replace finite routing candidates with a robust visibility-graph router.
- Add browser-measured font geometry and rendered visual regression coverage.
- Add ambiguity review and minimal conflicting-constraint explanations.

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
