import pandas as pd
import numpy as np
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_epidemie(path=None):

    if path is None:
        path = DATA_DIR / "epidemie.csv"

    df = pd.read_csv(path)

    # renommer les colonnes owid
    rename = {"Entity": "country", "Code": "code", "Day": "date"}
    for col in df.columns:
        if "death" in col.lower() and "cumulative" in col.lower():
            rename[col] = "cum_deaths"
        if "cases" in col.lower() and "cumulative" in col.lower():
            rename[col] = "cum_cases"
    df = df.rename(columns=rename)

    df["date"]       = pd.to_datetime(df["date"], errors="coerce")
    df["cum_cases"]  = pd.to_numeric(df["cum_cases"],  errors="coerce").fillna(0)
    df["cum_deaths"] = pd.to_numeric(df["cum_deaths"], errors="coerce").fillna(0)
    df["country"]    = df["country"].astype(str).str.strip()

    # virer les lignes sans code iso (agregats "World", "Africa", etc.)
    df = df[ df["code"].notna() & (df["code"].astype(str).str.strip() != "") ]
    df = df.dropna(subset=["date"])

    return df.sort_values(["country", "date"]).reset_index(drop=True)


def load_population(path=None, codes_valides=None):
    """
    codes_valides : set de codes ISO3 venant de epidemie.csv
                    si fourni, ca vire automatiquement les agregats regionaux
                    de la banque mondiale (WLD, EUU, etc.) qui sinon font
                    gonfler la population mondiale
    """

    if path is None:
        path = DATA_DIR / "population.csv"

    df = pd.read_csv(path)

    rename = {}
    for col in df.columns:
        c = col.lower().strip()
        if c == "country name":   rename[col] = "country"
        if c == "country code":   rename[col] = "code"
        if c == "year":           rename[col] = "year"
        if c == "value":          rename[col] = "population"
    df = df.rename(columns=rename)

    df["country"]    = df["country"].astype(str).str.strip()
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df = df.dropna(subset=["population"])
    df = df[ df["population"] > 0 ]

    # filtrer sur les codes connus de epidemie.csv
    # ca vire les agregats regionaux banque mondiale (Arab World, EUU, WLD...)
    if codes_valides is not None and "code" in df.columns:
        df = df[ df["code"].isin(codes_valides) ]

    # garder juste la pop la plus recente par pays
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df = df.sort_values("year").groupby("country").last().reset_index()

    return df[["country", "population"]]


def merge_epi_pop(df_epi, df_pop):

    data = df_epi.merge(df_pop, on="country", how="left")
    data = data.dropna(subset=["population"])

    return data.reset_index(drop=True)


def compute_sir(data, gamma=0.1):

    frames = []

    for country, grp in data.groupby("country"):

        grp = grp.sort_values("date").copy()
        N   = float(grp["population"].iloc[0])

        cum_cases  = grp["cum_cases"].values.astype(float)
        cum_deaths = grp["cum_deaths"].values.astype(float)
        new_cases  = np.maximum(0, np.diff(cum_cases, prepend=cum_cases[0]))

        I = np.zeros(len(grp))
        R = np.zeros(len(grp))

        for k in range(len(grp)):
            if k == 0:
                I[0] = cum_cases[0]
                R[0] = cum_deaths[0]
            else:
                recovered = gamma * I[k-1]
                I[k] = max(0, I[k-1] + new_cases[k] - recovered)
                R[k] = min(R[k-1] + recovered + (cum_deaths[k] - cum_deaths[k-1]),
                           N - I[k])

        grp["I"] = I
        grp["R"] = R
        grp["S"] = np.maximum(0, N - I - R)
        frames.append(grp)

    return pd.concat(frames).reset_index(drop=True)