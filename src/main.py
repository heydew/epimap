import pandas as pd
from pathlib import Path
from io_data import get_epi, get_pop, run_sir
import viz_curves
import viz_map

# les outs
OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(exist_ok=True)
GEO = Path(__file__).resolve().parents[1] / "data" / "world-countries.geojson"

if __name__ == "__main__":
    #  Chargement
    epi = get_epi()
    pop = get_pop(codes=set(epi["code"].unique()))

 # merge et Calcul
    df = epi.merge(pop, on="country").dropna(subset=["pop"])
    df = df.rename(columns={"pop": "population"})

    data = run_sir(df)

 # stats du monde
    world = data.groupby("date")[["S", "I", "R"]].sum().reset_index()
    # la pop totale
    total_p = data.drop_duplicates("country")["population"].sum()
# petit print en mode statistiques( manque la date du pic jvais faire plus tard)
    print(f"Stats: {len(data.country.unique())} pays chargés.")
    print(f"Max infectés: {world['I'].max():,.0f} personnes")

    # pour export
    f_sir = str(OUT / "sir.html")
    f_map = str(OUT / "map.html")

    viz_curves.plot_sir_animated(world, "Graphique SIR", f_sir)
    viz_map.choropleth_timelapse(data, str(GEO), f_map)

 #  La fin???????
    print("Ca ouvre!")
    viz_curves.out(f_sir)
    viz_map.out(f_map)