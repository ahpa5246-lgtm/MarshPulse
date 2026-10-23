# Organic river pattern and section motion (2026-10-23)

The original issue: the same square or closed loop was repeated only in selected regions; much of the white page remained blank. The user requested **long, naturally disappearing ends**, a unified light-page pattern and **scroll transitions**.

## Open-source components used (locally bundled)

- **D3 Contour** by Mike Bostock and contributors, ISC license. Already vendored in `vendor/d3-contour/`; original license kept in `vendor/d3-contour/LICENSE`. The implementation in `src/organic-pattern.mjs` invokes the actual D3 marching-squares isolines.
- **MotionFlow v1.0.0** by SLICEmyPAGE, MIT license. Local `vendor/motionflow/motionflow.min.js` and `motionflow.min.css`; license in `vendor/motionflow/LICENSE`. Use attribute-based scroll reveals, avoiding an npm build, CDN, or dynamic network dependency.

## How the long ends are made

Instead of outlining full repetitive closed contours, the engine selects **long open arcs** from distinct, seed-varying D3 iso-contour rings. Each open arc is extended at both ends along its actual tangent direction by 115–260 and 145–335 SVG units respectively, then converted to a **thin filled ribbon** with vertex-normal offsets. Width eases from exactly zero at the start to a bounded mid-arc thickness and tapers to zero at the far end. Individual zones have different contour seeds, threshold sets, color masks and sparsely placed coordinate dots.

This gives varied direction and graceful endpoints without hand-drawn fake geographical features.

## Application

- Homepage: hero, editorial introduction, destination cards, last light-colored call-to-action; dark marsh story remains clear and unpatterned.
- Water lab: intro, analysis workspace, evidence, methodology. Contours stay **behind** the actual water map and its click targets.
- Model: introduction and training reading section.
- Methods: introduction, research body and closing methodological note.

CSS masks leave the highest contrast behind the headings and forms. SVG is non-interactive, hidden from assistive technology, and does not pretend to be an authentic DEM or satellite raster.

MotionFlow (MIT) reveals below-the-fold titles, cards, study notes and supporting panels once upon scroll. The initial hero and interactive model controls are not hidden. Both the CSS river drift and MotionFlow honor reduced-motion preferences, and the site remains usable if external JS motion initialization fails.

## Verification

`node --test tests/*.test.mjs` covers the D3 ribbon geometry, tapered endings and deterministic zones. Playwright / Chrome smoke validates the raster click targets, all four routes, presence and pointer pass-through of the pattern, MotionFlow initialization, 320px overflow, CSV import/export and model training.

These are **ornamental lines derived from a synthetic scalar field**. They represent neither physical water routes nor Iraqi geographic coordinates. Source verification and ML training remain unchanged.
