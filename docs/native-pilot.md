# Author-published SVG development pilot

The fixed selection in [the manifest](../data/native-pilot-selection.json) contains five native SVGs from two Distill research articles. The selection was recorded on 2026-10-30 before edit attempts. It covers recurrent computation, external memory, attention-based reading, graph tasks and neural-network architectures. No selected figure will be replaced because it fails an edit.

This is a small purposive **development** pilot with two authoring-origin clusters. It is not representative of scientific diagrams, an untouched holdout, or independent relationship ground truth. All annotations created by this agent remain explicitly agent-reviewed. They can support conditional editing diagnostics, not claims about automatic recovery accuracy or human review.

## Sources and rights

- Chris Olah and Shan Carter, *Attention and Augmented Recurrent Neural Networks*, Distill (2016), [article and reuse terms](https://distill.pub/2016/augmented-rnns/), [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/). Selected assets: `rnn_basic_rnn.svg`, `rnn_memory.svg`, `rnn_read.svg`.
- Ameya Daigavane, Balaraman Ravindran and Gaurav Aggarwal, *Understanding Convolutions on Graphs*, Distill (2021), [article and reuse terms](https://distill.pub/2021/understanding-gnns/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Selected assets: `graph-tasks.svg`, `standard-neural-networks.svg`.

These are original article illustrations without an identified third-party caption exception. The article's diagram license applies; repository code licenses do not replace it. Original inputs remain byte-identical to pinned Git blobs, with SHA-256 recorded in the manifest. Any edited output is a derivative made by this project and must retain source attribution and indicate the change. No author endorsement is implied.

## Predeclared experiment

For each figure, retain the original SVG without normalization or removal of artwork. Inspect its browser-measured primitives, label compound objects and explicit connections, and retain unknown/ambiguous content. Record unsupported source features and annotation gaps separately from routing or verification failures.

Freeze one meaningful rigid-translation request before running it; then attempt a second edit from the accepted derived state. Finally request a translation that leaves the canvas. A rejected candidate must never become the next source. Compare with direct movement of the same reviewed parts without connector repair. Assess both outputs against the same accepted relationships and fresh browser measurements; direct movement may legitimately pass on disconnected objects or when a whole connected component moves together.

Report all five figures, every request, source and annotation hashes, review provenance, movement/routing scope, checker outcomes and refusal reasons. An unavailable annotation or an unsupported arrow construction is not a successful edit. Conditional success under reviewed assumptions does not establish that those assumptions match the authors' intent.

## Separate benchmark track

The existing SciDiagramRevision audit remains a different development track: 19 available reconstructed SVGs from 20 rows. The [benchmark paper, section 3](https://arxiv.org/html/2607.15272v1), describes an LLM-assisted vectorization pipeline; those SVGs should not be described as the original author-written vector sources. Their mixed source-paper rights remain unresolved for redistribution. The new pilot does not replace or improve that original audit's denominator.
