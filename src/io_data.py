from __future__ import annotations
from pathlib import Path
import pandas as pd

# --- Formats acceptés ---
REQUIRED_EPI_SIMPLE = {"date", "country", "cases", "recovered", "deaths"}
REQUIRED_POP_SIMPLE = {"country", "population"}

# OWID (ton epidemie.csv)
REQUIRED_EPI_OWID = {
    "Entity",
    "Day",
    "Cumulative confirmed cases",
    "Cumulative confirmed deaths",
}

# World Bank (ton population.csv)
REQUIRED_POP_WB = {"Country Name", "Year", "Value"}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# Mapping OWID -> GeoJSON (les noms exacts du GeoJSON)
OWID_TO_GEOJSON = {
    "Antigua and Barbuda": "Antigua and Barb.",
    "Bosnia and Herzegovina": "Bosnia and Herz.",
    "Bonaire Sint Eustatius and Saba": "Bonaire Sint Eustatius and Saba",
    "British Virgin Islands": "British Virgin Is.",
    "Cabo Verde": "Cabo Verde",
    "Cape Verde": "Cabo Verde",
    "Cayman Islands": "Cayman Is.",
    "Central African Republic": "Central African Rep.",
    "Cook Islands": "Cook Is.",
    "Curacao": "Curaçao",
    "Czechia": "Czechia",
    "Democratic Republic of Congo": "Dem. Rep. Congo",
    "Dominican Republic": "Dominican Rep.",
    "East Timor": "Timor-Leste",
    "Equatorial Guinea": "Eq. Guinea",
    "Eswatini": "eSwatini",
    "Falkland Islands": "Falkland Is.",
    "Faroe Islands": "Faeroe Is.",
    "French Guiana": "French Guiana",
    "French Polynesia": "Fr. Polynesia",
    "Guadeloupe": "Guadeloupe",
    "Marshall Islands": "Marshall Is.",
    "Martinique": "Martinique",
    "Mayotte": "Mayotte",
    "Micronesia (country)": "Micronesia",
    "Northern Mariana Islands": "N. Mariana Is.",
    "Pitcairn": "Pitcairn Is.",
    "Reunion": "Réunion",
    "Saint Barthelemy": "St-Barthélemy",
    "Saint Kitts and Nevis": "St. Kitts and Nevis",
    "Saint Lucy": "Saint Lucia",
    "Saint Martin (French part)": "St-Martin",
    "Saint Pierre and Miquelon": "St. Pierre and Miquelon",
    "Saint Vincent and the Grenadines": "St. Vin. and Gren.",
    "Sao Tome and Principe": "São Tomé and Principe",
    "Sint Maarten (Dutch part)": "Sint Maarten",
    "Solomon Islands": "Solomon Is.",
    "South Sudan": "S. Sudan",
    "Timor": "Timor-Leste",
    "Tokelau": "Tokelau",
    "Turks and Caicos Islands": "Turks and Caicos Is.",
    "United States": "United States of America",
    "United States Virgin Islands": "U.S. Virgin Is.",
    "Wallis and Futuna": "Wallis and Futuna Is.",
    "Iran": "Iran",
    "Iraq": "Iraq",
    "Kyrgyzstan": "Kyrgyzstan",
    "Laos": "Laos",
    "Macao": "Macao",
    "Myanmar": "Myanmar",
    "North Korea": "North Korea",
    "North Macedonia": "North Macedonia",
    "Palau": "Palau",
    "Palestine": "Palestine",
    "Papua New Guinea": "Papua New Guinea",
    "Philippines": "Philippines",
    "Russia": "Russia",
    "Serbia": "Serbia",
    "Slovakia": "Slovakia",
    "South Korea": "South Korea",
    "Syria": "Syria",
    "Taiwan": "Taiwan",
    "Tanzania": "Tanzania",
    "Trinidad and Tobago": "Trinidad and Tobago",
    "Turkey": "Turkey",
    "Uruguay": "Uruguay",
    "Uzbekistan": "Uzbekistan",
    "Venezuela": "Venezuela",
    "Vietnam": "Vietnam",
    "Yemen": "Yemen",
    "Zambia": "Zambia",
    "Zimbabwe": "Zimbabwe",
}
from difflib import get_close_matches

def fuzzy_match_country(country: str, geo_names: list[str], cutoff: float = 0.6) -> str:
    """Try to fuzzy match a country name to GeoJSON names if exact match fails"""
    matches = get_close_matches(country, geo_names, n=1, cutoff=cutoff)
    return matches[0] if matches else country


def load_epidemie(path: str | Path = DATA_DIR / "epidemie.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    df = pd.read_csv(path)
    cols = set(df.columns)

    if REQUIRED_EPI_OWID.issubset(cols):
        # Load GeoJSON to get valid country names
        import json
        geo_path = Path(DATA_DIR / "world_countries.geojson")
        with open(geo_path, encoding='utf-8') as f:
            geo = json.load(f)
        geo_names = [f['properties'].get('name') for f in geo['features']]

        out = pd.DataFrame()
        out["country"] = df["Entity"].astype(str).str.strip()

        # Apply mapping
        out["country"] = out["country"].replace(OWID_TO_GEOJSON, regex=False)

        # Fuzzy match anything still not in GeoJSON
        out["country"] = out["country"].apply(
            lambda x: fuzzy_match_country(x, geo_names) if x not in geo_names else x
        )

        out["date"] = pd.to_datetime(df["Day"], errors="coerce")
        if out["date"].isna().any():
            raise ValueError("epidemie.csv (OWID): certaines dates sont invalides")

        out["cases"] = pd.to_numeric(df["Cumulative confirmed cases"], errors="coerce").fillna(0.0)
        out["deaths"] = pd.to_numeric(df["Cumulative confirmed deaths"], errors="coerce").fillna(0.0)
        out["recovered"] = 0.0

        return out.sort_values(["country", "date"]).reset_index(drop=True)

    raise ValueError(f"epidemie.csv: format inconnu. Colonnes trouvées: {list(df.columns)}")

    # --- Cas B: OWID (celui que tu as) ---
    if REQUIRED_EPI_OWID.issubset(cols):
        out = pd.DataFrame()
        out["country"] = df["Entity"].astype(str).str.strip()
        out["country"] = out["country"].replace(OWID_TO_GEOJSON, regex=False)#-- normalisation noms pour GeoJSON
        out["date"] = pd.to_datetime(df["Day"], errors="coerce")
        if out["date"].isna().any():
            raise ValueError("epidemie.csv (OWID): certaines dates sont invalides")

        out["cases"] = pd.to_numeric(df["Cumulative confirmed cases"], errors="coerce").fillna(0.0)
        out["deaths"] = pd.to_numeric(df["Cumulative confirmed deaths"], errors="coerce").fillna(0.0)

        # pas présent dans OWID -> 0 (pour ne pas casser le pipeline)
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


def merge_epi_pop(df_epi: pd.DataFrame, df_pop: pd.DataFrame, drop_missing: bool = True) -> pd.DataFrame:
    data = df_epi.merge(df_pop, on="country", how="left")

    if data["population"].isna().any():
        missing = data.loc[data["population"].isna(), "country"].unique().tolist()

        if drop_missing:
            data = data.dropna(subset=["population"]).copy()
            preview = missing[:25]
            more = "" if len(missing) <= 25 else f" (+{len(missing)-25} autres)"
            print(f"[WARN] Population manquante (lignes supprimées): {preview}{more}")
        else:
            raise ValueError(f"population manquante pour: {missing}")

    return data


def compute_sir_from_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    Avec OWID:
    - cases est cumulatif
    - recovered = 0
    => S/I/R ici sert surtout à visualiser/pipeliner.
    """
    data = data.copy()
    data["I"] = data["cases"]
    data["R"] = data["recovered"] + data["deaths"]
    data["S"] = (data["population"] - data["I"] - data["R"]).clip(lower=0)
    return data
