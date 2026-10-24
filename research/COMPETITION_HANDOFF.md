# Mash Plus — competition research handoff and automatic operation
**Frozen handoff prepared 2026-10-24 · Model status: RESEARCH ONLY · Cutoff: 2026-11-15**

## Read this before presenting any score to the judges

The V3 and V4 genuine Kaggle GPU experiments confirmed the neural networks executed and learned, but did **not** demonstrate meaningful improvements over persistence. The V4 independent Dalmaj test recorded ConvGRU Brier **0.02660767** vs smoothed persistence **0.026600997** (lower is better), and ConvGRU wet-class F1 **0.57444** vs persistence **0.57335**; the experiment rejected both candidate architectures. No reference dataset of independently surveyed water has been collected. These negative findings remain published at [V4 methodology](V4_REPRODUCIBILITY.md) and [V3 historical evidence](experiments/mash-plus-v3-kaggle-real-2026-10-24.md).

The ongoing project forecasts a **coarse, Sentinel-2-derived visible-water proxy** at pilot grids, not water volume, flood hydraulics, managed Euphrates/Tigris inflow, full native 10m satellite imagery, or ecological field truth. `RESEARCH_ONLY` is required in all claims. A numerical Brier on chronologically split training-area validation is not an independently held-out Dalmaj result. Once final-test feedback has been inspected, repeated tuning makes that geography development data, not a fresh untouched test.

## Implemented and enforced free improvements

| Code / workflow | Verified technical capability | Limit |
|---|---|---|
| [One canonical Kaggle daily notebook](../kaggle/Mash_Plus_Daily_Trainer.ipynb) | Reads private real ESA Sentinel arrays; continues the **same** ConvGRU + optimizer and best checkpoint | GPU quota and daily scheduler best-effort; not a guaranteed completed day |
| [Daily orchestrator](../scripts/mash_plus_daily_bridge.py), [schedule](../.github/workflows/mash-plus-daily-until-nov15.yml) | Four distinct daily slots (05:15 / 09:15 / 13:15 / 17:15 Baghdad), each ~30 minutes measured in actual training loops, strictly sequential, no duplicate slot, stops after Nov 15 | GitHub Actions cron can be delayed |
| [Research training](../ml/daily_train.py), [checkpoint bundle](../ml/daily_bundle.py) | Validation-only best weights AND associated optimizer state persisted; up to 96 epochs/session with 30 measured training-loop-minute target, plateau rollback, SHA-256 checks on exactly 3 training regions | **No** Dalmaj or Hammar image is present in nightly fitting |
| [Transition auxiliary loss](../ml/marshnet_v3.py) | Train-only extra penalty on actually observed wet↔dry change pixels, weighted Brier/BCE, optional exclusion of ambiguous training labels | A new loss cannot magically prove advantage; monitor unweighted full-grid calibration |
| [Change diagnostics](../ml/change_diagnostics.py) | Reports wet gains, drying recall, transition F1, class support, uncertain labels, paired Brier by month and wet/stable condition | Only training-area chronological validation |
| [Month-block evidence](../ml/paired_evidence.py) | Region-stratified contiguous-month bootstrap of paired neural vs persistence Brier, avoids false IID per-pixel confidence | Repeated validation checkpoint selection biases this descriptive interval |
| [NASA POWER context](../ml/nasa_power_context.py) | NASA's free daily rainfall + temperature, complete-month checks, strictly **past-only** monthly summaries; optional separate notebook evidence | Weather data are **not currently neural inputs**; weather correlation cannot substitute for upstream flows |
| [Actual future month inference](../ml/forecast_next_month.py) | Saves probability-map arrays and optional PNGs, dated past-only provenance, source checksums, uncertainty | Future estimates are still unverified, coarse water-proxy cells |
| [Landsat 8/9 check](../ml/landsat_crosscheck.py) | Additional independently acquired optical sensor screening and cloud QA | Landsat-derived water proxy is **not human field truth** |
| [Blinded human review](../ml/prepare_field_review.py), [two-reviewer scoring](../ml/human_reference_evaluation.py) | Requires two actual reviewers, dates, source evidence, agrees/disagrees/uncertain tallies, same-sample Brier/F1 vs smoothed persistence | **No real human annotation has been submitted.** Oversampled classes prevent unweighted area/population-accuracy claims |
| [Automated independent Kaggle audit](../.github/workflows/audit-mash-plus-daily.yml) | Separate read-only daily 23:15 Baghdad check; reports true Kaggle kernel status, session ID, cumulative measured training-loop minutes, epochs, scores in Actions summary/artifact | A green bridge alone does not prove GPU completion |

The architecture has *not* been silently replaced. The active daily ConvGRU remains serializable against the original V4 weights. The experimental upstream [segmentation-models-pytorch](https://github.com/qubvel-org/segmentation_models.pytorch) U-Net remains a separate historic benchmark; it did not win the previous validation. The code also uses PyTorch, NASA POWER, rasterio, pystac-client, ESA Copernicus Sentinel scenes and Planetary Computer; preserve the respective copyright/data terms, dependencies and attribution.

## Verified tests, not mere assertions

- **First real day:** [Kaggle COMPLETE and retrieved 19.4 MB state zip](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40122873091). Day 1, two epochs, training-area validation Brier ~0.02854 and F1 ~0.77918, **not** a final test.
- [Already verified no duplicate GPU run in the same day](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40123033045).
- [Full GitHub scientific CI](https://github.com/ahpa5246-lgtm/MarshPulse/actions/workflows/ci.yml) runs actual CPU PyTorch forward/backward, exact day-1/day-2 optimizer resume and forced stalled-best rollback, train-only label leakage checks, independent-source QA, monthly paired evidence tests, past-only NASA weather parsing, two-reviewer evidence validation, and future-only forecast source checks. Synthetic fixtures in CI do **not** count as scientific accuracy evidence.
- **New model behavior is not empirically validated by code tests alone**. Its first scientific scores will appear when a new real Kaggle daily version completes. A previous day's score cannot be retroactively treated as proof a newly committed loss worked.

## Daily use after ChatGPT access ends

1. [Four-slot daily scheduled GPU training](https://github.com/ahpa5246-lgtm/MarshPulse/actions/workflows/mash-plus-daily-until-nov15.yml) starts automatically with the already configured GitHub Actions `KAGGLE` secret.
2. [Private Kaggle notebook](https://www.kaggle.com/code/minahussain111/mash-plus-daily-trainer) shows actual cells, status and output; open **Output** and look for `Mash_Plus_Daily_State.zip`, `Mash_Plus_next_month_maps/`, and `mash_plus_external_weather_RESEARCH_ONLY.json` (optional).
3. [Daily scientific audit](https://github.com/ahpa5246-lgtm/MarshPulse/actions/workflows/audit-mash-plus-daily.yml) checks Kaggle independently and generates an Actions **Step Summary** and attached `daily-research-audit.json`. If **ERROR** appears, do not restart from zero or delete the previous private state. Inspect source logs and maintain original checkpoint integrity.
4. Target four ~30-minute training-loop sessions per day (120 minutes); if Kaggle GPU quota/availability is exhausted or an earlier run overlaps the next slot, expect less than two hours, not fabricated completed time. On GPU quota exhaustion, expect an incomplete day, not a fake completion. GitHub schedule is conditional/best effort. Date guard rejects GPU dispatch after November 15, 2026.
5. For external reference, take the blinded review queue from the V4 experiment output, have two **real** independent interpreters annotate dates and original imagery, then run:
   ```bash
   python ml/human_reference_evaluation.py \
      --queue blinded_human_reference_queue.csv \
      --review-a reviewer_a.csv --review-b reviewer_b.csv \
      --spatial-manifest satellite_manifest.json \
      --predictions spatial_predictions_FOR_EXTERNAL_AUDIT.npz \
      --out independent_reference_score.json
   ```
   This computes **unweighted sample-only** results and records disagreements; it does not invent missing annotations or determine unbiased wetland area. Sampling-design-aware area accuracy requires an appropriate stratified weighting protocol. See [Olofsson et al. 2014](https://doi.org/10.1016/j.rse.2014.02.015).
6. If a final unseen-date/area test is possible later, predeclare its exact region and period **before** examining data or selecting a checkpoint. Use a **single untouched** final evaluation for comparison to all three simple baselines, with wet-class F1, Brier, observed fractions, temporal variability and the limitations.

## Defensible 30-second presentation

> Mash Plus is an open-source, reproducible research system for forecasting an Iraq wetland *satellite visible-water proxy*. Real Sentinel-2 and Kaggle GPU train a persistence-residual ConvGRU, with chronological validation and held-out geography against simple references. In early experiments our own gates **rejected** neural superiority, so we built a daily checkpoint-continuation pipeline with wet/dry transition diagnostics, monthly uncertainty screening, external-sensor checks, future forecast maps and a blinded human-reference protocol. We will only claim better performance when independent scores show it. It is not yet a field-validated hydraulic or environmental decision system.

No numerical score has been invented, no human field labels have been faked, and no repeated training on the same images should be marketed as repeated independent tests.
