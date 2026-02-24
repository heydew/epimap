from __future__ import annotations
import pandas as pd

REQUIRED_EPI = {"date", "country", "cases", "recovered", "deaths"}
REQUIRED_POP = {"country", "population"}

def load_epidemie(path: str = "data/epidemie.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_EPI - set(df.columns)
    if missing:
        raise ValueError(f"epidemie.csv: colonnes manquantes: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise ValueError("epidemie.csv: certaines dates sont invalides")

    df["country"] = df["country"].astype(str).str.strip()
    for c in ["cases", "recovered", "deaths"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    return df.sort_values(["country", "date"]).reset_index(drop=True)

def load_population(path: str = "data/population.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_POP - set(df.columns)
    if missing:
        raise ValueError(f"population.csv: colonnes manquantes: {sorted(missing)}")

    df["country"] = df["country"].astype(str).str.strip()
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    if df["population"].isna().any():
        raise ValueError("population.csv: certaines populations sont invalides")

    return df

def merge_epi_pop(df_epi: pd.DataFrame, df_pop: pd.DataFrame) -> pd.DataFrame:
    data = df_epi.merge(df_pop, on="country", how="left")
    if data["population"].isna().any():
        missing = data[data["population"].isna()]["country"].unique().tolist()
        raise ValueError(f"population manquante pour: {missing}")
    return data

def compute_sir_from_data(data: pd.DataFrame) -> pd.DataFrame:
    # I = cases (infectés actifs)
    data = data.copy()
    data["I"] = data["cases"]
    # R = recovered + deaths
    data["R"] = data["recovered"] + data["deaths"]
    # S = population - I - R
    data["S"] = data["population"] - data["I"] - data["R"]
    data["S"] = data["S"].clip(lower=0)
    return data
