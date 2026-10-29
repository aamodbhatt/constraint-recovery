# Research gate after the local systems checkpoint

The repository now has a working geometric editor, source-bound review, failure witnesses, stronger routing, sequence controls and compound-annotation infrastructure. **It does not yet establish a novel recovery method or a paper-ready learned advantage.** Constraint-based layout, inverse diagram editing and selective prediction have substantial prior work; see the README references.

## Current evidence

- The synthetic endpoint ranker improves over nearest-boundary matching but ties the tangent-aware heuristic. Scores are uncalibrated.
- Reuse and fresh geometric recovery both complete all 30 feasible authored sequence steps. A topological strip and ELK plus the same repair engine also complete them. These motifs do not demonstrate that latent-constraint reuse is necessary.
- The external development prefix contains 19 available SVGs. Browser geometry and unlabelled annotation views cover all 19; complete-figure editing still covers zero. No independent human relationship annotations exist.
- Arithmetic witnesses certify specific contradictions of the accepted fitted geometry. They do not certify inferred intent, a minimum repair, arbitrary curved-path safety or pixel-perfect typography.

## Narrow research question

Can a system recover **reusable, uncertainty-aware structural relationships** from existing vector diagrams and preserve them across unseen edit sequences, with fewer explicit corrections than strong geometric recovery and direct source editing?

The potential contribution is the recovery-and-review behavior on existing authored diagrams. MILP placement, shortest-path routing, local browser measurement or an annotation interface alone is not the novelty claim. A useful paper requires evidence that the recovered representation helps on cases strong alternatives cannot already solve at the same correction budget.

## Data and evaluation before another model

1. Define eligibility and edit scope before inspecting model errors. Keep unsupported/excluded figures in the denominator and record why they were excluded. Start with node/arrow diagrams, compound objects and containers; do not silently reclassify plots or image grids as successful graph recovery.
2. Use the current 20-row prefix only for development. Group future splits by source paper/authoring origin, including different diagrams and revisions from the same paper. Freeze a fresh holdout before feature/threshold selection. Check individual source rights before publishing assets or derived annotations.
3. Obtain independent annotations through the blind compound-object view. Have two people independently label an overlapping subset and adjudicate disagreements; retain ambiguous/unobservable intent. An agent-reviewed record or a confirmed UI status is not automatically human ground truth. An authored-program oracle may form a separate provenance-labelled evaluation track.
4. Measure primitive-role classification and object grouping separately from text ownership, endpoints, containment and other latent relations. Report per-diagram errors and source/annotation coverage, not only endpoint averages. Cluster uncertainty estimates by diagram/paper.
5. Compare nearest-boundary, tangent-aware geometry, the existing ranker, source metadata where available, reviewed/oracle relationships and direct source editing. Keep layout fixed when comparing recovery. Keep recovered graphs fixed when comparing layout. Include a strong simple packing control and the ELK-repair hybrid.
6. Evaluate held-out edit sequences, protected labels/relationships, style preservation, requested dimensions, selective completion and correct rejection of impossible requests. A refusal must remain visible; an invalid output must not become the next state. Retain case-level artifacts and independent checks.

## Review experiment to preregister

Test correction budgets of 0, 1, 2 and 4 endpoint/object questions per diagram. Compare random selection, smallest geometric margin, uncalibrated model uncertainty, and a task-sensitive question score based on disagreement between plausible edited outputs. Record candidate-set coverage: if the correct object is missing, a constrained chooser cannot repair it.

An edit request is **not evidence that the intended graph makes that request feasible**. A genuine source cycle may make a requested uniform flow impossible. Do not discard graph hypotheses simply because they produce an inconvenient edit; ask for review or return an honest conflict. Any structural assumption used to prune hypotheses must be independently justified or explicitly supplied by the user.

Proceed only if a method improves the declared correction/coverage tradeoff on the untouched holdout over the tangent-aware and simple-layout controls. If it ties, report that result and revise the hypothesis rather than describing infrastructure work as learned novelty.

## Next implementation checkpoint

Use reviewed compound objects to implement a conservative source-preserving adapter: move selected primitive groups as rigid objects, protect unselected artwork, retain source hierarchy/style, and independently measure the serialized result. First demonstrate this on authored rich fixtures and a rights-checked external subset. Keep unsupported style, effects, shared-part ownership and inconsistent manifests as explicit failures. The annotation format is not yet an editing adapter.

Only then train a small contextual relation/role model locally. Cloud compute is justified by a measured training or accuracy bottleneck, a frozen split and a bounded saved-output experiment. No GPU resource has been started or credit spent. The present endpoint pilot trains in a fraction of a second on CPU.
