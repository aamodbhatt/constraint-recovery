# Compound-object and relationship annotation

The external figures contain backgrounds, frames, labels, icons and shapes that cannot all be treated as independent rectangular graph nodes. The new `annotate` command groups measured SVG primitives into explicitly labeled objects and records relationships without model suggestions.

```sh
# Optional Node/Playwright development tools:
npm ci --ignore-scripts
npx playwright install chromium
node benchmarks/measure_svg.cjs figure.svg artifacts/geometry.json

constraint-recovery annotate figure.svg --measurements artifacts/geometry.json \
  --diagram-id my-diagram --source-url SOURCE_URL --license SOURCE_LICENSE \
  --output artifacts/annotation.html
```

Open the local HTML. Click or lasso parts, or use the primitive checklist; Shift-click adds to the selection. Assign an explicit role—node, container, connector, text, background, decoration or unknown—and an object status. A node can include several shapes and text elements. Roles and relation kinds start blank; statuses start unknown. The viewer supports content/canvas fitting, pan, zoom and primitive filtering.

Then record directed edges, containment, grouping, alignment or order between objects. A directed edge can identify a separate connector object. Self-edges are allowed in the annotation format even though the current editor cannot edit them: evaluation labels must not be forced to match implementation limits. Unknown and ambiguous relationships remain explicit. Primitive parts are disjoint across objects; containment is represented separately instead of assigning child primitives to both a frame and a node.

Download a JSON record to save; upload it through “Resume from JSON” to continue. A source digest mismatch, duplicate part assignment, broken object reference or inconsistent coverage is rejected. Removing an object referenced by a relation requires explicitly removing that relation first.

[Open the authored demo](demo/primitive-annotation.html). The screenshot below shows a **scripted fixture exercise**, not independent human annotations:

![Compound annotation of an authored SVG fixture](demo/compound-annotation-preview.png)

## Provenance and validation

The [version 2 schema](../data/annotation-v2.schema.json) adds compound objects and explicit primitive coverage to the original proposed relation-only format. It retains source hashes, source URL, license, split, annotator type/identity, evidence and per-object/relation status. Unassigned primitives remain listed, so partial annotation cannot silently become a complete-diagram label set.

```sh
constraint-recovery check-annotation downloaded.annotation.json \
  --source figure.svg --measurements artifacts/geometry.json
```

The checker validates structure, source binding, primitive/object references and coverage. It **does not verify semantic truth or the actual identity of an annotator**. Review metadata is self-reported. `human-reviewed` requires a declared human identity and evidence; an agent record cannot use that status. The checked-in [scripted example](../examples/styled-pipeline.annotation.agent.json) is marked `agent-reviewed`, with evidence stating that it is a workflow test. There is still no independently human-annotated external test set.

## Display and measurement scope

The original SVG is encoded as an image resource; it is not injected as active source markup into the tool’s DOM. Source scripts and external references are disabled in SVG image processing; see [SVG 2 processing modes](https://www.w3.org/TR/SVG2/conform.html#secure-animated-mode). The browser test includes a source-script message probe and verifies that no secondary network request is made. A pixel test also checks that the measured coordinate projection lands on the original blue node fill, independently of the overlay drawing.

Overlays project browser-measured envelopes into the source viewport. They exclude stroke/marker outlines and filter/clipping effects, and font fallback can vary across machines. Animated/conditional stylesheets and root CSS transforms are rejected for the annotation preview rather than displaying a knowingly mismatched overlay. Blocked assets are reported; verify missing artwork against the original before confirming semantics.

The generated HTML **contains the original SVG**, and full measurements contain source geometry. Keep external figures under ignored `artifacts/` or `.cache/` unless their individual reuse terms allow redistribution. The public demo uses an SVG authored for this MIT-licensed project. Measurement and annotation are not new editing coverage: complete-figure external edit support remains 0/19. The immediate next step is independent annotation and a source-preserving compound-node adapter, followed by held-out relation and edit-sequence evaluation.

`python benchmarks/build_external_annotations.py --rows 20` builds the existing development prefix from private cached sources and measurements. The [build audit](../results/annotation-view-audit.json) creates 19 unlabelled views, retains the missing twentieth source and creates **zero annotations**. Views and source copies remain in ignored `.cache/annotation-views/`. A successful build is not a rendering-fidelity certificate. See the [research gate](research-plan.md) before treating these development figures as evaluation data or training another model.
