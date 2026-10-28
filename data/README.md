# Evaluation data protocol

## What exists

- `results/external-compatibility.json`: first 20 test rows from SciDiagramRevision, selected before measuring support. No source images or SVGs are redistributed.
- `benchmarks/learn_attachments.py`: programmatically labeled endpoint scenes. Train/validation/test use seeds 101/202/303; staggered layouts use seed 404 and are excluded from training and threshold selection.
- No independently annotated real-diagram relationship test set exists yet. A compatibility audit is not that test set.

## External audit findings

The audited prefix contains 19 source SVGs and one missing source. The strict M0 parser accepts none. The report retains every row, source hash where available, and first rejection reason. It does not measure edit quality or claim representativeness of the whole dataset.

The upstream dataset declares `mixed-arxiv-source` licensing. Inspect each paper's reuse terms before redistributing an input or derived dataset. The audit keeps identifiers and compatibility results only.

Reproduce with:

```sh
PYTHONPATH=src python benchmarks/audit_external.py --rows 20
```

If your Python installation needs an explicit trusted CA bundle, supply `--ca-file /path/to/cacert.pem`. TLS verification stays enabled. Network failures stop the run rather than silently shrinking its denominator.

## Real relationship annotations: next step

1. Keep the audit prefix as a frozen ingestion test, including unsupported cases.
2. Create a separate licensed, supported pool for relationship evaluation; report all exclusions and any normalization performed.
3. Assign train/development/test by source paper or authoring origin before fitting a model. Do not split edits of the same diagram across partitions.
4. Annotate from the original drawing and, when available, its authored source program. Do not show the annotator model predictions as suggested answers.
5. Record arrow endpoints, containment, grouping, alignment, and ordering separately. Mark ambiguous or unobservable author intent instead of forcing a label.
6. Record annotator identity/type, evidence, review status, source hashes, license, and changes to labels. Agent annotations must not be described as human-reviewed.
7. Freeze test annotations before selecting features, thresholds or models. Treat the present synthetic experiment as a pilot, not a final paper result.

The `annotation.schema.json` file describes proposed records. An empty or unknown annotation is not scored as a confirmed relationship.
