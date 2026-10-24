# Mash Plus V3 — genuine Kaggle GPU run, 2026-10-24

**Scientific verdict:** NOT DEMONSTRATED. This is an actual, completed Kaggle Tesla T4 run, not synthetic training. The neural model **was not selected**: the validation-only champion is `PERSISTENCE_BASELINE`. No independent field truth or deployment validity exists.

**Authentic source evidence**
- [Kaggle V3 notebook and finished version 1](https://www.kaggle.com/code/minahussain111/mash-plus-v3-geo-holdout).
- [GitHub upload accepted by Kaggle](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40113554032).
- [Authenticated Kaggle status COMPLETE, full execution stdout and scientific readout](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40115087285).
- Source commit printed by Kaggle: `9d6b44d366dcbe50eef423d583b96c23e0681ca8`; trained with three seeds 17, 42, 2026.
- Kaggle experiment ZIP: `Mash_Plus_V3_Kaggle_Real_Research.zip` is in the Kaggle notebook outputs. This text is a summary of Kaggle stdout and verification audit, **not** a replacement for the complete source manifests and JSON files.

## Chronological validation, two training regions

| Seed | Neural validation Brier ↓ | Hard persistence Brier ↓ | Neural wet F1 | Best simple baseline wet F1 | Pass |
|---|---:|---:|---:|---:|---|
| 17 | 0.0015084794 | 0.0014514171 | 0.7533632 | 0.7533632 | NO |
| 42 | 0.0015209663 | 0.0014514171 | 0.7533632 | 0.7533632 | NO |
| 2026 | 0.0015090102 | 0.0014514171 | 0.7533632 | 0.7533632 | NO |

**Consequence:** no neural seed beat persistence on validation under the prespecified dual Brier+F1 gate. The actual selected champion was the simple persistence baseline.

## Predeclared Hammar geographic holdout

36 months contain observed same-pixel comparisons; observation overlap 70.35%. **103,737** evaluated pixels with **836** satellite-proxy wet examples (wet prevalence **0.81%**, below the predeclared >=1% screening gate).

| Prediction | Brier ↓ | Wet F1 ↑ |
|---|---:|---:|
| Neural V3 **rejected research challenger** | 0.005359 | 0.6542751 |
| Hard persistence **selected reference** | 0.005379 | 0.6542751 |
| Smoothed persistence | 0.005371 | 0.6542751 |
| Previous-year seasonality | 0.013226 | 0.1020942 |

The neural Brier was marginally lower than the strongest reference (0.005359 vs 0.005371, difference ~0.000012), but **not by the predeclared meaningful improvement threshold** (>=0.0005 and >=2% relative), and **wet F1 was identical** to persistence. The model was *not promoted* by the experiment. These are proxies from the same Sentinel-derived MNDWI/NDVI rule, not independently annotated water truth.

Other research test zones in the same stdout:
- Hawizeh held-out time: 22,109 pixels / 856 wet; V3 Brier .035508 vs smoothed .035516; wet F1 .497800 for both.
- Central held-out time: 21,707 pixels / 106 wet; V3 Brier .006321 vs smoothed .006330; wet F1 .477273 for both.

## Integrity and interpretive limits

- **Completed in Kaggle:** Verified `KernelWorkerStatus.COMPLETE` by authenticated Kaggle CLI. Real Sentinel-2 images acquired for Hawizeh, Central, Hammar; T4 GPU actually used.
- **Observed real limitation:** scarce wet targets and tiny F1 advantage; performance is not better than simple methods on validation.
- **Not proven:** field accuracy, forecasting actual water quantity/flow, ecological connectivity or restoration impact.
- **Engineering fix after this run:** `ml/train_v3.py` was corrected to load exactly the validation-selected neural checkpoint into test evaluation when a neural candidate is promoted. On THIS run no neural model passed promotion, so that distinction does not convert the negative result into a positive one. Subsequent experiments must use a new, pinned Git commit and independently predeclared final test set.

To explain to judges: "We tested a genuine three-area satellite-training pipeline and **our own safeguards rejected the neural candidate** rather than publishing misleading accuracy. The real engineering result is a reproducible satellite-data and scientific evaluation system; reliable neural superiority is a future research milestone."

See [validation protocol](../JUDGE_VALIDATION.md). Never remove or conceal negative results.
