from __future__ import annotations
from pathlib import Path
import pandas as pd

# --- Formats acceptés ---
REQUIRED_EPI_SIMPLE = {"date", "country", "cases", "recovered", "deaths"}
REQUIRED_POP_SIMPLE = {"country", "population"}

# ton epidemie.csv (OWID)
REQUIRED_EPI_OWID = {
    "Entity",
    "Day",
    "Cumulative confirmed cases",
    "Cumulative confirmed deaths",
}

# ton population.csv (World Bank)
REQUIRED_POP_WB = {"Country Name", "Year", "Value"}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def load_epidemie(path: str | Path = DATA_DIR / "epidemie.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    df = pd.read_csv(path)
    cols = set(df.columns)

    # --- Cas A: format "simple" ---
    if REQUIRED_EPI_SIMPLE.issubset(cols):
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        if out["date"].isna().any():
            raise ValueError("epidemie.csv: certaines dates sont invalides")

        out["country"] = out["country"].astype(str).str.strip()
        for c in ["cases", "recovered", "deaths"]:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

        return out.sort_values(["country", "date"]).reset_index(drop=True)

    # --- Cas B: OWID (celui que tu as) ---
    if REQUIRED_EPI_OWID.issubset(cols):
        out = pd.DataFrame()
        out["country"] = df["Entity"].astype(str).str.strip()
        out["date"] = pd.to_datetime(df["Day"], errors="coerce")
        if out["date"].isna().any():
            raise ValueError("epidemie.csv (OWID): certaines dates sont invalides")

        # IMPORTANT: ce sont des cumulés (pas des infectés actifs)
        out["cases"] = pd.to_numeric(df["Cumulative confirmed cases"], errors="coerce").fillna(0.0)
        out["deaths"] = pd.to_numeric(df["Cumulative confirmed deaths"], errors="coerce").fillna(0.0)

        # pas présent dans OWID -> on met 0 pour ne pas casser ton pipeline
        out["recovered"] = 0.0

        return out.sort_values(["country", "date"]).reset_index(drop=True)

    raise ValueError(f"epidemie.csv: format inconnu. Colonnes trouvées: {list(df.columns)}")


def load_population(path: str | Path = DATA_DIR / "population.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    df = pd.read_csv(path)
    cols = set(df.columns)

    # --- Cas A: format "simple" ---
    if REQUIRED_POP_SIMPLE.issubset(cols):
        out = df.copy()
        out["country"] = out["country"].astype(str).str.strip()
        out["population"] = pd.to_numeric(out["population"], errors="coerce")
        if out["population"].isna().any():
            raise ValueError("population.csv: certaines populations sont invalides")
        return out

    # --- Cas B: World Bank (celui que tu as) ---
    if REQUIRED_POP_WB.issubset(cols):
        tmp = df.copy()
        tmp["country"] = tmp["Country Name"].astype(str).str.strip()
        tmp["Year"] = pd.to_numeric(tmp["Year"], errors="coerce")
        tmp["Value"] = pd.to_numeric(tmp["Value"], errors="coerce")
        tmp = tmp.dropna(subset=["country", "Year", "Value"])

        # dernière année dispo par pays
        tmp = tmp.sort_values(["country", "Year"])
        latest = tmp.groupby("country", as_index=False).last()

        out = latest[["country", "Value"]].rename(columns={"Value": "population"})
        return out

    raise ValueError(f"population.csv: format inconnu. Colonnes trouvées: {list(df.columns)}")


def merge_epi_pop(df_epi: pd.DataFrame, df_pop: pd.DataFrame) -> pd.DataFrame:
    data = df_epi.merge(df_pop, on="country", how="left")
    if data["population"].isna().any():
        missing = data.loc[data["population"].isna(), "country"].unique().tolist()
        raise ValueError(f"population manquante pour: {missing}")
    return data


def compute_sir_from_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    Avec OWID:
    - cases est cumulatif
    - recovered = 0
    => S/I/R ici sert surtout à visualiser/pipeliner, pas "infectés actifs" réels.
    """
    data = data.copy()
    data["I"] = data["cases"]
    data["R"] = data["recovered"] + data["deaths"]
    data["S"] = (data["population"] - data["I"] - data["R"]).clip(lower=0)
    return data
