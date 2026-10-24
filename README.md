# MarshPulse — مختبر اتصال أهوار العراق

MarshPulse is a working, zero-build Arabic RTL research prototype for inspecting monthly wetland grids, identifying connectivity bottlenecks, forecasting water presence, and comparing **hypothetical** rescue scenarios. It is **not** a field-validated hydrological model, a monitoring service, or an operational restoration recommendation system.

**Website (after successful Pages enablement):** https://ahpa5246-lgtm.github.io/MarshPulse/

## October 2026 design + Mash Plus research-model branding

The site now has **four purposeful pages**, not one giant dashboard:

| Page | Primary outcome |
|---|---|
| [Home](index.html) | Explain the research question with an original cartographic illustration |
| [Water lab](lab.html) | Inspect connectivity, hypothetical interventions and model comparisons |
| [Mash Plus studio](model.html) | Train our own neural MLP, compare chronologically held-out predictions against persistence and export fitted JSON weights |
| [Methods](methods.html) | Data provenance, independent checks and scientific limitations |

Visual direction: warm ivory paper, navy type, restrained copper annotations; responsive Arabic reading with clear inter-section whitespace. Compared against actual NASA Worldview, JRC Surface Water Explorer and Earth Timelapse in [design audit](docs/design-audit-2026-10.md), following the owner's Senior-level-website-development-skills guidelines.

**Custom model is functional:** browser-side seeded backpropagation / Adam on 5 temporal inputs and 12 hidden neurons; export .json then load it into the lab for scenario predictions. The independent [PyTorch trainer](ml/train.py) is Kaggle-ready and generates compatible `best.pt` and `marshnet.json`; see [Kaggle guide](ml/KAGGLE.md). The lightweight M1 CSV example is not the image-based V3 Kaggle experiment; do not confuse them.

The website is still a research prototype: synthetic default data and theoretical "rescue" credits cannot prove physical wetland improvement. Test evidence is in GitHub Actions browser and unit jobs; real-data scientific validation remains future work.

---

## Mash Plus — one daily continuing Kaggle notebook (through 15 November 2026)

**The first real daily Kaggle GPU continuation ran successfully on 2026-10-24**, starting from V4 research-only ConvGRU weights and saving the model, AdamW optimizer and data manifest in a private state ZIP. It completed **day 1 / 2 cumulative epochs**. [Actual Kaggle COMPLETE state and downloaded 19.4 MB research checkpoint proof](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40122873091); [separate same-day no-duplicate safety check](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40123033045).

The [single canonical Kaggle notebook](kaggle/Mash_Plus_Daily_Trainer.ipynb) and [real private Kaggle notebook](https://www.kaggle.com/code/minahussain111/mash-plus-daily-trainer) run via [daily GitHub Actions scheduler](.github/workflows/mash-plus-daily-until-nov15.yml) at **05:15 Baghdad**, with a hard cutoff after **2026-11-15**. Each next day waits for a successful previous Kaggle version, transfers its checkpoint to a versioned private dataset, and resumes rather than trains afresh. Quota exhaustion, missing/failed outputs, or schedule delays can prevent a given day; there is **no guarantee of 23 GPU sessions**. [Complete implementation, safeguards, and reproducibility](research/DAILY_TRAINING.md).

**Scientific status remains research-only.** Repeated training on three fixed ESA Sentinel-2 regions does NOT establish independent field accuracy or scientific recognition. Hammar and Dalmaj test data are excluded from daily model fitting.

---

## Mash Plus V4 — real open-source challenger + fresh test geography (October 24, 2026)

**[New V4 Kaggle GPU notebook](kaggle/Mash_Plus_V4_Independent_Dalmaj_GPU.ipynb)** was uploaded as a private version 1 and GPU execution requested via [successful GitHub-to-Kaggle workflow](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40117636891). [Authenticated Kaggle verification](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40117780164) reported **RUNNING**, not completed or scientifically validated, at the time of the check. [Open the actual Kaggle notebook](https://www.kaggle.com/code/minahussain111/mash-plus-v4-independent-dalmaj).

This preregistered experiment adds a **genuine upstream** open-source [segmentation_models_pytorch](https://github.com/qubvel-org/segmentation_models.pytorch) ResNet18 U-Net alongside ConvGRU; rare wet/transition sampling and targeted training crops use **training labels only**. Three real Sentinel training pilots: Hawizeh, Central Marshes, Sinnaf; the **new, genuinely unseen Dalmaj Marsh** is the spatial test because V3's Hammar holdout was already examined. It also implements independent-SENSOR Landsat 8/9 optical screening and generates a **blank, blinded** human-reference annotation queue (not fabricated field labels).

**Scientific interpretation:** V3 failed to improve wet F1 beyond persistence. V4 is an attempt to address that failure, **not proof it has been solved**. The first authenticated status check confirmed only active execution; a scientifically credible result requires sealed Dalmaj scores, Brier/F1 superiority on natural support, and independent reviewer labels. The original V3 negative result remains published.

Read the [full protocol, license provenance, and limitations](research/V4_REPRODUCIBILITY.md). CI includes real upstream U-Net forward/backward, Sentinel sampler anti-leakage, Landsat QA and blind sampling tests; [passing CI proof](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40117489555).

---

## Mash Plus V3 — executed Kaggle GPU research, negative neural baseline result

**[One Kaggle notebook: Mash Plus V3 Geo-Holdout GPU](kaggle/MarshPulse_V3_GeoHoldout_GPU.ipynb)**. This is the Mash Plus V3 research challenger (legacy Python class: `MarshNetV3`), not a certified replacement for its V2 predecessor. It includes actual Sentinel-2 collection from two training pilot areas and an independently held-out third pilot area, a persistence-residual ConvGRU architecture, three independent seeded trainings, chronological validation, and strict **hard/soft persistence plus annual seasonality** comparisons. Promotion requires meaningful validation improvement over ALL simple baselines; failed neural candidates remain labeled RESEARCH ONLY.

The single-secret [GitHub-to-Kaggle publisher](.github/workflows/publish-mash-plus-kaggle.yml) **has run successfully** using the repository's `KAGGLE` secret and requested GPU execution. Its default manual `run_training=false` uploads only; the separately authorized first GPU execution was triggered once through a commit marker. [Proof of upload](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40113554032).

**Actual result (2026-10-24):** the three-area V3 notebook **completed on Kaggle Tesla T4** using real Sentinel-2 data. All three neural seeds FAILED the validation improvement gates; `PERSISTENCE_BASELINE` was selected. On spatially held-out Hammar, neural Brier = 0.005359 vs smoothed persistence 0.005371 (far below the prespecified gain) and both wet F1 = 0.654275, with only 0.81% wet pixels. The model is **NOT scientifically or operationally validated**. See [real evidence table and reproducible run links](research/experiments/mash-plus-v3-kaggle-real-2026-10-24.md), [judge validation protocol](research/JUDGE_VALIDATION.md), and [automated scientific audit](ml/judge_readiness.py).

---

## Scientific core upgrade (October 24, 2026) — real data first

**The previous real-pilot V2 model failed to beat persistence. It is not reliable or safe for water allocation, drought warnings or restoration decisions.** We have therefore implemented a reproducible, conservative improvement path rather than advertising artificial accuracy:

- `ml/quality_gate.py`: coverage/wet-class audits, honest undefined water-class metrics, three-way **same-observed-pixel** comparison against persistence and prior-year seasonal baseline, and an explicit `NOT_VALIDATED` scientific readiness gate.
- `ml/monitor_wetland.py`: useful independent satellite screening output, even if neural prediction fails: month-level observed water-proxy area, cloud coverage, matched-pixel change, image-space clusters (not actual hydraulic connections), and CSV/JSON exports.
- `ml/train_satellite.py`: class weighting estimated from **training observations only**; benchmark and quality audit included with every checkpoint. The data input is required and synthetic tests cannot masquerade as real imagery.
- [Real Satellite Monthly Research workflow](.github/workflows/real-satellite-pilot.yml): 60 most recent **complete** months near Hawizeh KBA, scheduled monthly on the 10th UTC as well as manually invokable. Availability depends on Sentinel scenes, Planetary Computer and available GitHub Actions minutes. Artifacts are retained for up to 90 days; CI **does not** claim success when real observations are missing.
- **Observed water dashboard:** [monitor.html](monitor.html) reads [36 real monthly screening observations](data/hawizeh-actual-observations.json) derived from the October 2023–September 2026 pilot. These are historical *proxies*, rounded for plotting, not current water quantities or hydrological truth.
- **Validation-class problem discovered:** the first 36-month run held 20,466 clear validation pixels but zero satellite-proxy wet pixels; validation-only calibration therefore correctly refused to fit. The rolling job now uses **60 months** to give training and validation a better chance of containing both wet and dry seasons. This is not yet a proven improvement.
- MNDWI threshold-sensitivity diagnostics are now published to show how changing the wet-proxy cutoff can change measured surface area.
- New quality and cloud-gap regression tests run on every GitHub push.

See the [scientific validation roadmap and reproducibility instructions](docs/scientific-readiness-roadmap.md). Until geographically independent evaluation and independent reference labels exist, there is **no operationally validated model** and no measured water saving attributable to MarshPulse.

---

## MarshNet V2 (October 23, 2026)

**New research architecture:** [MarshNet V2](ml/marshnet_v2.py) is an original implementation of a residual spatial encoder + two ConvGRU temporal memory cells + U-Net-style skip decoder. It operates on genuine multi-month multispectral images in Python/PyTorch, using channels B03, B04, B08, B11, NDVI, MNDWI and observed-pixel validity. It predicts a next-month per-pixel probability for a **satellite-derived pseudo-label**, not observed hydraulic flow or an independently verified wetland truth.

Start with the [ready-to-run Kaggle notebook](kaggle/marshnet_v2_hawizeh.ipynb). It uses the [Planetary Computer STAC collector](ml/collect_sentinel.py) to fetch ESA Sentinel-2 Level-2A scenes for a **small pilot rectangle near Hawizeh, not the Ramsar boundary**, and the [V2 trainer](ml/train_satellite.py) to calculate blocked-in-time test Brier/IoU/F1 against a same-observed-pixel persistence baseline. Scene IDs, scene timestamps, cloud masks, missing observations, and data digest are tracked. The trainer requires a genuine image manifest for normal operation; the explicit `--synthetic-smoke` option generates fixtures for code testing and marks them as **not real satellite training**.

**Executed real-imagery proof:** [GitHub Actions run 40003182078](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40003182078) acquired 24 real Sentinel-2 monthly scenes near Hawizeh (2024–2025) and trained a 622,305-parameter V2 checkpoint. **The model FAILED the persistence baseline**: held-out same-valid-pixel Brier 0.107144 vs persistence 0.000700; wet-class F1 was 0. This is deliberately published as a negative result in [experiment evidence](research/experiments/hawizeh-v2-real-s2-2024-2025.json). These masks are unverified satellite-derived proxies; no field ground truth or scientific generalization was established. **Not yet done:** independently verified wetland-water labels, proof of neural forecasting advantage across independent test regions, and hydraulic intervention validation.

**Important:** The browser's [MarshNet M1](model.html) and the [Kaggle/PyTorch V2](ml/marshnet_v2.py) have different model architectures and weights. A `.pt` V2 checkpoint is **not** compatible with the M1 `.json` import widget. A V2 inference backend or a suitable browser conversion will be a separate engineering milestone.

**Editorial design reference:** homepage now uses an elongated cropped photograph of the southern Iraqi marshes by **Almendilawi / Wikimedia Commons, CC BY-SA 4.0**, with an attribution link in the UI. The photograph remains governed by its original terms; it is not licensed under this repo's MIT software license. We do not copy the user's third-party website screenshot or its proprietary assets.

## Living Grid — offline, D3-based animated contours

[Living Grid implementation and documentation](docs/living-grid.md): a locally vendored, ISC-licensed **D3 Contour** Marching Squares engine renders restrained marsh-inspired contour patterns and faint coordinate dots on all four pages. The map receives the stronger overlay, while text areas remain mostly clear. Contours move slowly through CSS and stop when reduced motion is requested. **These illustrative geometries are not measured Iraqi terrain or live satellite output.** Tests cover deterministic geometry, real Chromium rendering and noninterference with the interactive map.

## Organic flowing pattern and scroll-driven editorial motion

The light areas on all four pages now use **organic open-ended contour ribbons**, with very long tapered ends rather than short repeated rings. The field is generated locally from vendored **D3 Contour** (ISC); every section uses a different deterministic seed, and the map remains clickable over all ornaments. **MotionFlow** (MIT, vendored locally) adds staggered one-time section reveals and restrained transitions. No CDN or build tooling is required; original licenses are preserved.

See [implementation documentation](docs/organic-pattern-motion.md). **All lines are illustration only, not real Iraq height or water data.** Reduced motion, low-data modes and non-JavaScript readability are explicitly accounted for.

## Floating glass navigation (MIT, no CDN)

All four pages have a responsive supplementary **floating navigation dock**. It links Home, Water Lab, MarshNet and Methods, uses [Headroom.js](https://github.com/WickyNilliams/headroom.js) to respond to scroll direction and [Gumshoe](https://github.com/cferdinandi/gumshoe) to highlight the visible page chapter. A thin progress indicator and a back-to-top shortcut help navigate longer research pages. The primary header remains unchanged as a no-JavaScript fallback. Mobile layouts move the pill to the safe-area-aware bottom; focusing scientific input fields temporarily hides the dock.

Both upstream libraries are included locally under `vendor/headroom` and `vendor/gumshoe`, along with their original MIT licenses. See [detailed engineering notes](docs/floating-navigation.md). The feature does not affect MarshNet weights, study data or scientific validation.

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
