import json
import pandas as pd
from pathlib import Path
import webbrowser

# noms CSV
MAP_PAYS = {
    "United States":                "United States of America",
    "Congo":                        "Republic of the Congo",
    "Democratic Republic of Congo": "Democratic Republic of the Congo",
    "Tanzania":                     "United Republic of Tanzania",
    "Ivory Coast":                  "Côte d'Ivoire",
    "Czech Republic":               "Czechia",
    "South Korea":                  "South Korea",
    "North Korea":                  "North Korea",
    "Laos":                         "Lao PDR",
    "Syria":                        "Syrian Arab Republic",
    "Russia":                       "Russia",
    "Iran":                         "Iran",
    "Vietnam":                      "Vietnam",
    "East Timor":                   "Timor-Leste",
    "Eswatini":                     "eSwatini",
    "Cape Verde":                   "Cabo Verde",
}


def choropleth_timelapse(data, geojson_path, out_file):
    """Carte choroplèthe pour le pipeline COVID réel."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)

    df = data.copy()
    # FIXE: la colonne s'appelle "pays" dans ce pipeline (pas "country")
    col_pays = "pays" if "pays" in df.columns else "country"
    df["name"] = df[col_pays].replace(MAP_PAYS)
    df["pct"] = (df["I"] / df["population"].replace(0, 1) * 100).clip(0, 100)
    df["month"] = df["date"].dt.strftime("%Y-%m")

    pivot = df.groupby(["month", "name"])["pct"].mean().unstack(level=0).fillna(0)
    dates_list = sorted(pivot.columns.tolist())
    map_data = pivot.to_dict(orient="index")

    _ecrire_carte_html(geo, map_data, dates_list, "COVID-19 — Évolution mondiale", out_file)


def carte_simulation(data: pd.DataFrame, geojson_path: str, out_file: str, titre: str = "Simulation"):
    """Carte choroplèthe pour le pipeline simulation SEIRD+V."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)

    df = data.copy()
    df["name"] = df["country"].replace(MAP_PAYS)
    df["pct"] = (df["I"] / df["population"].replace(0, 1) * 100).clip(0, 100)
    df["month"] = df["date"].dt.strftime("%Y-%m")

    pivot = df.groupby(["month", "name"])["pct"].mean().unstack(level=0).fillna(0)
    dates_list = sorted(pivot.columns.tolist())
    map_data = pivot.to_dict(orient="index")

    _ecrire_carte_html(geo, map_data, dates_list, titre, out_file)


def _ecrire_carte_html(geo, map_data, dates_list, titre, out_file):

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{titre}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; font-family: sans-serif; }}
        #map {{ height: calc(100vh - 70px); width: 100%; }}
        .ctrl {{ padding: 10px 16px; display: flex; align-items: center; gap: 12px;
                 background: #222; color: #eee; }}
        .ctrl b {{ min-width: 80px; }}
        input[type=range] {{ flex: 1; accent-color: #4A90D9; }}
        button {{ padding: 4px 14px; border: none; border-radius: 5px;
                  background: #4A90D9; color: white; cursor: pointer; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="ctrl">
        <button onclick="togglePlay()">▶ Play</button>
        <b id="date_texte">—</b>
        <input type="range" id="curseur" min="0" value="0" oninput="majCarte(+this.value)">
    </div>
    <script>
        const MAP_DATA = {json.dumps(map_data)};
        const DATES    = {json.dumps(dates_list)};
        const GEO      = {json.dumps(geo)};
        let idx = 0, timer = null, couche = null;

        const map = L.map('map').setView([25, 10], 2);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

        function couleur(p) {{
            if (p > 1.0)  return '#b71c1c';
            if (p > 0.5)  return '#e53935';
            if (p > 0.1)  return '#fb8c00';
            if (p > 0.05) return '#fdd835';
            if (p > 0.01) return '#aed581';
            return '#eeeeee';
        }}

        function majCarte(n) {{
            idx = Math.min(Math.max(0, n), DATES.length - 1);
            const d = DATES[idx];
            document.getElementById('date_texte').innerText = d;
            document.getElementById('curseur').value = idx;

            if (couche) map.removeLayer(couche);
            couche = L.geoJson(GEO, {{
                style: function(feature) {{
                    const nom = feature.properties.name;
                    const pct = (MAP_DATA[nom] && MAP_DATA[nom][d]) ? MAP_DATA[nom][d] : 0;
                    return {{ fillColor: couleur(pct), weight: 0.5, color: '#fff', fillOpacity: 0.8 }};
                }},
                onEachFeature: function(feat, layer) {{
                    const nom = feat.properties.name;
                    const pct = (MAP_DATA[nom] && MAP_DATA[nom][DATES[idx]]) ? MAP_DATA[nom][DATES[idx]] : 0;
                    layer.bindTooltip('<b>' + nom + '</b><br>Infectés : ' + pct.toFixed(3) + '%', {{ sticky: true }});
                }}
            }}).addTo(map);
        }}

        function togglePlay() {{
            if (timer) {{ clearInterval(timer); timer = null; }}
            else {{
                timer = setInterval(() => {{
                    if (idx >= DATES.length - 1) {{ clearInterval(timer); timer = null; return; }}
                    majCarte(idx + 1);
                }}, 300);
            }}
        }}

        document.getElementById('curseur').max = DATES.length - 1;
        majCarte(0);
    </script>
</body>
</html>"""
    Path(out_file).write_text(html, encoding="utf-8")
    print(f"Carte exportée : {out_file}")


def out(p):
    webbrowser.open(Path(p).resolve().as_uri())