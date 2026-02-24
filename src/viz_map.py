from __future__ import annotations
from pathlib import Path
import json
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
    geo_path = Path(geojson_path)
    if not geo_path.exists():
        raise FileNotFoundError(
            f"GeoJSON introuvable: {geo_path}\n"
            f"Place-le dans data/ ou change le chemin."
        )

    # ✅ Forcer UTF-8 (évite UnicodeDecodeError sur Windows)
    try:
        geo_data = json.loads(geo_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        # fallback si jamais le fichier a un BOM ou autre variante
        geo_data = json.loads(geo_path.read_text(encoding="utf-8-sig"))

    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=geo_data,          # <-- on passe l'objet JSON (pas le chemin)
        data=df_values,
        columns=["country", "value"],
        key_on=key_on,
        fill_opacity=0.8,
        line_opacity=0.2,
        legend_name=legend_name,
    ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(out_html)
