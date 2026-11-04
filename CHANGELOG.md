# Changelog

## 1.0.0 — Local workspace release (2026-11-04)

- Dataset inspection: CSV class balance, missing numeric values and feature summaries.
- Real experiment training: Random Forest and Logistic Regression with train-only fitted preprocessing.
- Split control: Random stratified, group-disjoint and chronological holdouts.
- Evaluation: Per-class metrics, confusion matrices and protocol fingerprints for comparing like-for-like runs.
- Saved-model prediction: Predict from workspace-generated model artifacts; arbitrary model uploads are rejected.
- Persistent history: SQLite experiment metadata, local model artifacts and JSON report exports.
- Added a responsive local dashboard, request-boundary validation, ignored local state, regression tests and browser workflow verification.
- Preserved the prior case-study material and its contribution/reuse limitations.

Remaining scope: The original Python training CLI remains available. The studio adds a local user interface and persisted experiments; it does not capture packets or monitor a network. Real-traffic quality depends on licensed data, labels and an appropriate independent evaluation.
