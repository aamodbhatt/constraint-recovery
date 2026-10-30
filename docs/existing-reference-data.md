# Reference labels without recruiting annotators

New manual annotation is one evaluation option, not a prerequisite for continuing this project. Existing expert annotations and original authoring programs can supply references independently of our recovery predictions. Rechecking our own labels with the same assistant cannot establish independent human ground truth.

## Best immediate fit: source-declared graph references

The [draw.io file specification](https://github.com/jgraph/drawio/wiki/File-Format) documents an embedded `mxfile` in exported SVGs. Its graph cells retain declared vertex IDs and source/target bindings. Read this original graph as the reference; score recovery from a separately prepared visual input. [Penrose](https://penrose.cs.cmu.edu/docs/ref/using) exports its source programs in SVG metadata too, and its [Substance language](https://penrose.cs.cmu.edu/docs/ref/substance/overview) explicitly declares objects and relations. These are source-program references, not new human reannotations.

A [two-source feasibility probe](../results/source-oracle-feasibility.json) pins original files from [jgraph/drawio-diagrams](https://github.com/jgraph/drawio-diagrams) to revision `cc78dc2e7df8cf3ad437e6f876fbc33d2d0b7e01` and verifies their Git blobs:

| Original example | Declared vertices | Declared edges | Both ends bind to vertices |
|---|---:|---:|---:|
| `flowchart.drawio.svg` | 6 | 5 | 5 |
| `connect-shapes.svg` | 18 | 0 | 0 |

Both examples were inspected during discovery. They are development probes, not a random sample or held-out benchmark. The zero-edge case stays visible: a useful-looking diagram need not contain useful reference connections. Counts include declared vertex cells, not an independently inferred semantic object inventory.

`benchmarks/audit_source_oracles.py` reads metadata without rendering it or fetching embedded resources. It handles plain, percent-encoded and raw-deflate authoring pages; rejects duplicate IDs, entities, malformed/truncated streams and resource-budget overruns; and retains free/unbound endpoints. Source/target ordering alone is not semantic direction. Arrow styles and renderer defaults must be resolved before making directed-edge labels.

```sh
# Acquire pinned sources once, with a trusted CA bundle if this host needs one:
python benchmarks/audit_source_oracles.py --ca-file /path/to/cacert.pem
# Repeat entirely offline:
python benchmarks/audit_source_oracles.py --offline
```

Original SVGs remain in ignored `.cache/label-source-audit`; no artwork is redistributed. The repository declares Apache-2.0. Check per-file notices before publishing a future dataset.

### Prevent reference leakage

1. Freeze source repositories, eligibility, rendering/normalization and splits before fitting or selecting recovery methods. Keep figures/revisions from one authoring origin together.
2. Extract references into a separate scoring artifact. Remove embedded graph payloads, hidden source code and semantic identifiers from the recovery input. Distinguish a geometry-only arm from a source-metadata baseline. Preserve visual labels and all visible artwork.
3. Ground reference cells to visible parts using an independently specified exporter/format mapping. Report coverage and ambiguous/unmapped cells; do not generate geometry from the answer graph and present its easy recovery as real-figure recognition.
4. Freeze predictions before the scorer reads references. Retain unsupported examples and direction/containment uncertainty. Source graph absence does not prove that a visible connection is semantically absent.
5. Report explicit connections separately from alignment, latent intent and perceived composition, which an authoring file may not encode.

The [blinded reference pipeline](source-reference-recovery.md) now strips the graph, preserves browser pixels and scores geometry-only endpoint predictions against a restricted exporter mapping. One of these two development probes is scored: both classical baselines recover10/10 bindings on the flowchart; the resource-blocked tutorial remains unscored. This is not a holdout or learned improvement. The flowchart's HTML labels remain outside the conservative editing adapter, so no new editing coverage follows. An expanded source-program pool and authoring-origin holdout remain next.

## Existing expert annotations: AI2D-RST

[AI2D-RST](https://github.com/thiippal/AI2D-RST) provides expert grouping and connectivity graphs for 1,000 science diagrams. The [dataset paper](https://doi.org/10.1007/s10579-020-09517-1) describes its annotation process. The repository declares CC BY 4.0 for the added corpus annotations; underlying AI2D image rights must be checked separately. The current official catalogue lists version1.1, and the repository's1.1 release fixes annotation errors.

This is relevant to perceptual grouping and relationship understanding, but its figures are raster images. It is not a native-SVG editing benchmark. An evaluation using its supplied object regions must be labeled conditional on those regions, not end-to-end detection. Vectorizing an image does not transfer human part labels to SVG primitives automatically.

The documentation and annotation schema were inspected. The official URN download returned HTTP403 in this environment; the full corpus has **not** been acquired or integrated. GitHub's release contains code archives, not a demonstrated full-corpus data download. Do not claim otherwise or use an unverified mirror as equivalent provenance.

## Other candidates and secondary review

- [FlowLearn](https://github.com/Jo-Pan/FlowLearn) includes scientific flowcharts and a separate simulated Mermaid/SVG subset. Its program-derived references could stress a parser across another renderer; simulated figures cannot replace evidence on original real diagrams. Inspect each subset's actual labels and rights before adoption.
- [SketchGraphs](https://github.com/PrincetonLIPS/SketchGraphs) contains real CAD primitives with designer-imposed constraints. It is a promising adjacent constraint-recovery task, but geometric CAD relationships and its data/licensing requirements differ from scientific-diagram editing. It would be a separate research track, not a plug-in label source for the five native figures.
- A different vision-language model can supply a blinded second prediction or propose uncertain labels. Record the model/version, inputs and raw outputs; score agreement as model agreement. This is useful supplementary evidence, not independent human truth or a substitute for a source-program reference.

The practical choice is to continue with source-program references for SVG recovery and reuse existing expert corpora where their task matches. Human review remains useful for subtle author intent and edit-quality studies, but it need not block the next engineering and quantitative-recovery checkpoint.
