# MarshPulse — from an interactive prototype to evidence-grade wetland monitoring

Status: **research / NOT operationally validated**. Last revised 2026-10-24.

## What works today

The project already has a working browser-based water-connectivity simulation, forecast experiments, an actual PyTorch image+time ConvGRU model, an automatic real ESA Sentinel-2 monthly acquisition workflow, and quality-tested reporting. The web demo's default grid and hypothetical rescue actions remain **synthetic** and should not be interpreted as Iraqi water management forecasts.

New reproducible tools:

- `ml/collect_sentinel.py`: collect genuine multispectral Sentinel-2 Level-2A imagery through Microsoft Planetary Computer, preserve SCL cloud/quality mask and scene provenance. A roughly 10 km pilot box near the [Hawizeh KBA center](https://www.keybiodiversityareas.org/en/site/factsheet/8056) is used for research, **not an official Ramsar polygon**.
- `ml/quality_gate.py`: inspect visible-water **proxy** prevalence and clear pixel coverage, compare next-month MarshNet, previous-month persistence, and same-month-prior-year seasonality **on identical valid pixels**. Missing/cloudy observations are not relabeled as dry land. Wet-class F1 is undefined, not 1, when the test set contains no wet pixels.
- `ml/monitor_wetland.py`: monthly `water_monitor.csv` and JSON record observed-water-proxy area and area-change **only over the overlapping clear pixels**; count image pixel clusters, explicitly not hydraulic connectivity. No expansion from observable area to total water volume or whole-wetland area.
- `ml/train_satellite.py`: train-only positive-class weighting (cap 8), chronological splits, checkpoints, independent-pixel baselines and transparent failure/readiness flags. The latest archived run's outputs are accessible in GitHub Actions artifacts.
- `.github/workflows/real-satellite-pilot.yml`: manual or monthly (day 10 at 04:17 UTC) research run on the last 36 complete calendar months. It does not self-train from its own predictions. Image availability, GitHub Action scheduling, runner resources and API availability are **not guaranteed**; missing imagery causes failure instead of synthetic substitution.

## Non-negotiable scientific rules

1. Images **are real**, labels derived from MNDWI/NDVI are **not field-verified truth**. Do not equate open water with reed-covered floodwater, marsh extent, soil moisture or water quality.
2. Never cite website unit/UI tests as model prediction accuracy. Compare water-specific recall/precision/F1, balanced accuracy and Brier score, not accuracy alone. A majority-dry prediction may have near-perfect accuracy while totally missing water.
3. Disclose spatial and temporal data leakage, observation mask coverage, class imbalance, missing months, thresholds and uncertainty. Train-only normalization and chronological holdout are mandatory.
4. Models cannot be used for civil engineering allocation, ecological restoration decisions, public alerts or safety decisions without independent water reference labels, a geographic holdout and improvements over persistence and seasonal baselines.
5. The historical 2024–2025 pilot **failed**: MarshNet Brier 0.107144 versus persistence 0.000700 and wet F1 0. See [original measured negative result](../research/experiments/hawizeh-v2-real-s2-2024-2025.json). New experiments do not retroactively change this result.

## Validation milestones — incomplete until proven

- **A. Wet-label QA**: obtain wet and dry examples throughout the annual cycle; audit threshold sensitivity, clouds, valid-pixel overlap, monthly scene coverage, predicted class collapse. Existing automation now outputs diagnostics, not fabricated scores.
- **B. Spatial transfer**: train on a documented geographic extent and evaluate at one or more **entirely held-out** wetland locations (Central Marsh, Hammar etc.) with differing ecological regimes. Do not choose regions on test score.
- **C. Independent reference**: manually interpret/label co-registered multispectral/high-resolution imagery or obtain field surveys. Keep labels and annotator disagreement separate from thresholds used to generate model proxies. Use independent wetland boundaries.
- **D. Honest baselines**: compare matched-pixel persistence, 12-month seasonality and a simple supervised model before increasing ConvGRU parameters. Select hyperparameters on validation period only, report final test once.
- **E. Uncertainty and deployment**: calibrate predicted probabilities, publish performance by month, coverage and location, estimate change intervals, log drift and abstain on low-quality observations.
- **F. Real management integration**: any claim about saved water or improved ecological conditions requires hydrological measurements, stakeholder involvement and observed real interventions. Current pixel-connectivity simulations do not model discharge or flow.

A proposed **research target** (not achieved) is repeatable positive Brier skill versus *both* baselines plus adequate precision and recall for wet pixels across independent seasons and places. No automatic workflow may label a model "trusted" merely because more epochs finish.

## Reproduce

```sh
python ml/collect_sentinel.py --bbox 47.64 31.53 47.74 31.63 --start 2023-01 --end 2025-12 --pixels 64 --max-scenes 2 --out ./sentinel
python ml/quality_gate.py --input ./sentinel/hawizeh_s2_monthly.npz --out ./out/quality_audit.json
python ml/monitor_wetland.py --input ./sentinel/hawizeh_s2_monthly.npz --manifest ./sentinel/satellite_manifest.json --out ./out
python ml/train_satellite.py --input ./sentinel/hawizeh_s2_monthly.npz --out ./out --base 16 --lookback 4 --epochs 12 --cpu
```

Python dependencies: numpy, PyTorch, rasterio, pystac-client and planetary-computer. Network access is needed for real satellite imagery. A CPU run is supported. Results written to `./out` include an auditable JSON experiment report, CSV monthly monitoring and a saved model. The official pipeline rolls its 36-month window through the last fully completed month. Any test using `--synthetic-smoke` must be labeled synthetic.

## Research sources

- [ESA Sentinel-2 Level-2A scene-classification classes](https://sentinels.copernicus.eu/documents/d/sentinel/s2-pdgs-cs-di-psd-v15-0)
- [Hawizeh Key Biodiversity Area](https://www.keybiodiversityareas.org/en/site/factsheet/8056)
- [JRC Global Surface Water monthly dataset](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_MonthlyHistory) — independent historical contextual source, not yet incorporated as a verified field-label training source
- [A 2024 hand-labeled surface-water validation dataset and its limitations](https://doi.org/10.5194/essd-16-4311-2024)

The platform is a research **prototype**. The next defensible steps are better labels and validation, not unconstrained, indefinite model training.
