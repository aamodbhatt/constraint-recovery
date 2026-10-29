# Repeated-edit pilot

The first sequence experiment uses five authored programs: chains of four/six nodes, branches of four/six nodes, and a four-node diamond. Every method receives the same checked initial SVG and six requests: longer text, a larger font, portrait conversion, explicit branch insertion, landscape conversion, and a shorter label/smaller font. A final 80×60 canvas request is deliberately impossible.

```sh
python benchmarks/run_sequences.py --elk --output artifacts/edit-sequences.json
```

The [recorded run](../results/edit-sequences.json) preserves every step, failure and skipped request. It uses a fail-stop protocol: an unsuccessful feasible request ends that method’s sequence; no invalid intermediate SVG is propagated. The impossible final request is counted as a correct rejection only when the method reaches and rejects it. [The interactive walkthrough](demo/sequence/index.html) shows one complete authored sequence.

| Method | Feasible steps passed / planned | Complete feasible sequences | Final impossible requests reached and rejected |
|---|---:|---:|---:|
| Reuse accepted graph + MILP | 30 / 30 | 5 / 5 | 5 / 5 |
| Fresh geometric recovery + MILP | 30 / 30 | 5 / 5 | 5 / 5 |
| Topological strip | 30 / 30 | 5 / 5 | 5 / 5 |
| ELK + same MILP repair | 30 / 30 | 5 / 5 | 5 / 5 |
| ELK layered, declared direction | 12 / 30 | 0 / 5 | 0 / 5 |
| Direct attributes, fixed geometry | 0 / 30 | 0 / 5 | 0 / 5 |

The direct-attribute baseline fails its first long-label request. The ELK-only configuration fails on narrow branching layouts: its natural width exceeds the fixed canvas. Its final impossible requests are **unattempted**, not accepted erroneously. ELK receives the same recovered graph and text-fitting rules, but its layered layout objective differs from the canvas-constrained displacement objective. These results do not establish superiority over all ELK configurations or modern AI editors.

## What this establishes

The prototype survives these edit sequences, preserves the known program graph and protected labels, and rejects the deliberately impossible requests with independently checked node-size witnesses. New sidecars bind to each output’s exact source digest. A stale digest is rejected instead of silently reusing a graph on a different figure.

## What it does not establish

**Fresh recovery ties reuse, and a simple topological strip also passes everything.** These motifs are too easy to demonstrate that latent-constraint reuse or MILP is necessary for feasibility. The strip shares text metrics and the visibility router; the ELK-repair hybrid shares the MILP/routing engine. Neither is an independent learned model.

The reuse and fresh methods accumulate 11,621.2 units of L1 node displacement across accepted edits, compared with 42,548.4 for the strip and 31,678.4 for ELK repair in this local run. This reflects their explicit objectives; displacement is not a human judgment of layout quality, and ELK-only has fewer accepted steps so its displacement total is not directly comparable. Different optimal placements and platform font metrics may change these observations.

These are synthetic engineering diagnostics. They do not measure real-diagram recovery accuracy, calibration, source-style preservation or a learned advantage. Next evaluation needs independently established constraints, compound nodes/containers, incidental alignments, ambiguous ownership and edit requests whose consequences distinguish plausible recovered graphs. The external 19-source development audit still has zero fully editable figures.
