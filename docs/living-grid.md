# Living Grid — marsh-inspired background contour system

**Implemented**: October 23, 2026.

## Source and license

The contour geometry is computed with the actual **D3 Contour** Marching Squares algorithm (Mike Bostock and contributors), copied from https://github.com/d3/d3-contour at its v4 source layout and adapted solely to use .mjs imports and a tiny, local array-threshold helper. The upstream code is **ISC-licensed**, with the unmodified copyright and license notice at [vendor/d3-contour/LICENSE](../vendor/d3-contour/LICENSE). We deliberately avoided AGPL-licensed alternate contour packages to keep rights clear. Application-specific procedural field synthesis and SVG composition are in [src/living-grid.mjs](../src/living-grid.mjs).

### Why local vendoring?
- Works on GitHub Pages, Codespaces and an offline local HTTP server without CDN connections.
- Builds geometries once on page load: no animation loop or recurring D3 recalculation.
- Small fixed-size scalar fields (90×55–106×59), five or six fixed thresholds.
- Deterministic coordinates permit snapshot regression testing.

## What it renders

* A noninterfering isocontour overlay on the home hero.
* A lighter, transparent trace behind the chapter cards.
* A stronger cyan contour layer **around** the interactive water map, with coordinate points but behind the raster and all click targets.
* Small faint traces on scientific page intros (MarshNet and methodology).
* A slowly moving water-like effect driven by CSS animation (84-second alternation), plus near-static coordinate-dot glimmer.

## Scientific integrity and readability

This is **illustrative ornament** generated from a seeded analytic scalar field, **not** Iraqi marsh topographic elevation, a Sentinel raster, DEM, or a measurement. The label reads *STUDY GRID · ABSTRACT*. The UI's actual simulation remains an independent data display; do not interpret the ornament as scientific output.

CSS alpha masks reduce contour visibility behind headings and text. The interactive map stays above all ornamental paths. SVG is `aria-hidden="true"`, `focusable="false"`, with `pointer-events:none`; no screen reader or mouse target changes.

Motion is explicitly disabled for `prefers-reduced-motion:reduce` and `prefers-reduced-data:reduce`. Opacity and dot density are lower on mobile. These constraints matter more than maximal effect density.

## Verification

Automated tests include:
- deterministic scalar field and nonflat generated values;
- the vendored ISC D3 contour algorithm producing valid, closed SVG rings;
- real Chromium rendering of contour SVG paths and coordinate dots;
- preserving the interactive map's pointer interactions;
- regression tests for all site routes, CSV, training, export and 320px reflow.

Screenshots and JSON artifacts are produced by GitHub Actions' `Scientific Core CI` workflow as `marshpulse-browser-proof`.
