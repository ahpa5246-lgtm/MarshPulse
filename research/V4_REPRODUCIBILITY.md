# Mash Plus V4: real-satellite experiment and reproducible independent checks

**Research status:** GPU experiment submitted to Kaggle. No field validation, ecological certification, or proof of neural superiority is implied by publication or code tests.

## Why this experiment exists
The complete V3 Kaggle/T4 study **rejected every neural seed** and selected persistence. On geographically held-out Hammar, neural Brier 0.005359 versus smoothed persistence 0.005371, and wet-class F1 was identical 0.654275. Only 836 out of 103,737 matched pixels were classified wet by the unverified Sentinel index (0.81%); overall accuracy alone is inappropriate. [Evidence](experiments/mash-plus-v3-kaggle-real-2026-10-24.md).

V4 predeclares **two** alternative learners and makes it possible to detect, rather than hide, continued failure:
- the original persistence-anchored ConvGRU;
- a persistence-residual U-Net from [segmentation_models_pytorch](https://github.com/qubvel-org/segmentation_models.pytorch), with ResNet18 encoder and no external pretrained weights (the source library is primarily MIT-licensed with [additional component-specific licenses](https://github.com/qubvel-org/segmentation_models.pytorch/tree/main/LICENSES)). This is an imported reviewed package, not a pasted copy of unknown code.

Both are trained using real ESA Sentinel-2 L2A accessed with the open-source [pystac-client](https://github.com/stac-utils/pystac-client), [Planetary Computer SDK](https://github.com/microsoft/planetary-computer-sdk-for-python), and [rasterio](https://github.com/rasterio/rasterio). Existing package licenses and Sentinel data-use conditions apply; using them does **not** confer peer review on our trained weights.

## Fixed geographical design
These rectangles approximate **pilot sampling boxes**, NOT official marsh boundaries:

| Purpose | Named area | W,S,E,N (longitude/latitude) | Source |
|---|---|---|---|
| Train | Hawizeh | 47.64,31.53,47.74,31.63 | [KBA 8056](https://www.keybiodiversityareas.org/en/site/factsheet/8056) |
| Train | Central Marshes | 47.00,31.04,47.10,31.14 | Previous research pilot; not a KBA boundary |
| Train | Sinnaf Seasonal Wetlands | 47.2667,31.8167,47.3667,31.9167 | [KBA 8050](https://www.keybiodiversityareas.org/en/site/factsheet/8050), centroid 31.8667,47.3167 |
| **New sealed spatial test** | Dalmaj Marsh | 45.4167,32.15,45.5167,32.25 | [KBA 8043](https://www.keybiodiversityareas.org/en/site/factsheet/8043), centroid 32.2000,45.4667 |

48 complete monthly periods: 2022-10 through 2026-09. 64×64 spatial grid covering each ~10 km rectangular pilot, so spatial pixel cells are **coarser than native Sentinel-2 10m**, and cannot be falsely described as 10m forecasts.

Historical Hammar data was already inspected in V3: **not used as a fresh V4 final test**. All AOI rectangles/date ranges were frozen in the V4 notebook **before** new test collection. Any changes after Dalmaj scores have been viewed require an additional untouched site/test period.

## Train-only rare wet class methodology
- `--wet-bce-ratio 3`: explicit positive class weight in masked training BCE combined with proper Brier.
- `--wet-sampler-boost 3` and `--change-sampler-boost 3`: WeightedRandomSampler uses **only training target months**, weighting observed wet fractions and wet/dry transition rates.
- `--crop-size 32`, `--water-center-prob .75`: target-aware training-only crops near rare water/shoreline pixels; **never crop/resample validation or test**.
- Both models start from a zero residual on the same smoothed persistence prior (soft prior 0.01/0.99).
- This resampling can distort probability calibration or overfit: compare **natural-prevalence validation Brier and wet-class F1**; reject improved training loss without a validation gain.

## Honest automated selection and comparison
Every model is run with identical, chronologically divided training regions. Only validation data selects checkpoint/seed or neural architecture. Both frozen alternatives are then reported on the independent Dalmaj heldout region. A new experiment with different hyperparameters cannot reuse Dalmaj as an untouched test.

**Validation numerical screen (minimum, not scientific certification):** at least 25 wet target pixels, Brier advantage ≥2% relative *and* 0.0005 absolute over the best of three simple baselines, and wet-class F1 gain ≥0.02 above the best simple comparator. New unseen geography must meet the same post-selection spatial accuracy screen and sufficient wet examples/months. The [judge readiness gate](../ml/judge_readiness.py) fails closed on missing/worse results and cannot authorize operational use.

References: prior-month persistence, smoothed prior, previous-year seasonality. Report true/false wet pixels, precision, recall, F1, Brier, observation coverage, month-wise paired scores. Pixel-level support counts are **not independent statistical replicates** because geographic neighbors and monthly scenes are correlated.

## External evidence: real work versus things nobody can fabricate
1. **Landsat 8/9 cross-sensor check** ([code](../ml/landsat_crosscheck.py)). Uses Planetary Computer `landsat-c2-l2`, USGS QA_PIXEL cloud/shadow/snow bits, the Collection 2 surface reflectance offset/scale, and aligned monthly windows. This produces a different optical sensor's **water INDEX proxy**. Monthly acquisitions are not simultaneous; 30m Landsat data is resampled to the much coarser study grid. Therefore Landsat agreement is **supplementary sensor agreement, NOT field truth**.
2. **Blinded reference tasks** ([code](../ml/prepare_field_review.py)). Generates a dated lat/long CSV for independent human image annotation, sampling visible-water, near-water, and dry examples across heldout months. The annotation values are **blank**. This cannot be counted as validated labels until actual independent reviewer/field data arrive. Reviewers must inspect contemporaneous higher-resolution imagery and document source, date, uncertainty and agreement.
3. Independent sampling/accuracy design: [Olofsson et al. 2014](https://doi.org/10.1016/j.rse.2014.02.015); class-stratified or probability-proportional reference sampling needs appropriate inclusion weights for area accuracy. Oversampling rare water without correcting population weights creates biased population estimates.

## Run/provenance links
- [Kaggle V4 notebook](https://www.kaggle.com/code/minahussain111/mash-plus-v4-independent-dalmaj)
- [source notebook](../kaggle/Mash_Plus_V4_Independent_Dalmaj_GPU.ipynb)
- [authenticated Github-to-Kaggle GPU request](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40117636891)
- [separate Kaggle scientific evidence audit](../.github/workflows/audit-mash-plus-v4-kaggle.yml)
- [CI with real SMP forward/backward and synthetic anti-leakage checks](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40117489555)

A GPU run status of **COMPLETE** only establishes that code executed. Whether a model is useful depends on complete `judge_readiness.json` reports, defensible blind reference data, uncertainty estimation and external domain-expert assessment. We will record negative or inconclusive results as such.
