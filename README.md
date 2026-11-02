# Network Threat Detection

Reproducible Python workflow for classifying **labeled network-flow records**. The project explores security analytics and the challenges of evaluating imbalanced network datasets.

## What is included

- A complete CLI to load a CSV, remove common identifiers, clean non-finite values, split before fitting transformations, and train a model.
- Two configurable classifiers: Random Forest and multinomial-capable Logistic Regression.
- Stratified train/test holdout, per-class precision/recall/F1, macro and weighted averages, and a confusion matrix.
- A separate, **synthetic** test dataset generator and automated regression tests.

> **No real dataset or pretrained model is distributed.** The original research dataset's redistribution rights are not established. Provide your own appropriately licensed CSV with a `Label` column. Results vary with data quality and sampling; this is not a production intrusion detection system.

## Quick start

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python examples/make_synthetic_data.py --output results/demo_flows.csv
python -m src.train --input results/demo_flows.csv --model random-forest --output results/evaluation
python -m unittest discover -s tests -v
```

The synthetic dataset is generated from artificial statistical distributions and **must not** be used as a real-world accuracy benchmark.

## Using a real dataset

```bash
python -m src.train --input path/to/licensed_flows.csv --label Label --model logistic-regression --output results/evaluation
```

The report includes `metrics.json`, `classification_report.txt`, `confusion_matrix.csv`, and `run_metadata.json` in the local output directory. It avoids storing raw network records in these outputs.

## Method and limits

The holdout split is performed *before* any imputation or scaling. All preprocessing is fitted on the training portion only through `sklearn.pipeline.Pipeline`, avoiding a leakage pattern in earlier experiments. Identifiers (flow IDs, IP addresses, timestamps) are dropped by default; numeric network-flow characteristics remain.

This is a random stratified split. Traffic from the same host, capture, or time period may remain correlated between train and test. For deployment-oriented claims, use an independent capture, temporal/group-aware split, drift checks, calibration, and operational false-positive analysis. The program does not sniff packets or monitor a network live.

## Repository layout

- `src/train.py` — ingestion, preprocessing, training, evaluation CLI
- `examples/make_synthetic_data.py` — synthetic, non-sensitive testing input
- `tests/test_training.py` — leakage and output tests
- `docs/evaluation.md` — validation guidance and reproducibility limits

## Project maturity

**Validated code demo**, not a production sensor. Previous historical notebook scores have intentionally not been copied because they require reevaluation using corrected preprocessing and independently verified data provenance.

## Acknowledgments and reuse

Developed from an earlier collaborative investigation of network security data. Specific contribution and reuse rights for historical artifacts should be verified before any original notebooks, datasets, or diagrams are added. This refreshed code is a clean implementation of the methodological approach.
