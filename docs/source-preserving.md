# Source-preserving SVG checkpoint

Install the optional importer with `pip install -e '.[svg,test]'`, then run:

```sh
constraint-recovery edit examples/styled-pipeline.svg --source-preserving \
  --width 330 --height 650 --flow vertical \
  --output artifacts/styled-portrait.svg
```

The [authored example](../examples/styled-pipeline.svg) exercises a nonzero viewBox origin, nested groups, translation/uniform scaling, stylesheet inheritance and specificity, a gradient, and a cubic connector. The [portable demo](demo/styled-portrait.html) keeps the original gradient, stylesheet, metadata, group hierarchy, source element tags and existing node/edge IDs. Text line tspans are regenerated when labels are fitted; connector geometry is rerouted. An unchanged graph round-trips byte-for-byte. An edited document is serialized again, so whitespace, namespace prefixes and XML comments are not promised to survive.

The importer resolves author presentation attributes, static selectors and inline CSS, including `!important`. CSS geometry, dynamic/functional selectors, at-rules, unsupported fonts, independently styled tspans, rotations, reflections, skew, nonuniform scaling, nested viewports, clipping, filters, raster content, decorative artwork and unmarked arrows are rejected. This is a controlled subset, not a browser-equivalent SVG parser. Source lines that need a multi-segment route are rejected rather than changing their tag and potentially invalidating CSS. Branch additions currently require the default normalized exporter.

Geometry uses normalized viewBox coordinates. For a local point `p`, the recovered point is `p' = T_origin T_parent ... T_local p`. Each editable transform has a positive scalar linear part `s I`; rectangle extents and font sizes scale by `s`. Export applies the inverse element transform to solved positions. The original transform hierarchy remains in the document. Canvas changes intentionally update the viewBox and viewport dimensions.

For quadratic/cubic connectors, subdivision continues until every control point is within 0.2 viewBox units of the chord segment. The convex-hull property bounds curve-to-chord distance, with hard recursion and point budgets. Arc segments, disconnected subpaths and closed paths are rejected. This approximation supports recovery; it is **not a formal curved-path collision certificate**. Successful layout edits reroute connectors as straight segments before verification. Pixel-level browser geometry, effects and inferred author intent are outside the checker’s guarantee.

## External audit

[The new audit](../results/extended-compatibility.json) uses the same 20-row development prefix as the initial strict-parser audit: 19 available SVGs and one missing source. Both parsers still accept **zero complete diagrams**. The extended parser gets further on some rows, then rejects other visible shapes, decorations, text styles or unmarked connectors. This is infrastructure progress, not a demonstrated improvement in real-diagram editing coverage or learned accuracy.

The audit can cache the original responses privately under ignored `.cache/` and rerun without a network connection:

```sh
python benchmarks/audit_external.py --extended --cache-dir .cache/external \
  --output artifacts/external-audit.json
python benchmarks/audit_external.py --extended --cache-dir .cache/external --offline \
  --output artifacts/external-audit-offline.json
```

Add `--inventory` to record aggregate observations across all visible-tree primitives, rather than only the first rejection. The 19 available development sources contain 1,429 such primitives: 305 rectangles, 511 texts, 304 paths, 209 circles, 59 lines, 22 polygons, 10 images, seven uses and two ellipses. Eighteen rectangles cover the canvas. After excluding these backgrounds, 136 of 511 directly positioned text anchors lie in multiple rectangles and 185 lie in none. These counts are computed without resolving CSS visibility, glyph extents or semantic roles. They motivate container and decoration handling; they do not imply an accuracy result.

`constraint-recovery inspect input.svg --output artifacts/inventory.json` provides local primitive locations and geometry. It supports arbitrary finite 2D affine transforms for **inventory bounds only**; the editor retains its stricter transform policy. Ellipse envelopes are analytic; path bounds conservatively transform the path’s local axis-aligned envelope. Strokes, effects and referenced instances are not included. Inspection does not fetch resources or execute scripts. It is not a sanitizer and must never authorize embedding an otherwise rejected source. Checked-in external results retain aggregate observations, source IDs and hashes, without figure geometry or text.

Source figures are not committed. The upstream license is mixed by arXiv source; inspect individual rights before redistribution. These development rows are not an untouched test set. An independent relation-label evaluation and fresh holdout are still needed.
