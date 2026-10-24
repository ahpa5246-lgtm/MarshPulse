# Independent MarshPulse evidence audit — 2026-10-24

Source: [genuine 60-month Sentinel training run](https://github.com/ahpa5246-lgtm/MarshPulse/actions/runs/40036570036), artifact `hawizeh-monthly-research-unverified` (12536919906). Verification was run independently on the downloaded raw NPZ, manifest, predictions and monthly monitoring JSON.

**Technical archive replay: PASS. Environmental forecasting readiness: NOT VALIDATED.**

## Recomputed from saved binary arrays, not copied from UI

| Metric | Calibrated MarshNet | Previous-month persistence | Previous-year seasonal |
| --- | ---: | ---: | ---: |
| Brier score ↓ | 0.027392514 | **0.018780557** | 0.132474615 |
| Wet F1 ↑ | 0.408206 | **0.497800** | 0.105113 |
| TP / FP / FN | 587 / 1433 / 269 | 396 / 339 / 460 | 331 / 5111 / 525 |

60 image months (Oct 2021–Sep 2026), 120 scene identifiers, 60×7×64×64 array, dataset SHA-256 `d9ac8f487460058b29cf5bb790b047280ea9c524e33eac52be694a7fe774cc45`, and 42,544 shared observed holdout pixels including 856 proxy-wet pixels. Chronological split: 36 training target months, 8 validation, 12 test. All saved confusion matrices, Brier scores, dates, wet labels and cloud masks independently matched their original input data.

The validation-only probability calibration reduced holdout Brier from 0.082071421 to 0.027392514, without beating persistence. It **did not** establish environmental validity.

## Fault-injection verification

Our independent replay verifier correctly rejected four deliberate manipulations:

- Data archive bytes changed → SHA mismatch.
- Observed/cloud-pixel mask changed → mismatch with source image.
- Saved Brier changed to 0.0001 → mismatch with recomputed predictions.
- Monthly reported water area increased by 50 km² → mismatch with spectral wet classification and pixel area.

Implementation: [ml/verify_experiment.py](../ml/verify_experiment.py). The **real satellite workflow now fails if this verifier rejects an experiment**, and publishes `independent-verification.json` alongside the model and provenance.

## Explicit unsolved acceptance criteria

- **Unmet:** MarshNet beats previous-month persistence on Brier and wet F1.
- **Unmet:** independent field-verified water labels, AOI/Ramsar boundary, geographically disjoint evaluation, ground-truth accuracy or hydrological flow modeling.
- **Unverified externally:** live GitHub Pages URL. Passing Chrome tests serve the repository locally, not the public URL.
- **Not claimed:** water saved, restored marsh area, physical channel connectivity, deployable drought forecasting, or that this model functions as a ChatGPT-equivalent trustworthy environmental system.

Browser/engineering tests can establish application behavior and data consistency but cannot prove scientific accuracy. The raw observations are Sentinel-derived **proxies** susceptible to threshold and cloud uncertainty.

See also [scientific readiness roadmap](scientific-readiness-roadmap.md).
