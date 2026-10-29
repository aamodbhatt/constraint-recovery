# Browser-derived geometry for external SVGs

The XML inventory can identify source syntax, but it cannot resolve real glyph extents, all transforms, CSS or referenced instances. The optional Playwright bridge now measures those through the browser’s SVG geometry APIs without executing source scripts or loading secondary file/network references.

```sh
npm ci --ignore-scripts
npx playwright install chromium
node benchmarks/measure_svg.cjs figure.svg artifacts/geometry.json
```

The output binds to the exact UTF-8 source digest and records the browser version, canvas, source locations/IDs, normalized envelopes and computed styling. Text content is excluded by default; `--include-text` includes it for local annotation work. Measurements are read-only: they do not turn unsupported figures into editable constraint graphs, sanitize the SVG or establish author intent.

## Coordinates and limits

For each SVG graphics primitive, the browser provides a local `getBBox()` envelope and its screen transform `M_e`. If the root’s screen transform is `M_r` and viewBox origin is `o`, the normalized transform is `T(−o) M_r⁻¹ M_e`. Transforming the local envelope’s four corners gives a conservative axis-aligned envelope in normalized viewBox coordinates. The bridge also stores a projection into the source viewport for later annotation overlays.

Text envelopes use the actual local browser font resolution. Rotations, affine transforms and `<use>` instances can be measured even though the editor does not yet support all of them. CSS 3D transforms/perspective are rejected per primitive. Envelopes exclude stroke/marker outlines and do not certify clipping or filter effects; effects on ancestors are flagged. Display/visibility/opacity observations are not a pixel-level visibility test. Font fallback and blocked assets can change appearance.

Source JavaScript is disabled at the browser-context level. The context is offline, service workers are blocked, and the route handler permits only the main temporary SVG plus embedded raster images; secondary network and local-file requests are aborted. Source bytes, primitive count and elapsed work have explicit limits. Animation timelines are paused/cancelled for measurement. These controls are tested with active script and secondary-resource probes; they are not a claim to handle every hostile SVG or certify arbitrary browser rendering.

## External development audit

```sh
# First obtain the private source cache through audit_external.py.
node benchmarks/measure_external.cjs --rows 20
```

The bridge measures all **1,429 primitives across the 19 available sources** in the existing 20-row development prefix. One source remains missing. Full measurements stay in ignored `.cache/browser-geometry/`; the [committed audit](../results/browser-geometry-audit.json) contains only aggregate observations, source hashes and task IDs.

All 511 texts have browser envelopes. Excluding canvas-covering rectangle envelopes, 134 text envelopes lie inside multiple rectangle envelopes and 192 lie inside none. These are candidate geometric containments, not semantic labels. Two secondary resource references are blocked; the [dataset card](https://huggingface.co/datasets/yashengsun/SciDiagramRevision) explains that some raster panels are supplied as separate files. Their absence is retained in the audit rather than silently treating the rendering as complete.

**Editing support is still 0/19 complete external figures.** The new capability is geometry acquisition for compound-object and relation annotation. No new relationship accuracy or learned advantage has been established.

For a future local annotation viewer, original source should be displayed in an image context rather than inserted as active inline SVG. SVG image processing disables source scripts and external references; see [SVG 2 processing modes](https://www.w3.org/TR/SVG2/conform.html#secure-animated-mode). This is separate from the controlled browser context used to collect measurements.
