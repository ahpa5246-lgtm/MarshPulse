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