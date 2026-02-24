from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd

def plot_sir(sim: pd.DataFrame, title: str, out_path: str) -> None:
    plt.figure()
    plt.plot(sim["t"], sim["S"], label="S")
    plt.plot(sim["t"], sim["I"], label="I")
    plt.plot(sim["t"], sim["R"], label="R")
    plt.xlabel("Temps (jours)")
    plt.ylabel("Population")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
