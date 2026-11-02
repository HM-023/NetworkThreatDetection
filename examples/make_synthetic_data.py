"""Create artificial, non-sensitive test records. NOT a performance benchmark."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def make_sample(rows=150, seed=15):
    rng = np.random.default_rng(seed)
    classes = np.array(["normal", "suspicious", "anomalous"])
    y = classes[np.arange(rows) % len(classes)]
    rng.shuffle(y)
    effects = pd.Series(y).map({"normal": 0, "suspicious": 0.7, "anomalous": 1.3}).to_numpy()
    return pd.DataFrame({
        "Flow ID": [f"demo-{i:05d}" for i in range(rows)],
        "Src IP": ["192.0.2.10"] * rows,
        "Dst IP": ["198.51.100.20"] * rows,
        "Flow Duration": (rng.exponential(5, rows) + effects).round(4),
        "Packets": rng.poisson(10 + effects * 2, rows),
        "Bytes": rng.poisson(1000 + effects * 180, rows),
        "Destination Port": rng.choice([80, 443, 8080], rows),
        "Label": y,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="demo_flows.csv")
    ap.add_argument("--rows", type=int, default=150)
    args = ap.parse_args()
    if args.rows < 30:
        raise ValueError("Use at least 30 synthetic rows")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    make_sample(args.rows).to_csv(output, index=False)
    print(f"Created synthetic example: {output}")


if __name__ == "__main__":
    main()
