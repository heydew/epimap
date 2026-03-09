import pandas as pd
from pathlib import Path
from viz_map import COUNTRY_NAME_MAP

from io_data    import load_epidemie, load_population, merge_epi_pop, compute_sir
from viz_curves import plot_sir_animated, out as ouvre_graphique
from viz_map    import choropleth_timelapse, out as ouvre_carte


OUT_DIR      = Path(__file__).resolve().parents[1] / "out"
GEOJSON_PATH = Path(__file__).resolve().parents[1] / "data" / "world-countries.geojson"
OUT_DIR.mkdir(exist_ok=True)


def monde(data_sir):
    world = data_sir.groupby("date")[["S","I","R"]].sum().reset_index()

    # une seule valeur de population par pays (pas par date)
    pop_monde = data_sir.drop_duplicates(subset="country")["population"].sum()
    world["population"] = pop_monde

    return world.sort_values("date")


if __name__ == "__main__":

    df_epi = load_epidemie()

    # passer les codes ISO valides pour virer les agregats regionaux
    # du csv population (genre "Arab World", "WLD", etc.)
    codes_valides = set(df_epi["code"].dropna().unique())
    df_pop = load_population(codes_valides=codes_valides)

    data     = merge_epi_pop(df_epi, df_pop)
    data_sir = compute_sir(data)

    world    = monde(data_sir)
    date_min = world["date"].min().date()
    date_max = world["date"].max().date()
    n_pays   = data_sir["country"].nunique()
    pop_G    = world["population"].iloc[0] / 1e9

    print(f"C'est parti les mecs, données COVID chargées ({date_min} -> {date_max})")
    print(f"{n_pays} pays, population mondiale ~{pop_G:.1f}G")
    print(f"pic infectés : {world['I'].max():,.0f}  ({world.loc[world['I'].idxmax(), 'date'].date()})")
    print("génération des fichiers...")

    path_sir   = str(OUT_DIR / "sir_monde.html")
    path_carte = str(OUT_DIR / "carte_timelapse.html")

    plot_sir_animated(world, f"COVID-19 monde ({date_min} -> {date_max})", path_sir)

    import json

    with open(str(GEOJSON_PATH), encoding="utf-8") as f:
        geo = json.load(f)

    noms_geojson = set(f["properties"]["name"] for f in geo["features"])
    noms_csv = set(data_sir["country"].apply(lambda x: COUNTRY_NAME_MAP.get(x, x)))

    for p in ["congo"]:
        match = df_epi[df_epi["country"].str.lower().str.contains(p)]
        print(match["country"].unique())








    choropleth_timelapse(data_sir, str(GEOJSON_PATH), path_carte)

    print("ouverture dans le navigateur:")
    ouvre_graphique(path_sir)
    ouvre_carte(path_carte)