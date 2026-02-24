from __future__ import annotations
import os
import folium
import pandas as pd

def choropleth_world(
    df_values: pd.DataFrame,
    geojson_path: str,
    out_html: str,
    key_on: str = "feature.properties.name",
    legend_name: str = "Infectés (valeur)",
) -> None:
    """
    df_values doit contenir: country, value
    geojson doit avoir un champ qui correspond à 'country' (souvent properties.name ou properties.ADMIN).
    """
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(
            f"GeoJSON introuvable: {geojson_path}\n"
            f"Place-le dans data/ ou change le chemin."
        )

    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=geojson_path,
        data=df_values,
        columns=["country", "value"],
        key_on=key_on,
        fill_opacity=0.8,
        line_opacity=0.2,
        legend_name=legend_name,
    ).add_to(m)

    # Tooltip (liste simple) — optionnel, mais utile
    folium.LayerControl().add_to(m)
    m.save(out_html)
