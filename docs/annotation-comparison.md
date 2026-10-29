# Comparing independent annotations without choosing a gold reviewer

`compare-annotations` compares two source-bound version 2 records. It reports primitive coverage, role agreement, object grouping, full-part correspondences and overlap of positive relationship labels. It never treats an annotator's object IDs as semantic truth or calls an unknown relationship false.

The [interactive demonstration](demo/annotation-comparison.html) uses scripted perturbations of one authored MIT fixture. It is not a study with two reviewers. Actual independent human labels are still absent from this repository.

## Workflow

Have reviewers use separate [unlabelled source views](demo/native-pilot/review/index.html) and save their own records before inspecting existing agent labels. Retain unknown/ambiguous parts and relations. For an overlapping subset, compare the two independent records before adjudicating differences.

```sh
node benchmarks/measure_svg.cjs figure.svg artifacts/geometry.json --snapshot

constraint-recovery compare-annotations reviewer-a.json reviewer-b.json \
  --source figure.svg --measurements artifacts/geometry.json \
  --output artifacts/comparison.json --html
```

Open `artifacts/comparison.html` to select an object correspondence and inspect its part envelopes. Both panes show the same original drawing; “Focus selected parts” applies the same crop to both, avoiding a misleading scale difference. Unmatched objects remain available. The page changes no annotation and confers no review status. Adjudicated labels must be saved as a separate record with their own provenance.

JSON-only comparison can omit source/measurements. The output then says which checks were absent. With `--source`, both annotation hashes must match the exact SVG. With `--measurements`, both primitive inventories must match the supplied source-bound measurement record. This validates supplied evidence, rather than independently rerunning the browser. Image overlays require both source and measurements and use the established inert-image/projection guards.

## Coverage before scores

Let `U` be the declared primitive inventory. The two records must describe the same `U`; differing inventories cause rejection instead of silently shrinking the comparison domain. Let `C_L` and `C_R` contain primitives whose object has a confirmed non-unknown role on each side. Role/grouping comparisons use only:

```text
J = C_L ∩ C_R
joint coverage = |J| / |U|
```

Report left-only, right-only and neither-confirmed counts as well. A record's confirmed status remains a self-reported label, not a correctness guarantee. A high conditional score at low coverage does not establish agreement on the rest of the figure.

## Grouping and object correspondence

Within `J`, object memberships define two partitions. Let `n_ij` be the contingency-table counts, `a_i` and `b_j` their row/column totals, and `C(n,2)=n(n−1)/2`. Define:

```text
A = Σ_ij C(n_ij,2)
L = Σ_i C(a_i,2)
R = Σ_j C(b_j,2)
N = C(|J|,2)

ARI = [A − LR/N] / [(L+R)/2 − LR/N]
VI  = Σ_ij (n_ij/|J|) log₂[a_i b_j / n_ij²]
```

The adjusted Rand index follows [Hubert and Arabie](https://doi.org/10.1007/BF01908075). Variation of information follows [Meilă's partition-comparison work](https://stat.uw.edu/research/tech-reports/comparing-clusterings). These are classical metrics, not novel methods in this project. Fraction arithmetic keeps the ARI chance correction exact before converting its result to JSON. VI is reported in bits. Fewer than two joint primitives gives an unscorable grouping result (`null`); identical degenerate partitions of at least two primitives receive ARI 1.

For visual correspondence, solve maximum-total-IoU linear assignment on the **full** confirmed part sets, without removing parts that the other side left uncertain. Role is ignored during assignment so a same-parts/different-role disagreement remains visible. Nonzero matches, unmatched objects and local IoU ties are exposed. The overlap sum divided by the larger object count retains unmatched objects in the denominator. An IoU match is a diagnostic, not an adjudicated semantic identity.

## Relationships and missing labels

Before comparing a positive relation label, every endpoint object must have an exact full-part **and role** correspondence. This is stricter than the soft matching display. Alignment/group endpoints are canonicalized without order; directed edges, containment and before-relations retain direction.

Report overlap of the declared comparable positive-label sets, along with one-sided labels, duplicate declarations, unresolved relations and unscorable confirmed declarations. Unlisted relations are unspecified: primitive coverage does not establish an exhaustive relationship inventory. The resulting positive-label Jaccard is not precision, recall or accuracy.

Connector binding is compared only for jointly declared edge labels with exact grounded connector objects on both sides. Missing or differently grouped binding evidence remains unscorable. Optional explicit shaft/head geometry is compared separately; exact equality of those fields does not verify that a selected tip represents the authors' intent.

No labels in a denominator means `null`, rather than perfect agreement. Comparisons are bounded to 5,000 primitives and 500 confirmed objects to constrain assignment cost. Across a future corpus, report per-diagram coverage and group uncertainty estimates by source paper/authoring origin; do not treat thousands of primitives from two articles as thousands of independent diagrams.

## Scripted diagnostic

The [saved fixtures](../results/annotation-comparison-fixtures.json) derive from one program-authored annotation:

| Constructed variation | Joint coverage | Grouping ARI | Joint-domain role agreement |
|---|---:|---:|---:|
| Object IDs renamed | 10/10 | 1.000 | 100% |
| Card and labels split | 10/10 | 0.848 | 80% |
| Decoder left unknown | 7/10 | 1.000 | 100% |

The last row demonstrates why a perfect conditional score must not hide abstention. The split leaves the endpoint relation unscorable until object grouping is resolved. None of these numbers estimates real inter-annotator agreement, recovery accuracy or human intent.

Rebuild the demonstration with:

```sh
node benchmarks/measure_svg.cjs examples/compound.svg artifacts/comparison-geometry.json --snapshot
python benchmarks/build_annotation_comparison.py
```
