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

## Development results

Open the [comparison workspace](demo/native-pilot/index.html) to inspect all five cases and both checked moves. The [separate unlabelled review packet](demo/native-pilot/review/index.html) contains original sources and primitive-selection tools without role or relation suggestions. It creates no completed human labels; independent reviewers should save their own records before consulting the agent-labelled comparison.

The original editor accepted **0/5 first moves**; [all initial failures](../results/native-pilot-initial.json) are retained. After adding preserved editor metadata, explicit non-marker/separate-head geometry and whole-connector translation:

| Frozen figure | Accepted moves / planned | Outcome |
|---|---:|---|
| Basic RNN | 2/2 | Ten timestep parts move together; two state shafts update and one separate head translates |
| External memory | 0/2 | Unresolved read/write context remains protected; second move is skipped |
| Weighted read | 2/2 | Fourteen readout/equation parts move together; seven accepted connections reroute |
| Graph tasks | 0/2 | Mid-marker rerouting is unsupported; second move is skipped |
| Standard networks | 2/2 | 134 node parts and their connecting curve translate; lower row stays protected |

The total is **6 accepted of 10 planned moves**, eight attempted moves, three complete sequences and three checked out-of-canvas refusals on supported sequences. Refusal on an unsupported figure is not counted as an established infeasibility result. Two authoring origins and agent-supplied relationships are substantial limits.

For the first move of each figure, compare two direct source-edit controls using the same reviewed parts and translations: node-only movement is accepted on 0/5; a stronger translate-only rule that also carries connectors when both endpoints move identically is accepted on 1/5, tying the editor on the standard-network row. The latter comparison isolates endpoint repair on the two nonuniform moves. Refused controls are not all proven semantically wrong: unresolved annotations and unsupported marker behavior also prevent assessment. These are small deterministic controls, not comparisons against expert hand editing or contemporary AI diagram editors.

The weighted-read output exposed a routing limitation: independent connections shared segments. The [retained visibility-only checkpoint](../results/native-pilot-visibility.json) records the earlier behavior. The editor now prefers ordered channel tracks where supported. A [paired comparison](../results/parallel-routing.json) keeps the same source, relationships and two moves fixed: both routing modes complete both moves, while the new routes have zero contacting pairs outside the accepted endpoint envelopes. The comparison workspace lets you switch between them. [Mathematical derivation and checking boundary](channel-routing.md).

This local shaft check does not certify every edge, stroke/head clearance, or topology hidden inside logical-object envelopes. Visibility fallback may still produce contacts, which are reported as warnings. Source text uses local font fallback; computed-style and pose checks are not a pixel-identity certificate.

The [saved results](../results/native-pilot.json) include every case, planned/skipped moves, annotation/source/request hashes and implementation-file hashes. Fresh damaged candidates must be rejected when a separate head moves incorrectly, a carried curve changes geometry or editor metadata is altered.

```sh
PYTHON=.venv/bin/python node benchmarks/measure_native_pilot.cjs
PYTHON=.venv/bin/python node benchmarks/native_pilot_check.cjs
node benchmarks/native_presentation_check.cjs
PYTHON=.venv/bin/python node benchmarks/compare_parallel_routing.cjs
python benchmarks/build_native_pilot_demo.py
```

The frozen source and annotation files are checked in with attribution. Full browser style measurements and intermediate controls remain under ignored `.cache/` and `artifacts/`. The external development fixtures also run as CI regressions; they are consequently not an untouched holdout.

## Separate benchmark track

The existing SciDiagramRevision audit remains a different development track: 19 available reconstructed SVGs from 20 rows. The [benchmark paper, section 3](https://arxiv.org/html/2607.15272v1), describes an LLM-assisted vectorization pipeline; those SVGs should not be described as the original author-written vector sources. Their mixed source-paper rights remain unresolved for redistribution. The new pilot does not replace or improve that original audit's denominator.
