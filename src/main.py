from __future__ import annotations
from pathlib import Path
import pandas as pd

from io_data import load_epidemie, load_population, merge_epi_pop, compute_sir_from_data
from model import SIRParams, SIRState, simulate_sir, indicators
from viz_curves import plot_sir
from viz_map import choropleth_world

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "out"
OUT_DIR.mkdir(exist_ok=True)

GEOJSON_PATH = PROJECT_ROOT / "data" / "world_countries.geojson"


def latest_snapshot_for_map(data_sir: pd.DataFrame) -> pd.DataFrame:
    snap = data_sir.sort_values("date").groupby("country").last().reset_index()
    snap["value"] = (snap["I"] / snap["population"]) * 100.0
    return snap[["country", "value"]]


def main():
    # 1) Lire CSV + calculer SIR depuis les données
    df_epi = load_epidemie()
    df_pop = load_population()
    data = merge_epi_pop(df_epi, df_pop, drop_missing=True)
    data_sir = compute_sir_from_data(data)

    print("=== Aperçu SIR calculé depuis les CSV ===")
    print(data_sir[["date", "country", "S", "I", "R"]].head())

    # 2) Simulation SIR
    country = "Canada"

    pop_series = df_pop.loc[df_pop["country"] == country, "population"]
    if pop_series.empty:
        raise ValueError(f"Pays '{country}' introuvable dans population.csv")
    N = float(pop_series.iloc[0])

    rows = data_sir.loc[data_sir["country"] == country].sort_values("date")
    if rows.empty:
        raise ValueError(f"Pays '{country}' introuvable dans epidemie.csv après merge")

    # ✅ prendre le premier jour où I > 0 (sinon simulation plate)
    rows_pos = rows[rows["I"] > 0]
    if rows_pos.empty:
        raise ValueError(f"Aucun cas > 0 trouvé pour {country}")
    first = rows_pos.iloc[0]

    S0, I0, R0 = float(first["S"]), float(first["I"]), float(first["R"])

    params = SIRParams(beta=0.35, gamma=0.12)
    sim = simulate_sir(N, params, SIRState(S=S0, I=I0, R=R0), days=120, dt=1.0)

    print("\n=== Indicateurs ===")
    print(indicators(sim))

    # 3) Courbes (✅ en % pour que ça soit lisible)
    plot_path = OUT_DIR / "sir_curves.png"
    plot_sir(sim, f"SIR - {country}", str(plot_path), N=N)
    print(f"\nCourbes sauvegardées: {plot_path}")

    # 4) Carte Folium (snapshot)
    map_df = latest_snapshot_for_map(data_sir)
    map_path = OUT_DIR / "map.html"

    choropleth_world(
        map_df,
        geojson_path=str(GEOJSON_PATH),
        out_html=str(map_path),
        key_on="feature.properties.name",
        legend_name="% infectés (snapshot CSV)"
    )
    print(f"Carte sauvegardée: {map_path}")


if __name__ == "__main__":
    main()
