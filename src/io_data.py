from __future__ import annotations
from pathlib import Path
import pandas as pd

REQUIRED_EPI = {"date", "country", "cases", "recovered", "deaths"}
REQUIRED_POP = {"country", "population"}

# racine du projet = dossier parent de src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

def load_epidemie(path: str | Path = DATA_DIR / "epidemie.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

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

def load_population(path: str | Path = DATA_DIR / "population.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

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
    data = data.copy()
    data["I"] = data["cases"]
    data["R"] = data["recovered"] + data["deaths"]
    data["S"] = (data["population"] - data["I"] - data["R"]).clip(lower=0)
    return data
