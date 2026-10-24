# Mash Plus — free improvements that actually test wetland-change forecasting
**Updated 2026-10-24 · Research-only**

## What has been implemented
The [daily training script](../ml/daily_train.py) continues the same ConvGRU + AdamW checkpoint from private Kaggle data. As of this change, after each daily training stage it **runs the best chronological-validation checkpoint** against monthly **wet gain**, **drying**, and **unchanged** pixels in Hawizeh, Central Marshes, and Sinnaf only, using the original unresampled satellite scenes. The code lives in [change_diagnostics.py](../ml/change_diagnostics.py); synthetic correctness tests live in [test_change_diagnostics.py](../tests/test_change_diagnostics.py).

The next completed Kaggle daily training report (same [one Kaggle notebook](../kaggle/Mash_Plus_Daily_Trainer.ipynb)) automatically adds `validation_change_diagnostics`, containing:
- `wet_gain_recall`, `drying_recall`, `transition_f1` and correctly observed change prevalence. The zero-change persistence prediction has zero event recall when changes exist.
- Correct comparisons against **smoothed previous-month persistence** on the exact same natural **shared observed pixels**, plus event-only, stable-only, and confident-label-only Brier.
- Separate monthly counts and regional breakdowns to avoid treating all neighboring pixels as independent evidence.
- `uncertain_target_pixels` near MNDWI 0.1 or NDVI 0.3 thresholds. These uncertainty masks are **evaluation diagnostics**, not manually validated ground truth.
- This diagnostic has **no influence on checkpoint selection** or the final-test geography. It is descriptive rather than another free chance to tune the model on a once-independent final test.

**No evidence of improvement is claimed from implementing diagnostics.** A new authenticated complete daily Kaggle version must be compared to the exact same validation support and baseline before improvement is asserted. Checkpoint selection still uses validation Brier and wet F1; no change to the checkpoint's architecture or optimizer-state schema.

## Highest-value free research upgrades, NOT YET TRAINED/PROVEN
1. **Reliable labels:** Seek two genuinely independent specialists to annotate clear, georeferenced wet/dry or uncertain cases, prioritizing wet boundaries, rapidly changing areas and changes over time. The existing [blind reference queue](../ml/prepare_field_review.py) intentionally leaves human labels empty. Landsat alone is an independent SENSOR but is still a derived optical-index label, not field truth.
2. **Hydrometeorological forcing:** NASA [GPM IMERG](https://gpm.nasa.gov/data/imerg) makes precipitation estimates available, and Copernicus [ERA5-Land](https://climate.copernicus.eu/climate-reanalysis) provides historical rainfall, temperature and land state. A future **separate** predictor could use past-only rainfall, upstream levels and seasonality; adding inputs to the currently running ConvGRU would change its architecture and requires a separate new training/evaluation protocol, not loading incompatible optimizer state. For Iraqi wetlands, rainfall alone will not explain managed upstream river flow.
3. **Historical water prior:** [JRC Global Surface Water](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater) provides a satellite-derived historical surface water occurrence reference covering **1984–2021**. It can guide an externally documented historical review or pre-2022 priors; it must never be mislabeled as independent 2022–2026 water truth.
4. **Fair new holdout:** The past Hammar and Dalmaj site results have been inspected. Any post-optimization headline score must come from an **additional unseen site or newly accrued untouched dates** with predeclared scoring and no feedback-to-training leakage.
5. **Avoid unbounded GPU spend:** Keep the best validation checkpoint, not merely the most recent epoch. Pause for data-quality investigation when gains plateau. Scheduled Kaggle executions depend on available free quota and GitHub Actions scheduling, not the chat session running indefinitely.

## What can be claimed to judges
**Yes:** reproducible real Sentinel-2 acquisition, Kaggle GPU training, saved checkpoint, chronological validation, measured water-change diagnostics, and explicit model-to-persistence comparisons.

**No:** certified water-volume prediction, 10m spatial precision when the experiment uses approximately 10km/64 grid cells, field verification, or superior machine learning without a passing predeclared independent test.

These additions aim to make model failures obvious and prioritize genuinely informative new data. They do not silently declare improvement because a more sophisticated metric exists.
