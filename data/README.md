# Evaluation data protocol

## What exists

- [Native SVG development pilot](../docs/native-pilot.md): a separately fixed five-figure, two-article selection with pinned author-published inputs and per-article Creative Commons notices. This is development data, not an untouched test set.

- `results/external-compatibility.json`: first 20 test rows from SciDiagramRevision, selected before measuring support. No source images or SVGs are redistributed.
- `benchmarks/learn_attachments.py`: programmatically labeled endpoint scenes. Train/validation/test use seeds 101/202/303; staggered layouts use seed 404 and are excluded from training and threshold selection.
- No independently annotated real-diagram relationship test set exists yet. A compatibility audit is not that test set.
- `results/browser-geometry-audit.json`: offline browser envelopes for all 19 available development sources, with full measurements kept privately in `.cache/`. This is geometry, not gold node/edge annotation. See [measurement scope](../docs/browser-geometry.md).

## External audit findings

The audited prefix contains 19 source SVGs and one missing source. The strict M0 parser accepts none. The report retains every row, source hash where available, and first rejection reason. It does not measure edit quality or claim representativeness of the whole dataset.

The upstream dataset declares `mixed-arxiv-source` licensing. Inspect each paper's reuse terms before redistributing an input or derived dataset. The audit keeps identifiers and compatibility results only.

The [benchmark's vectorization protocol](https://arxiv.org/html/2607.15272v1) reconstructs editable SVGs from paper figures using an LLM-assisted pipeline. These cached benchmark files are not established as the authors' native SVGs. Keep their provenance separate from the new author-published pilot.

Reproduce with:

```sh
PYTHONPATH=src python benchmarks/audit_external.py --rows 20
```

If your Python installation needs an explicit trusted CA bundle, supply `--ca-file /path/to/cacert.pem`. TLS verification stays enabled. Network failures stop the run rather than silently shrinking its denominator.

## Independent references: next step

1. Keep the audit prefix as a frozen ingestion test, including unsupported cases.
2. Create a separate licensed, supported pool for relationship evaluation; report all exclusions and any normalization performed.
3. Assign train/development/test by source paper or authoring origin before fitting a model. Do not split edits of the same diagram across partitions.
4. Reuse existing expert annotations or extract a separately stored source-program reference where the task permits. Strip answer-bearing metadata from recovery inputs and report geometry-to-reference mapping coverage. New manual labeling is an alternative for perceptual intent, not a mandatory blocker; see [existing reference data](../docs/existing-reference-data.md). Do not show a new annotator model predictions as suggested answers.
5. Record arrow endpoints, containment, grouping, alignment, and ordering separately. Mark ambiguous or unobservable author intent instead of forcing a label.
6. Record annotator identity/type, evidence, review status, source hashes, license, and changes to labels. Agent annotations must not be described as human-reviewed.
7. Freeze test annotations before selecting features, thresholds or models. Treat the present synthetic experiment as a pilot, not a final paper result.

The original `annotation.schema.json` describes the proposed relation-only version 1 records. The implemented [version 2 format](annotation-v2.schema.json) adds compound objects, source primitive locations and explicit coverage. An empty, unknown or agent-reviewed annotation is not independent human ground truth.

Use the [local compound annotation workflow](../docs/compound-annotation.md) after browser measurement. It starts with no predicted role or relationship selected and supports resumable source-bound JSON downloads. `check-annotation` checks structural/provenance consistency; it does not establish semantic truth or verify who performed the annotation. The checked-in authored example is explicitly a scripted agent-reviewed workflow test. External annotation pages contain original figure bytes and must remain private until reuse rights are checked.

After independent records are saved, use [annotation comparison](../docs/annotation-comparison.md) to inspect coverage, grouping and grounded positive-label overlap before adjudication. The demo uses constructed variations of one authored record, not independent reviewers. Agreement tooling does not fill the missing human-label dataset.

## External source-program feasibility

`source-oracle-feasibility-selection.json` pins two purposive development probes from the public draw.io diagram repository. `results/source-oracle-feasibility.json` records verified original-source hashes and declared vertex/binding counts; artwork remains private in `.cache/label-source-audit`. These are source-declared references, not agent-confirmed or newly human-reviewed annotation records. No SVG editing support, grounding accuracy or unseen evaluation follows from metadata extraction. One probe has zero edges and is retained.

The [blinded recovery checkpoint](../docs/source-reference-recovery.md) now implements metadata stripping, render preservation, separate numeric-input prediction and source-reference scoring. Its protocol is `source-recovery-protocol.json`; `results/source-recovery.json` retains1/2 scored development probes and the geometry-baseline tie. Original artwork and private grounding remain ignored. It creates no newly human-reviewed labels and expands no editing denominator.
