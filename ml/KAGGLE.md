# MarshNet V3 — Three-area Kaggle GPU research challenge (October 2026)

**New unified notebook:** [MarshPulse_V3_GeoHoldout_GPU.ipynb](../kaggle/MarshPulse_V3_GeoHoldout_GPU.ipynb). Kaggle: select **GPU** and enable **Internet**, then **Run All**. The notebook retrieves its code from GitHub and records the exact commit SHA. It acquires ESA Sentinel-2 imagery near **Hawizeh + Central** (training) and **Hammar** (entirely held-out spatial region), with fixed-date monthly chronologies, strict scene provenance and cloud masks.

The V3 `ml/marshnet_v3.py` corrects a smoothed persistence prior using a residual ConvGRU; `ml/train_v3.py` performs three fixed-seed trials and selects models **solely** on temporal validation. Crucially, we evaluate four baselines on identical clear pixels: *hard persistence, smoothed persistence, prior-year seasonality, V3*. The third baseline prevents mistaking simple probability smoothing for neural learning. A **≥2% relative AND ≥0.0005 absolute validation Brier advantage**, at least 25 observed wet validation pixels, and **≥0.02 absolute wet-class F1 improvement over the strongest simple baseline** are required to select V3. Per-month paired losses are retained so correlated pixels are not confused with independent study replicates. Entirely clouded-out months retain `VALID=0` and are not silently converted to dry land. Rejected model checkpoints are archived as **RESEARCH_ONLY**, not called deployable.

The Hammar spatial test is read only after validation selection, which does not prove field accuracy. Three rectangular pilot AOIs are **not official site boundaries**. The water target is an unverified MNDWI/NDVI proxy. The browser M1 JSON engine cannot run the PyTorch V3 checkpoint. No independent field labels or true hydrological forecasts are included. **Never issue real-world environmental decisions from this notebook.** Kaggle runtime cannot be launched via a GitHub connector; only the notebook is published. Source scene identifiers and SHA-256 digests demonstrate provenance consistency and reproducibility, **not cryptographic authentication of the ESA source or field truth**. GitHub Actions has separately run an 8-epoch, 2-seed real-image CPU rehearsal; this does **not** establish that the full three-area Kaggle study has been run.

CPU rehearsal with genuinely acquired Hawizeh imagery: [MarshNet V3 real research CI](https://github.com/ahpa5246-lgtm/MarshPulse/actions/workflows/v3-real-challenge.yml). Historical V2 comparison: [60-month verified run](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40064994264).

---

# Important: new image-based V2 training

For the new stronger spatial-temporal ConvGRU architecture and **real Sentinel-2 acquisition**, use the [MarshNet V2 Hawizeh Kaggle notebook](../kaggle/marshnet_v2_hawizeh.ipynb), [collector](collect_sentinel.py) and [trainer](train_satellite.py). V2 outputs a PyTorch `marshnet_v2.pt` checkpoint. The commands below are for the **older lightweight M1** CSV baseline and will not train V2. The first genuine V2 pilot run is [documented with a negative baseline result](../research/experiments/hawizeh-v2-real-s2-2024-2025.json).

---

# MarshNet — Kaggle reproducibility

The trainable architecture lives in ml/train.py. It updates real PyTorch weights and exports best.pt, marshnet.json and metrics.json. The objective is next-month water-presence classification, **not** solar-filament segmentation.

## Dataset first
Prepare verified 12–72 complete, consecutive monthly grids as date,row,col,water. Do not use the synthetic demo to claim real Iraqi marsh forecasting. Review cloud masking, AOI and water thresholds for every Sentinel-derived CSV.

## Kaggle notebook cells
Connect a Kaggle input dataset containing monthly.csv, then run:

    !git clone https://github.com/ahpa5246-lgtm/MarshPulse.git /kaggle/working/MarshPulse
    !pip install -q -r /kaggle/working/MarshPulse/ml/requirements.txt
    !python /kaggle/working/MarshPulse/ml/train.py --csv /kaggle/input/YOUR-DATASET/monthly.csv --epochs 60 --seed 42 --out /kaggle/working/marshnet

Use the exact dataset path shown in the Kaggle sidebar. Internet access is needed for git clone if the source repository is not supplied as an input. GPU is optional for a small grid.

## Artifacts
- best.pt: best-validation PyTorch checkpoint.
- marshnet.json: trained weights and evaluation metadata compatible with MarshPulse's import control on lab.html.
- metrics.json: held-out error and F1 for MarshNet and persistence.

The holdout consists of later dates than training and internal validation. Better Brier on these dates does not establish physical restoration value. A region-held-out evaluation and independent field checking are still needed.

The lab checks import date range, grid shape and data category, but it **does not cryptographically verify that the imported model was trained on precisely the CSV currently open**. Save a separate SHA-256 of source data and publish provenance before entering scientific competitions.

Current public repo does not contain a field-verified training dataset or a completed authentic Kaggle training run.