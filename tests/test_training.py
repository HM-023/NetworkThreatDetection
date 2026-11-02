import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from src.train import prepare_xy, make_pipeline, evaluate_csv
from examples.make_synthetic_data import make_sample


class TestClassifierWorkflow(unittest.TestCase):
    def test_identifiers_removed_and_nonfinite_cleaned(self):
        frame = make_sample(90)
        frame["Bytes"] = frame["Bytes"].astype(float)
        frame.loc[1, "Bytes"] = np.inf
        X, y = prepare_xy(frame)
        self.assertNotIn("Flow ID", X.columns)
        self.assertNotIn("Src IP", X.columns)
        self.assertFalse(np.isinf(X.to_numpy(dtype=float)).any())
        self.assertEqual(len(y), 90)

    def test_scaler_is_inside_pipeline(self):
        features = ["Packets", "Bytes"]
        p = make_pipeline(features, model="logistic-regression")
        self.assertIn("preprocess", p.named_steps)
        preprocess = p.named_steps["preprocess"]
        self.assertIn("scale", preprocess.transformers[0][1].named_steps)

    def test_end_to_end_reports(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "demo.csv"
            make_sample(90).to_csv(file, index=False)
            report = evaluate_csv(file, Path(d) / "output", model="logistic-regression")
            self.assertIn("macro avg", report)
            self.assertTrue((Path(d) / "output" / "confusion_matrix.csv").exists())

    def test_small_valid_fractional_split(self):
        # Ten records and test_size=0.25 yield three test rows, not round(2.5).
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "small.csv"
            pd.DataFrame({"Packets": range(10), "Label": ["a"] * 4 + ["b"] * 3 + ["c"] * 3}).to_csv(file, index=False)
            report = evaluate_csv(file, Path(d) / "output", model="logistic-regression")
            self.assertEqual(report["macro avg"]["support"], 3)

    def test_rejects_no_numeric_data(self):
        f = pd.DataFrame({"Label": ["a", "b"] * 10, "Flow ID": [str(i) for i in range(20)]})
        with self.assertRaises(ValueError):
            prepare_xy(f)


if __name__ == "__main__":
    unittest.main()
