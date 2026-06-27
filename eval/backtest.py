"""Backtest the delay model on the Jan-2020 holdout (a one-year generalization test).

Trains on Jan 2019 (via data/model.pkl) and scores Jan 2020, reporting AUC,
Brier score, calibration, and lift over the base rate. This is the project's
eval moat: real predictions validated against real outcomes a year forward.

Run:  python eval/backtest.py   (requires data/model.pkl — run train_model.py first)
"""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve

DATA = Path(__file__).parent.parent / "data"
HOLDOUT = DATA / "Jan_2020_ontime.csv"
FEATURES = ["OP_UNIQUE_CARRIER", "ORIGIN", "DEST", "DAY_OF_WEEK", "DEP_TIME_BLK"]
TARGET = "ARR_DEL15"


def main() -> None:
    model = joblib.load(DATA / "model.pkl")

    df = pd.read_csv(HOLDOUT, usecols=FEATURES + [TARGET])
    df["DAY_OF_WEEK"] = df["DAY_OF_WEEK"].astype("Int64").astype(str)
    df = df.dropna(subset=[TARGET])
    X, y = df[FEATURES], df[TARGET].astype(int)

    p = model.predict_proba(X)[:, 1]
    base = float(y.mean())

    auc = roc_auc_score(y, p)
    brier = brier_score_loss(y, p)
    brier_base = brier_score_loss(y, np.full_like(p, base))  # always predict base rate

    print("=" * 56)
    print(f"BACKTEST  train=Jan2019  holdout=Jan2020  n={len(y):,}")
    print("=" * 56)
    print(f"  ROC-AUC          {auc:.4f}   (0.5 = no skill)")
    print(f"  Brier score      {brier:.4f}   vs base-rate {brier_base:.4f}")
    print(f"  base delay rate  {base:.3f}")
    print(f"  Brier skill      {(1 - brier / brier_base) * 100:.1f}% better than base rate")
    print("\n  Calibration (predicted -> actual delay rate):")
    frac_pos, mean_pred = calibration_curve(y, p, n_bins=10, strategy="quantile")
    for mp, fp in zip(mean_pred, frac_pos):
        bar = "#" * int(fp * 40)
        print(f"    pred {mp:5.2f} -> actual {fp:5.2f}  {bar}")


if __name__ == "__main__":
    main()
