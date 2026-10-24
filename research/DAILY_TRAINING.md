# Mash Plus — one continuous daily Kaggle training notebook through 15 November 2026

**Actual status as of 2026-10-24:** First daily GPU run **COMPLETED** and produced a persistent model+optimizer state ZIP. This is research continuation, NOT an environmental-use certification.

## The one notebook
- [Mash Plus Daily Trainer (single notebook source)](../kaggle/Mash_Plus_Daily_Trainer.ipynb)
- [Actual private Kaggle daily notebook](https://www.kaggle.com/code/minahussain111/mash-plus-daily-trainer)
- [Real first-run Kaggle/GitHub publisher](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40122702855)
- [Authenticated Kaggle `COMPLETE` + downloaded real checkpoint and reported scores](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40122873091)
- [Scheduled daily GitHub Actions workflow](../.github/workflows/mash-plus-daily-until-nov15.yml)

## Daily schedule and cutoff
Every day **05:15 Asia/Baghdad (02:15 UTC)** from 2026-10-25 to **2026-11-15 inclusive** (GitHub Actions scheduled events are best-effort, not guaranteed exact-time execution). Initial run executed manually on **2026-10-24**. A permanent cutoff in `scripts/mash_plus_daily_bridge.py` **refuses to request another GPU session after 2026-11-15**.

The workflow uses the existing GitHub Actions `KAGGLE` secret. It never prints or writes its value into the notebook. Every day:
1. Read true Kaggle status of `minahussain111/mash-plus-daily-trainer`. **SKIP** when previous version is queued or running, **FAIL CLOSED** on a genuine previous-day error rather than overwrite weights.
2. If the latest daily Kaggle version is **COMPLETE**, download its `Mash_Plus_Daily_State.zip`; verify its source hashes, trainer research-only label and checkpoint.
3. Create a **new version of the private Kaggle dataset** `minahussain111/mash-plus-daily-state` from that checkpoint and three training-source archives.
4. Upload the **same canonical notebook** as a new private Kaggle version and request GPU T4. It resumes model weights **and AdamW optimizer state**. No previous checkpoint means no silent fallback to training anew.
5. Train **2 bounded epochs** with rare-water and transition-month sampling from training targets only; validate only on the chronological validation portions of the three training regions; save a new checkpoint, full optimizer state, source fingerprints and report to Kaggle outputs.

## Source data and scientific protection
- Source imagery originated from the **completed real V4 Kaggle run**, not sample fixtures.
- The persistent private dataset contains Hawizeh, Central Marshes and Sinnaf Sentinel-2 arrays and their original source manifests, and **no** Dalmaj or Hammar test arrays or labels.
- Only **one** research model is repeatedly updated: persistence-residual **ConvGRU** (`MarshNetV3` class), starting from the best available V4 **research-only** checkpoint. The existing SMP U-Net remains a historical separate challenger, not another nightly retrain.
- It uses only the specified train/chronological validation partitions. Water-class F1 and Brier are monitored; no threshold tuning on the already examined geographic test regions.
- Repeated updates on the **same** training dataset do not create new independent evidence. New imagery/labels require provenance review and explicit safe integration; indefinitely training on fixed pseudo-labels risks overfitting.
- Published weights remain `RESEARCH_ONLY_NOT_FIELD_VALIDATED`. To claim performance at the competition, obtain untouched geographical/temporal and independently verified water reference labels and compare to hard/smoothed persistence and annual seasonality with uncertainty.

## Verified day-one result (NOT field or final test)
Authenticated Kaggle status `KernelWorkerStatus.COMPLETE`; separate GitHub audit downloaded the real ZIP and confirmed:

| Data point | Evidence |
|---|---:|
| Daily model iteration | 1 |
| Cumulative epochs completed | 2 |
| Kaggle run UTC date | 2026-10-24 |
| Best chronological validation Brier | 0.0285438791 |
| Best chronological validation wet-class F1 | 0.7791816390 |
| Persistent state ZIP size | 19,411,220 bytes |
| Field validated | **FALSE** |

These training-region validation numbers must not be compared directly to historical V4 Dalmaj test scores: the datasets, test windows, and population supports differ.

## Newly added: is the neural net really learning water change?

The [change-event diagnostics](../ml/change_diagnostics.py) now run after each day's checkpoint selection. On **chronological validation only** (no Dalmaj/Hammar test feedback), they separately measure:
- wet gain and drying recall, plus precision/F1 for actual wet↔dry transition events;
- event-only Brier and stable-water Brier versus smoothed last-month persistence **on identical unresampled clear pixels**;
- counts of uncertain satellite proxy labels near MNDWI 0.1 / NDVI 0.3 thresholds and scores excluding them as a **sensitivity analysis**, not ground truth;
- per-area and per-month evidence and observed changes.

The metric payload appears under `daily_training_report.json → validation_change_diagnostics` on subsequent complete Kaggle versions. This does not change the model's weights, checkpoint/optimizer compatibility, or original validation promotion rule; **its presence alone does not mean predictive skill improved**. [Scientific limitations and free external-data options](CHANGE_VALIDATION.md).

## Operational failure behavior
- A green **GitHub launch** only proves a push request; inspect the [read-only scientific audit](../.github/workflows/audit-mash-plus-daily.yml) for Kaggle `COMPLETE`, actual `day_index` and incremented `epochs_completed`.
- On Kaggle quota denial, output loss, unknown source, SHA mismatch, no observed labels, or a failed previous run, **do not overwrite the last good dataset checkpoint**. GitHub scheduled workflows can be delayed or skipped; the system does not fabricate missed training days.
- Kaggle may *automatically unzip* dataset files. The canonical notebook supports either intact state ZIP or validated extracted bundle files; this fix was necessary in the first day's startup.
- The privately stored source arrays and model checkpoints are NOT placed in the public GitHub repository, to avoid accidental data redistribution and conflating private experimental weights with a certified public model.

## Original system components
- PyTorch/AdamW official implementation for stateful training
- Sentinel-2 from ESA via Microsoft Planetary Computer; license remains Copernicus Sentinel Data Terms and Conditions
- Github Actions schedule, official Kaggle CLI (`kaggle==2.2.5`), private Kaggle Datasets version storage
- [Two-day real CPU continuation regression tests](../tests/test_daily_continuation.py): synthetic fixture only, for code correctness, not scientific performance

**Date scope:** The 15 November cutoff was selected as the working interpretation of "mid-November"; change it explicitly if the competition has a different date. No Kaggle GPU quota is guaranteed by this workflow.
