from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd


def plot_sir(sim: pd.DataFrame, title: str, out_path: str, N: float | None = None) -> None:
    """
    Si N est fourni, on trace en % de la population (beaucoup plus lisible).
    """
    plt.figure()

    if N is not None and N > 0:
        S = sim["S"] / N * 100.0
        I = sim["I"] / N * 100.0
        R = sim["R"] / N * 100.0
        ylabel = "% de la population"
    else:
        S, I, R = sim["S"], sim["I"], sim["R"]
        ylabel = "Population"

    plt.plot(sim["t"], S, label="S")
    plt.plot(sim["t"], I, label="I")
    plt.plot(sim["t"], R, label="R")
    plt.xlabel("Temps (jours)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
