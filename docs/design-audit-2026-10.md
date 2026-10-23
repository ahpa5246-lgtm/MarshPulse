# Design audit — 2026-10-23

This revision applies the journey-first, visual-comparison and error-matrix guidance from [Senior-level-website-development-skills](https://github.com/ahpa5246-lgtm/Senior-level-website-development-skills), especially docs/04-design-and-accessibility.md and docs/competitive-visual-qa-ar.md. This file is a review record; it is NOT proof that the upstream visual-quality-gate CLI was run.

## Observed defects and correction
- Single-page overload: home now presents the research thesis, lab holds the live analysis, model holds training, and methods holds scientific protocols.
- Repetitive green gradients, decorative orbits and cards: replaced with an ivory research-atlas surface, navy ink, restrained copper markers, original 2D illustrative water-network figure and readable editorial rhythm.
- Important map crowded by unrelated content: dedicated analysis page with a larger water map, companion controls and secondary outcomes.
- Little evidence of custom AI: a genuine, trainable five-input/12-hidden-unit MarshNet MLP with time-held-out evaluation and importable weights, plus an optional Kaggle PyTorch trainer.
- Claim/demonstration ambiguity: synthetic default is clearly labelled and field-data caveats remain visible.

## Released product comparison (official interfaces, accessed 2026-10-23)

1. NASA Worldview — https://worldview.earthdata.nasa.gov/ — direct remote-sensing comparator. Dedicated time/layer exploration; adopt workflow separation rather than copying appearance, code or tiles.
2. JRC Global Surface Water Explorer — https://global-surface-water.appspot.com/ — direct water-history map comparator. Learn the historical-view task and legend clarity; our added scenario remains hypothetical and is not a validated successor.
3. Google Earth Timelapse — https://developers.google.com/earth-engine/timelapse/about — aspirational visual storytelling. Learn large meaningful visual hierarchy with progressive detail. No copied brand or imagery.

## Direction decision
Direction A, selected: editorial wetland field atlas. Neutral paper, calm type hierarchy, provenance annotations, three major destinations. Requires more navigation but materially reduces screen density.
Direction B, rejected: dark sidebar-operated monitoring console with stacked metric cards. Suitable to expert analysts but retains the major single-screen cognitive-overload defect.

## Evidence and unresolved verification
Actual screenshots and user journey checks are produced by GitHub Actions' Scientific Core CI workflow, browser-smoke job (desktop 1440px and mobile 390px, home/lab/model/methods, interactive data operations, runtime errors). Test success alone does not certify beautiful design, WCAG compliance or mobile readability. Human review should include 320px reflow, Arabic font fallback, tab order, contrast and dataset-specific long errors.
The site remains a research prototype, not a field-validated Iraqi marsh management system.