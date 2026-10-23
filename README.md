# MarshPulse — مختبر اتصال أهوار العراق

MarshPulse is a working, zero-build Arabic RTL research prototype for inspecting monthly wetland grids, identifying connectivity bottlenecks, forecasting water presence, and comparing **hypothetical** rescue scenarios. It is **not** a field-validated hydrological model, a monitoring service, or an operational restoration recommendation system.

**Website (after successful Pages enablement):** https://ahpa5246-lgtm.github.io/MarshPulse/

## October 2026 design + MarshNet update

The site now has **four purposeful pages**, not one giant dashboard:

| Page | Primary outcome |
|---|---|
| [Home](index.html) | Explain the research question with an original cartographic illustration |
| [Water lab](lab.html) | Inspect connectivity, hypothetical interventions and model comparisons |
| [MarshNet studio](model.html) | Train our own neural MLP, compare chronologically held-out predictions against persistence and export fitted JSON weights |
| [Methods](methods.html) | Data provenance, independent checks and scientific limitations |

Visual direction: warm ivory paper, navy type, restrained copper annotations; responsive Arabic reading with clear inter-section whitespace. Compared against actual NASA Worldview, JRC Surface Water Explorer and Earth Timelapse in [design audit](docs/design-audit-2026-10.md), following the owner's Senior-level-website-development-skills guidelines.

**Custom model is functional:** browser-side seeded backpropagation / Adam on 5 temporal inputs and 12 hidden neurons; export .json then load it into the lab for scenario predictions. The independent [PyTorch trainer](ml/train.py) is Kaggle-ready and generates compatible `best.pt` and `marshnet.json`; see [Kaggle guide](ml/KAGGLE.md). We have NOT run Kaggle on a real Iraqi marsh dataset, do not claim we have.

The website is still a research prototype: synthetic default data and theoretical "rescue" credits cannot prove physical wetland improvement. Test evidence is in GitHub Actions browser and unit jobs; real-data scientific validation remains future work.

---

## MarshNet V2 (October 23, 2026)

**New research architecture:** [MarshNet V2](ml/marshnet_v2.py) is an original implementation of a residual spatial encoder + two ConvGRU temporal memory cells + U-Net-style skip decoder. It operates on genuine multi-month multispectral images in Python/PyTorch, using channels B03, B04, B08, B11, NDVI, MNDWI and observed-pixel validity. It predicts a next-month per-pixel probability for a **satellite-derived pseudo-label**, not observed hydraulic flow or an independently verified wetland truth.

Start with the [ready-to-run Kaggle notebook](kaggle/marshnet_v2_hawizeh.ipynb). It uses the [Planetary Computer STAC collector](ml/collect_sentinel.py) to fetch ESA Sentinel-2 Level-2A scenes for a **small pilot rectangle near Hawizeh, not the Ramsar boundary**, and the [V2 trainer](ml/train_satellite.py) to calculate blocked-in-time test Brier/IoU/F1 against a same-observed-pixel persistence baseline. Scene IDs, scene timestamps, cloud masks, missing observations, and data digest are tracked. The trainer requires a genuine image manifest for normal operation; the explicit `--synthetic-smoke` option generates fixtures for code testing and marks them as **not real satellite training**.

**Executed real-imagery proof:** [GitHub Actions run 40003182078](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40003182078) acquired 24 real Sentinel-2 monthly scenes near Hawizeh (2024–2025) and trained a 622,305-parameter V2 checkpoint. **The model FAILED the persistence baseline**: held-out same-valid-pixel Brier 0.107144 vs persistence 0.000700; wet-class F1 was 0. This is deliberately published as a negative result in [experiment evidence](research/experiments/hawizeh-v2-real-s2-2024-2025.json). These masks are unverified satellite-derived proxies; no field ground truth or scientific generalization was established. **Not yet done:** a Kaggle run in the user's account, independently validated marsh water labels, credible geographically held-out forecasting, and hydraulic intervention validation.

**Important:** The browser's [MarshNet M1](model.html) and the [Kaggle/PyTorch V2](ml/marshnet_v2.py) have different model architectures and weights. A `.pt` V2 checkpoint is **not** compatible with the M1 `.json` import widget. A V2 inference backend or a suitable browser conversion will be a separate engineering milestone.

**Editorial design reference:** homepage now uses an elongated cropped photograph of the southern Iraqi marshes by **Almendilawi / Wikimedia Commons, CC BY-SA 4.0**, with an attribution link in the UI. The photograph remains governed by its original terms; it is not licensed under this repo's MIT software license. We do not copy the user's third-party website screenshot or its proprietary assets.

## Living Grid — offline, D3-based animated contours

[Living Grid implementation and documentation](docs/living-grid.md): a locally vendored, ISC-licensed **D3 Contour** Marching Squares engine renders restrained marsh-inspired contour patterns and faint coordinate dots on all four pages. The map receives the stronger overlay, while text areas remain mostly clear. Contours move slowly through CSS and stop when reduced motion is requested. **These illustrative geometries are not measured Iraqi terrain or live satellite output.** Tests cover deterministic geometry, real Chromium rendering and noninterference with the interactive map.

## Organic flowing pattern and scroll-driven editorial motion

The light areas on all four pages now use **organic open-ended contour ribbons**, with very long tapered ends rather than short repeated rings. The field is generated locally from vendored **D3 Contour** (ISC); every section uses a different deterministic seed, and the map remains clickable over all ornaments. **MotionFlow** (MIT, vendored locally) adds staggered one-time section reveals and restrained transitions. No CDN or build tooling is required; original licenses are preserved.

See [implementation documentation](docs/organic-pattern-motion.md). **All lines are illustration only, not real Iraq height or water data.** Reduced motion, low-data modes and non-JavaScript readability are explicitly accounted for.

## Run

No npm, paid API, GPU, database or build step required.

~~~bash
git clone https://github.com/ahpa5246-lgtm/MarshPulse.git
cd MarshPulse
python -m http.server 8000
~~~

Open http://localhost:8000 in a modern browser; Codespaces can forward port 8000. Direct file:// opens can block JavaScript modules.

To run built-in Node.js 22+ tests:

~~~bash
node --check src/engine.mjs
node --check src/app.mjs
node --test tests/*.test.mjs
~~~

## Working features

| Feature | Implemented | Limitation |
|---|---|---|
| Spatial analysis | Wet area, component count, largest cluster, four-neighbor articulation points | Grid lacks coordinates / real marsh boundaries |
| Prediction | Logistic next-month cell-water classifier, trained on earlier months | Does not use measured discharge, evaporation or biodiversity |
| Independent check | Chronological holdout Brier/F1 against persistence | Synthetic scores are not field evidence |
| Scenario | Graph-based counterfactual selection of 0–12 grid cells | Does NOT simulate water volumes or ecological effects |
| Import | Strict CSV validation; duplicate/missing cells and gaps rejected | Data source never automatically verified |
| Evidence | Downloadable JSON with parameters, provenance, uncertainty limits and selected cells | Not a field validation or scientific publication |
| Website | Mobile responsive dark Arabic dashboard; live controls and maps | Github Pages deployment depends on repo settings |

## CSV data format

Import a complete, consecutive series with columns date,row,col,water:

~~~csv
date,row,col,water
2022-01,0,0,0.8
2022-01,0,1,0.2
2022-01,0,2,0.6
~~~

- date is YYYY-MM; YYYY-MM-DD is accepted but still treated as its month, and duplicate month/cell pairs are rejected.
- row and col are zero-based indices of a **complete rectangular grid**.
- water is a fraction between 0 and 1; a documented **fixed threshold 0.5** decides whether a cell is wet.
- Supply 12–72 **consecutive** months, at least 3×3 cells, at most 4900 cells and no nulls or absent cells.
- Imported measurements always remain **IMPORTED / UNVERIFIED** until external validation.
- The "example CSV" button downloads a **synthetic format sample**, not field data.

### Satellite export starting point

Paste earth-engine/export_monthly_grid.js in the Google Earth Engine Code Editor at https://code.earthengine.google.com/. Use a qualifying noncommercial research account, review/adjust the **coarse pilot bounding box**, run and start the task in the Tasks panel. The script aggregates monthly cloud-masked Sentinel-2 MNDWI water detections to grid cells. Its threshold and mask need independent calibration; it deliberately leaves invalid observations blank rather than calling them dry. Review and fix incomplete months before importing. Earth Engine script **has not been executed on a real account yet**.

Official sources: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED and https://earthengine.google.com/noncommercial/.

## Scientific algorithm

1. Water fraction above 0.5 creates a wet/dry raster; connected components and articulation points are computed over four-neighbor adjacency.
2. A small L2-regularized logistic classifier uses current water, previous water, four-neighbor wetness, month sine/cosine and intercept to forecast the next month's wet state.
3. Training uses only earlier target months. The final chronological quarter is unseen; the scoring records Brier error, wet-class F1, precision, recall and accuracy.
4. Persistence (next month is the same as this month) is the baseline. The UI explicitly flags whenever the model **does not outperform** this baseline in Brier error.
5. The scenario applies an **imaginary penalty** to predicted wetness to represent stress. A greedy solver preserves selected cells in a graph and compares component sizes. One credit does **not** represent water discharge, costs or actual restoration.

The demo generates 60 months of **deterministic synthetic data**, not a real map or observed history of the Iraqi marshes. No real observational model has been trained or validated.

## Kaggle / real training

The present classifier already trains in the browser; Kaggle GPU adds no benefit without validated real data. Once an independently checked satellite time series exists, Kaggle could compare more powerful models with blocked spatio-temporal evaluation and reproducible splits. Do not claim that training on this synthetic demonstration is scientific validation.

## Next milestones before scientific competition submission

- Confirm a real marsh polygon and source resolution; quality-check Sentinel-2 versus Sentinel-1 and independent reference imagery.
- Add actual discharge, water-level, salinity and topographic constraints; validate forecast uncertainty and seasonal baseline alternatives.
- Evaluate unseen years and **regions** to reduce spatial leakage, compare decision policies and sensitivity to the wet threshold.
- Obtain expert review before claiming environmental impact or suggesting real flow management.
- Publish a dataset card with source licenses, failures, spatial reference and provenance.

## Licensing

MIT license for original source code (LICENSE). Satellite imagery and platform use are governed by their original provider terms.
