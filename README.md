# Constraint recovery

Recover an inspectable graph from a simple scientific SVG, edit its layout through explicit constraints, and check the exported result.

**Status: local geometric baseline.** This checkpoint contains no trained model and makes no claim of research novelty. It establishes an executable reference pipeline for later learned constraint recovery.

![Local before-and-after example with verification evidence](docs/demo/preview.png)

The checked-in [example report](docs/demo/portrait.html) and SVGs can be downloaded and opened locally. On the first local 30-case synthetic run, the solver pipeline passed all 30 checks, versus 20 for the simple fixed-placement baseline. See [full results](results/local-baseline.json) for case-level errors and scope.

## Try it

Python 3.10+; CPU only. No API keys, model downloads, or cloud GPU.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'

constraint-recovery recover examples/pipeline.svg --output artifacts/recovered.json
constraint-recovery edit examples/pipeline.svg \
  --labels examples/labels.json \
  --font-size 20 --width 300 --height 650 --flow vertical \
  --output artifacts/pipeline-portrait.svg
```

Open `artifacts/pipeline-portrait.html` in a local browser. The command also writes an editable SVG, the resulting constraint graph, and a JSON verification report. To run from an existing environment without installation, prefix commands with `PYTHONPATH=src python3 -m constraint_recovery` instead of `constraint-recovery`.

## Current pipeline

```text
Supported SVG → recovered nodes and directed edges → optional human review
              → text fitting → MILP placement → connector routing
              → SVG serialization → fresh SVG import → independent checks
```

- Import rectangular nodes, editable text, and directed line/polyline/absolute M/L connectors.
- Infer text ownership by containment and connector ownership by boundary proximity. Ambiguous endpoints are rejected.
- Inspect the JSON graph; `edit --constraints reviewed.json` accepts corrections to source/target relationships while retaining source text and geometry. It requires matching primitive IDs.
- Apply replacement labels, font-size changes, and new canvas dimensions. `--flow vertical` or `horizontal` explicitly requests a directed flow layout; `free` preserves only graph connectivity and geometric feasibility.
- Fit labels with conservative Pillow font metrics. Place nodes with SciPy/HiGHS mixed-integer optimization: minimize L1 displacement subject to canvas bounds, fixed fitted sizes, pairwise nonoverlap and optional flow constraints.
- Route connectors using finite candidate paths, rejecting paths through nodes or outside the canvas.
- Re-import the exported SVG and check node/edge identities, directed connectivity, labels, typography bounds, node overlaps, arrow attachments and node-crossing connectors.

The checker checks compliance with the accepted graph. **It cannot prove that the recovered graph expresses the author's intended meaning.**

## Scope and limits

This is a normalized diagram editor, not a lossless arbitrary-SVG editor. Export retains node IDs, labels, basic fills/strokes and accepted connectivity, while normalizing typography and connectors. Rich styles, transforms, nested containers, plots, raster images, text outlines, undirected lines and curved connectors are unsupported and may require normalization or are rejected. Inherited styling is not supported. Start with the supplied example or similarly simple diagrams.

Text sizing is a conservative local estimate, not browser pixel-level certification. Connector routing is a finite search and may fail even when a more sophisticated route exists. Large diagrams, dense routing and solver time limits can prevent a usable result. The baseline caps inputs at 40 nodes.

When an edit is infeasible or fails verification, the CLI exits with code 2 and does not export a new diagram. It does not silently shrink text or remove nodes. A pre-existing file at the output path is not removed on failure: check the exit status rather than treating its presence as success. Output must differ from the input path.

## Tests and benchmark

```sh
python -m pytest -q
PYTHONPATH=src python benchmarks/run.py --output artifacts/benchmark.json
```

The seeded 30-case engineering benchmark covers longer labels, larger fonts and portrait conversion on generated chains. It compares the solver pipeline with a simple baseline that scales positions and fits text while keeping node placements fixed. Full case records and failures are retained. The comparison is **not** against ELK, a learned model, an LLM, or external scientific diagrams, and is not evidence of a research contribution.

## Research direction

The research target is recovering latent relationships from supported existing SVGs, distinguishing intended constraints from incidental geometry, representing uncertainty, and improving preservation over repeated edits.

Relevant prior work includes [Constraint SVG](https://constraints.cs.washington.edu/web/csvg-uwtr-2000-08-04.pdf), [Mockdown](https://www.cs.cornell.edu/~jsarracino/files/mockdown-final.pdf), [Penrose](https://penrose.cs.cmu.edu/), [constraint-graph layout generation](https://arxiv.org/abs/2011.13417), [SciDiagramEdit](https://arxiv.org/abs/2607.15272), and [InfoEdit](https://arxiv.org/abs/2609.33286). Constraint-based SVG layout and AI diagram editing are established areas; this repository does not claim to invent them.

See [ROADMAP.md](ROADMAP.md) for milestones and the cloud-training gate.

## License

MIT. See [LICENSE](LICENSE).
