"""Train a leakage-aware baseline classifier from labeled network flow CSV data."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

IDENTIFIER_COLUMNS = {"Flow ID", "Src IP", "Dst IP", "Timestamp"}


def prepare_xy(frame: pd.DataFrame, label: str = "Label"):
    if label not in frame.columns:
        raise ValueError(f"Target column {label!r} was not found")
    if len(frame) < 10:
        raise ValueError("At least 10 rows are required for a meaningful demo")
    y = frame[label].astype("string").str.strip()
    valid = y.notna() & y.ne("")
    frame, y = frame.loc[valid].copy(), y.loc[valid].astype(str)
    excluded = IDENTIFIER_COLUMNS | {label}
    features = frame.drop(columns=list(excluded & set(frame.columns)))
    # Baseline intentionally uses numeric flow statistics; do not silently encode IDs.
    numeric = features.select_dtypes(include=[np.number, "bool"]).copy()
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    numeric = numeric.loc[:, numeric.notna().any(axis=0)]
    if numeric.empty:
        raise ValueError("No usable numeric feature columns remain after cleaning")
    counts = y.value_counts()
    if len(counts) < 2 or counts.min() < 2:
        raise ValueError("Need at least 2 classes and 2 records per class for stratification")
    return numeric, y


def make_pipeline(feature_names, model="random-forest", seed=42):
    numeric_steps = [("impute", SimpleImputer(strategy="median"))]
    if model == "logistic-regression":
        numeric_steps.append(("scale", StandardScaler()))
        estimator = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    elif model == "random-forest":
        estimator = RandomForestClassifier(n_estimators=100, min_samples_leaf=2,
                                           class_weight="balanced_subsample", random_state=seed, n_jobs=-1)
    else:
        raise ValueError(f"Unsupported model: {model}")
    preprocessor = ColumnTransformer([("numeric", Pipeline(numeric_steps), list(feature_names))],
                                     remainder="drop")
    return Pipeline([("preprocess", preprocessor), ("classifier", estimator)])


def evaluate_csv(input_path, output_dir, label="Label", model="random-forest", seed=42, test_size=0.25):
    if not 0.1 <= test_size <= 0.5:
        raise ValueError("test_size must be between 0.1 and 0.5")
    frame = pd.read_csv(input_path, low_memory=False)
    X, y = prepare_xy(frame, label)
    n_classes = y.nunique()
    test_rows = math.ceil(len(y) * test_size)
    if test_rows < n_classes or len(y) - test_rows < n_classes:
        raise ValueError("Not enough rows per split to cover all classes; adjust test size")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, stratify=y, test_size=test_size, random_state=seed)
    pipeline = make_pipeline(X_train.columns, model=model, seed=seed)
    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)
    labels = sorted(y.unique().tolist())
    report = classification_report(y_test, predictions, labels=labels, output_dict=True,
                                   zero_division=0)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_dir / "classification_report.txt").write_text(
        classification_report(y_test, predictions, labels=labels, zero_division=0), encoding="utf-8")
    matrix = confusion_matrix(y_test, predictions, labels=labels)
    pd.DataFrame(matrix, index=labels, columns=labels).to_csv(output_dir / "confusion_matrix.csv")
    metadata = {"model": model, "seed": seed, "test_size": test_size,
                "rows": len(y), "train_rows": len(X_train), "test_rows": len(X_test),
                "feature_count": len(X.columns), "classes": labels,
                "split": "random-stratified", "preprocessing_fitted_on": "training-only",
                "note": "Not an independent-capture or real-world generalization estimate"}
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to an appropriately licensed flow CSV")
    parser.add_argument("--output", default="results")
    parser.add_argument("--label", default="Label")
    parser.add_argument("--model", choices=["random-forest", "logistic-regression"], default="random-forest")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.25)
    args = parser.parse_args()
    result = evaluate_csv(args.input, args.output, args.label, args.model, args.seed, args.test_size)
    print(f"Finished. Macro F1: {result['macro avg']['f1-score']:.3f}; results in {args.output}")


if __name__ == "__main__":
    main()
