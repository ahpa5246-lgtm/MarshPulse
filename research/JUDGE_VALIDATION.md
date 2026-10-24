# Mash Plus V3 — evidence required before presenting scientific performance to judges

**Status:** RESEARCH ONLY; no independent field-water validation and no certified operational accuracy.
**Research question:** Can a compact ConvGRU forecast the next month's **visible open-water satellite proxy** more accurately than persistence and a 12-month seasonal baseline on previously unseen months **and** a never-trained geographic area?

## 1. Proof that computation is genuine, not a decorative website

- [Kaggle private notebook](https://www.kaggle.com/code/minahussain111/mash-plus-v3-geo-holdout) actually executes on an NVIDIA T4 if the Kaggle runtime has GPU enabled. The output must contain the exact Git commit hash, satellite scene IDs, timestamps, provenance manifest hashes, two geographically separate training AOIs, a third held-out Hammar AOI, trained checkpoint, and `v3_evaluation.json`.
- [GitHub Actions upload](../.github/workflows/publish-mash-plus-kaggle.yml) being green means only that Kaggle accepted a notebook/version and training request. It is **not** proof the notebook cells finished.
- Read real Kaggle `KernelWorkerStatus` using [the authenticated execution audit](../.github/workflows/audit-mash-plus-kaggle.yml). A finished Kaggle notebook must provide output evidence; a failed run is not evidence of a trained model.
- The public [browser demonstration](../model.html) trains a **distinct M1 baseline**, with synthetic demo data unless the user supplies a CSV. It is not the V3 GPU inference engine and must not be presented as if it displays V3 predictions.

## 2. Locked, falsifiable model test

Primary task: next-month wet proxy probability on observed clear pixels.
Labels are MNDWI > 0.1 and NDVI < 0.3 from Sentinel-2, **not independent observations**.
Fixed geographical train AOIs: Hawizeh and Central Marshes. Hammar is *never* used for model fitting, calibration or architecture/seed selection.
Use only data through month t−1 for forecasting month t. Training-only normalization.
Compare on **exactly the same cloud-free target pixels** to:
1. hard last-month persistence;
2. 0.01 / 0.99 smoothed last-month persistence;
3. 12-month seasonal reference.

Report the actual class prevalence, observed pixel coverage, per-region and per-month confusion matrices (TP, FP, FN, TN), wet-class recall/precision/F1, Brier score, and error examples. Never headline overall accuracy in a dry-dominated dataset.

**Predeclared minimum research promotion gate** (not universal scientific certification):
- validation selects a seed that beats *all* three baselines in Brier by >=2% relative and >=0.0005 absolute, **and** wet F1 by >=0.02;
- independent geographical test must reproduce these numerical improvements on the same clear observations, have >=25 positive proxy pixels, >=1% wet class prevalence, >=6 comparable months including >=3 wet months, >=20% common pixel coverage, and improvements in a majority of comparable months;
- missing or undefined metrics fail closed;
- **do not tune hyperparameters on the Hammar test results** to make it pass; predeclare a different future test site before changing the model.

These are conservative engineering screening gates, **not** significance tests, peer-review acceptance standards, or guarantees of generalization. Monthly satellite observations are correlated, as are adjacent pixels. The result must distinguish high pixel count from independent evidence across months and marshes.

Run the reproducible decision audit after downloading Kaggle `v3_evaluation.json`:

```bash
python ml/judge_readiness.py \
  --input v3_evaluation.json \
  --out judge_readiness.json \
  --markdown judge_readiness.md
```

Or rerun the [GitHub Kaggle audit workflow](../.github/workflows/audit-mash-plus-kaggle.yml) **after** Kaggle reports COMPLETE; it downloads and checks actual Kaggle outputs without retraining.

## 3. What would qualify as independent external validation?

1. Predefine representative sample units stratified by visible-water, dry-land, margins, vegetated wetland and different dates/regions; use an auditable probability-based sampling protocol rather than cherry-picking impressive examples.
2. Have human specialists independently annotate temporally matched higher-resolution imagery and/or georeferenced field observations. Record their image sources, timestamps, location, annotator identity and agreement/disagreement. Resolve ambiguous pixels transparently.
3. Measure weighted confusion matrices, user's/producer's class accuracies, precision, recall, wet-class F1, reference area, and uncertainty intervals (for example, region/month-block bootstrap and sampling-design-aware confidence intervals where appropriate).
4. Keep reference set independently sealed before any new training. Clearly document disagreement due to reeds, shadows, cloud, sediment and flooded vegetation.
5. Seek qualified external ecological/remote-sensing review. Even success does not imply predictions of water **volume, inflow, hydraulic connection, water quality, biodiversity or restoration effectiveness**.

Scientific accuracy-area sampling design reference: Olofsson et al. (2014), *Remote Sensing of Environment* 148:42–57, DOI 10.1016/j.rse.2014.02.015.

## 4. Honest presentation to judges

**Supported:** "Mash Plus V3 is a reproducible research prototype for forecasting a Sentinel-2 visible-water proxy, with real-image acquisition, code-backed neural training, chronological model selection, and a held-out geographic test against persistence and seasonal baselines."

**Conditionally supported only if post-run results pass the audit:** "The model surpassed prespecified proxy benchmarks in the Hammar test area for this study window."

**Unsupported:** "The system is globally recognized, field validated, predicts real marsh water volume, determines rescue interventions or reliably outperforms operational water monitoring systems."

Show failure cases and uncertainty along with successes. If `judge_readiness.json` reports `NOT_DEMONSTRATED`, present the negative result and the improved research method rather than a fabricated accuracy number.

## 5. Reproducibility caveat

The initial Kaggle run cloned commit `9d6b44d366dcbe50eef423d583b96c23e0681ca8`.
A subsequent code review fixed a checkpoint-selection discrepancy: geographic testing must use the **validation-approved** checkpoint, not an unrelated best research seed. That correction cannot modify a notebook runtime already using the old commit. If the first report is affected, a **new full validation/test run on the corrected commit** is required before any comparative performance claim.
