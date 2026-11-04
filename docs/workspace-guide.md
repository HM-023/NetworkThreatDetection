# Network Threat Detection: workspace guide

## Start and stop

Use `python -m webapp.app` from the repository root and open the printed loopback address. Python 3.11 or later is the supported baseline. Use the virtual environment activation command for your operating system. The default port is 8101; `--port` changes it. `Ctrl+C` shuts down the server.

## Main workflow

1. Inspect the built-in synthetic example, or choose **My licensed CSV file** and select a file. The app accepts up to 3 MiB, 20,000 rows, 100 columns and 30 classes. The default label column is `Label`; change it if needed. Duplicate CSV headers are rejected.
2. Choose Random Forest or Logistic Regression. Random Forest uses one CPU worker in the studio. Neither model is pretrained.
3. Choose a holdout strategy. Random stratified splits preserve class proportions approximately. Group holdouts keep identifiers in the selected group column disjoint; the group column is removed from features. Temporal holdouts use strictly earlier unique timestamps for training and later timestamps for testing; the timestamp column is removed from features. A group/time split is rejected if training lacks a held-out class.
4. Train, then review per-class metrics and the confusion matrix. Imputation and optional scaling are fitted only on training rows. Every experiment records a data fingerprint, protocol fingerprint, seed and split details.
5. Compare classifiers in history only when comparison keys match. A matching key means the same data and split settings, not that the data is unbiased or representative. Synthetic results are execution checks only.
6. Open **Model predictions**, choose a saved experiment and select a feature CSV. All trained feature columns must exist and be numeric. Prediction accepts up to 1,000 rows. Results include uncalibrated class probabilities.
7. Export evaluation or prediction JSON. Raw input CSV rows are not saved. Locally generated model artifacts are stored under the selected data directory; never replace them with files from an untrusted source. The app has no model-upload endpoint.

## Local data and backups

Records live in `data/workspace.sqlite3` by default. ML model artifacts additionally live in `data/models/`. These paths are excluded from git. The file formats contain local workspace information and are not encrypted by the application. Stop the server before copying the entire data directory for a simple backup, then use `--data-dir` to reopen that copy. Deleting the data directory while the server is stopped resets the workspace. Exported files are saved wherever the browser downloads them; this app does not automatically publish them.

## Local browser boundary

Use the exact printed localhost/127.0.0.1 URL and reload after restarting the server. A new random session token is issued each time. There is no remote bind option. Host checks resist DNS rebinding, and API requests require the page's token. This is a browser-request boundary, not account authentication and not a defense against other software already running as the same operating-system user.

## Browser verification

GitHub Actions runs the end-to-end journey in `tests/browser.cjs` using pinned Playwright 1.56.1. It exercises real forms and local API actions, checks browser errors and mobile viewport fit, reloads persisted state and captures desktop/mobile PNGs. Screenshots use only synthetic or fictional inputs.
