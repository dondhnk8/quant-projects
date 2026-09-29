from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FILES = {"2324": "pldata2324.csv", "2425": "pldata2425.csv", "2526": "pldata2526.csv"}
USECOLS = ["Date", "HomeTeam", "AwayTeam", "FTR", "PSCH", "PSCD", "PSCA"]
BINS = np.linspace(0, 1, 11)

def load_matches():
    frames = [
        pd.read_csv(DATA_DIR / fname, usecols=USECOLS).assign(Season=season)
        for season, fname in FILES.items()
    ]
    df = pd.concat(frames, ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    return df.dropna().reset_index(drop=True)

def add_fair_probs(df):
    """Remove the bookmaker margin: 1/odds, then divide by each row's total"""
    raw = 1 / df[["PSCH", "PSCD", "PSCA"]]
    fair = raw.div(raw.sum(axis=1), axis=0)
    df = df.copy()
    df[["p_home", "p_draw", "p_away"]] = fair.to_numpy()
    return df

def to_long(df):
    """One row per outcome: its claimed probability and whether it happened"""
    outcomes = {"H": "p_home", "D": "p_draw", "A": "p_away"}
    parts = [
        pd.DataFrame({"prob": df[col], "happened": (df["FTR"] == result).astype(int)})
        for result, col in outcomes.items()
    ]
    return pd.concat(parts, ignore_index=True)

def calibration_table(long, bins=BINS):
    """Works on any table with columns 'prob' and 'happened' """
    long = long.assign(bin=pd.cut(long["prob"], bins, include_lowest=True))
    table = long.groupby("bin", observed=True).agg(
        n=("happened", "size"),
        avg_prob=("prob", "mean"),
        actual=("happened", "mean"),
    )
    table["gap"] = table["avg_prob"] - table["actual"]
    table["noise"] = np.sqrt(table["avg_prob"]*(1-table["avg_prob"])/table["n"])
    return table

def plot_calibration(table, label, path):
    err = 2 * table["noise"]
    yerr = [np.minimum(err, table["actual"]), np.minimum(err, 1 - table["actual"])]

    plt.figure(figsize=(6,6))
    plt.plot([0,1], [0,1], linestyle="--", color="gray", label="perfect calibration")
    plt.errorbar(table["avg_prob"], table["actual"], yerr=yerr, fmt="o-", capsize=3, label=f"{label} (±2 std. errors)")
    plt.xlim(0,1)
    plt.ylim(0,1)
    plt.xticks(np.arange(0, 1.1, 0.1))
    plt.yticks(np.arange(0, 1.1, 0.1))
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.xlabel("Claimed probability")
    plt.ylabel("Actual frequency")
    plt.title(f"Calibration of {label}")
    plt.legend()
    plt.savefig(path, dpi=150)
    plt.show()

if __name__ == "__main__":
    df = add_fair_probs(load_matches())
    assert np.allclose(df[["p_home", "p_draw", "p_away"]].sum(axis=1), 1)

    table = calibration_table(to_long(df))
    print(len(df), "matches")
    print(table.round(3))
    (BASE_DIR / "results").mkdir(exist_ok=True)
    plot_calibration(table, "Pinnacle closing odds", BASE_DIR / "results" / "calibration.png")
