from __future__ import annotations
import os
from pathlib import Path

import pandas as pd

from io_data import load_epidemie, load_population, merge_epi_pop, compute_sir_from_data
from model import SIRParams, SIRState, simulate_sir, indicators
from viz_curves import plot_sir
from viz_map import choropleth_world

# -------- Config --------
OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

GEOJSON_PATH = "data/world_countries.geojson"  # local si vous le versionnez pas

def latest_snapshot_for_map(data_sir: pd.DataFrame) -> pd.DataFrame:
    # prend la dernière date par pays pour la carte
    snap = (data_sir.sort_values("date").groupby("country").last().reset_index())
    # valeur = % infectés (plus scientifique qu'un nombre brut)
    snap["value"] = (snap["I"] / snap["population"]) * 100.0
    return snap[["country", "value"]]

def main():
    # 1) Lire CSV + calculer SIR depuis les données
    df_epi = load_epidemie()
    df_pop = load_population()
    data = merge_epi_pop(df_epi, df_pop)
    data_sir = compute_sir_from_data(data)

    print("=== Aperçu SIR calculé depuis les CSV ===")
    print(data_sir[["date", "country", "S", "I", "R"]].head())

    # 2) Simulation SIR (base scientifique)
    # Choix utilisateur (vous pourrez mettre une interface plus tard)
    country = "Canada"
    N = float(df_pop[df_pop["country"] == country]["population"].iloc[0])

    first = data_sir[data_sir["country"] == country].sort_values("date").iloc[0]
    S0, I0, R0 = float(first["S"]), float(first["I"]), float(first["R"])

    params = SIRParams(beta=0.35, gamma=0.12)  # vous ajusterez plus tard
    sim = simulate_sir(N, params, SIRState(S=S0, I=I0, R=R0), days=120, dt=1.0)

    ind = indicators(sim)
    print("\n=== Indicateurs ===")
    print(ind)

    # 3) Courbes
    plot_path = str(OUT_DIR / "sir_curves.png")
    plot_sir(sim, f"SIR - {country}", plot_path)
    print(f"\nCourbes sauvegardées: {plot_path}")

    # 4) Carte Folium (snapshot)
    map_df = latest_snapshot_for_map(data_sir)
    map_path = str(OUT_DIR / "map.html")

    # NOTE: selon le GeoJSON, il faudra peut-être key_on="feature.properties.ADMIN"
    choropleth_world(
        map_df,
        geojson_path=GEOJSON_PATH,
        out_html=map_path,
        key_on="feature.properties.name",
        legend_name="% infectés (snapshot CSV)"
    )
    print(f"Carte sauvegardée: {map_path}")

if __name__ == "__main__":
    main()
