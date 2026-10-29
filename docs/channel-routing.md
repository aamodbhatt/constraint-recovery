# Separating parallel shafts in an accepted SVG graph

Independent shortest paths can preserve every accepted attachment while sharing a visible segment. The native weighted-read figure exposes this: seven curves become seven orthogonal paths, but several paths initially merge visually. The editor now prefers a bounded ordered-channel candidate for suitable parallel groups and separately measures contacts in the serialized output.

This uses classical routing ideas. Track ordering and constraint graphs have a long history in circuit layout; see the [PARC physical-design report, section 2.1](https://xeroxparcarchive.computerhistory.org/_cd6_/autolayout/documentation/.EDACFinal.tioga%217.html) and [Tse and Kinsner's channel-router paper](https://doi.org/10.1016/0167-9260(88)90005-3). Neither channel routing nor the partial-order algorithm is claimed as a new research contribution here.

## Candidate geometry

Consider one accepted source/target object pair and 2–32 rerouted connectors. All escape ports must use one common opposing axis; source columns and target columns must each be distinct. Let `u` increase from source toward target, and let `v` run across the ports. Connector `i` has source column `s_i`, target column `t_i`, and a trunk track `u_i`:

```text
(s_i, source_u) → (s_i, u_i) → (t_i, u_i) → (t_i, target_u)
```

The terminal positions retain their original offsets in the accepted objects. Moving a logical object does not snap its connections to a box center.

Let `I_i = [min(s_i,t_i), max(s_i,t_i)]`. To avoid a trunk contacting another connector's branches, impose:

```text
s_j ∈ I_i  ⇒  u_i ≥ u_j + δ       j ≠ i
t_j ∈ I_i  ⇒  u_j ≥ u_i + δ       j ≠ i
```

These inequalities define a directed order graph. A topological traversal computes longest-path ranks. With spacing `δ`, set `u_i = offset + δ rank(i)` and center the used tracks in the available band between the endpoint escape regions. Current candidate spacing is eight viewBox units, with additional eight-unit margins at each band end. This is track spacing, not a minimum Euclidean clearance between every pair of shafts: terminal columns can be closer.

The implementation declines this candidate family on a cycle, coincident terminal columns, insufficient track depth or an obstacle/canvas violation. It then tries the visibility router. A failed candidate is **not** a proof that every possible routing is infeasible; extra bends, different channels or a different junction model may work.

## Why the order constraints help

Within this three-segment family, source branches extend from the source boundary to their tracks, while target branches extend from their tracks to the target boundary. A source branch whose column lies in trunk `i`'s span must end before that trunk; a target branch in the same span must start after it. The two inequalities enforce those conditions. Intersecting trunk spans receive an order constraint, so they cannot occupy the same track in an accepted acyclic assignment. Distinct terminal columns prevent coincident source/source or target/target branches. Opposite-side coincident columns also receive the required order constraint.

Those arguments apply to shaft centerlines in the common channel, under the stated port and family assumptions. Every candidate still undergoes obstacle checks and fresh source/style/pose verification after serialization.

## Independent output evidence

`edge_check.py` calls no router or solver. It receives the actual serialized M/L/line/polyline segments transformed through fresh browser matrices. It computes transverse point contacts and positive-length collinear sharing between each rerouted parallel pair. Contacts inside the union of the two accepted endpoint envelopes are excluded; the bounds are conservative logical-object envelopes.

`parallel_shaft_checks` records connector IDs, contacting-pair counts and pairwise shared length. `warnings` exposes nonzero contacts even when attachment and node checks pass. A channel preference does not itself certify separation: the measured result does. The paired diagnostic deliberately checks a visibility output while declaring a channel preference and requires the same nonzero observations, guarding against trusting the planner label.

The contact check uses floating-point tolerances of approximately `1e-6` in its predicates and a two-million segment-pair budget across an edit. Exceeding that budget declines the edit instead of returning a partial clean result. It excludes stroke thickness, separately drawn heads, unchanged connectors, self-contacts of one shaft, and contacts hidden inside the accepted endpoint envelopes. It does not prove complete-figure topology, author intent or pixel identity. Spacing and obstacle-search limits can also make this preference decline a visually feasible layout.

## Paired native diagnostic

The [saved comparison](../results/parallel-routing.json) holds the source, agent-reviewed relationships and two frozen moves fixed, varying only `--routing visibility` versus `--routing channel`. Both modes complete both moves. Ordered candidates remove the observed external shaft contacts in this seven-link case; this is a specific development result on one figure, not a representative benchmark or learned advantage. The broader five-figure pilot retains both of its declined cases.

| Move | Visibility: contacting pairs / shared-segment pairs | Ordered channel: contacting pairs / shared-segment pairs |
|---|---:|---:|
| 1 | 8 / 6 | 0 / 0 |
| 2 | 9 / 5 | 0 / 0 |

```sh
PYTHON=.venv/bin/python node benchmarks/compare_parallel_routing.cjs
```

Original illustration: Chris Olah and Shan Carter, [*Attention and Augmented Recurrent Neural Networks*](https://distill.pub/2016/augmented-rnns/), Distill, 2016, [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/). The compared outputs are modifications by this project; no author endorsement is implied.
