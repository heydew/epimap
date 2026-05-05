import pandas as pd
from io_data import get_epi, get_pop, run_sir
import viz_curves
import viz_map
import os

DOSSIER_OUT = "../out"
CHEMIN_GEO = "../data/world-countries.geojson"

if not os.path.exists(DOSSIER_OUT):
    os.mkdir(DOSSIER_OUT)

if __name__ == "__main__":
    donnees_epi = get_epi()
    donnees_pop = get_pop(codes=set(donnees_epi["code"].unique()))

    # merge sur code ISO
    df = donnees_epi.merge(donnees_pop[["code", "pop"]], on="code").dropna(subset=["pop"])
    df = df.rename(columns={"pop": "population"})

    donnees = run_sir(df)

    monde = donnees.groupby("date")[["S", "I", "R"]].sum().reset_index()

    print(f"Pays charges : {donnees['pays'].nunique()}")
    print(f"Max infectes : {monde['I'].max():,.0f}")

    fichier_sir = DOSSIER_OUT + "/sir.html"
    fichier_carte = DOSSIER_OUT + "/map.html"


    viz_curves.plot_sir_animated(monde, "Courbe infectés COVID", fichier_sir)

    viz_map.choropleth_timelapse(donnees, CHEMIN_GEO, fichier_carte)

    print("Ca ouvre!")
    viz_curves.out(fichier_sir)
    viz_map.out(fichier_carte)