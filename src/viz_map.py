import json
import pandas as pd
from pathlib import Path
import webbrowser

MAP_PAYS = {
    "United States":                        "United States of America",
    "Congo":                                "Republic of the Congo",
    "Democratic Republic of Congo":         "Democratic Republic of the Congo",
    "Tanzania":                             "United Republic of Tanzania",
    "Ivory Coast":                          "Côte d'Ivoire",
    "Cote d'Ivoire":                        "Côte d'Ivoire",
    "Czech Republic":                       "Czechia",
    "Laos":                                 "Lao PDR",
    "Syria":                                "Syrian Arab Republic",
    "East Timor":                           "Timor-Leste",
    "Timor":                                "Timor-Leste",
    "Eswatini":                             "eSwatini",
    "Cape Verde":                           "Cabo Verde",
    "Burma":                                "Myanmar",
    "Brunei":                               "Brunei Darussalam",
    "Moldova":                              "Republic of Moldova",
    "North Macedonia":                      "Macedonia",
    "Micronesia (country)":                 "Federated States of Micronesia",
    "Micronesia":                           "Federated States of Micronesia",
    "Palestine":                            "West Bank",
    "Guinea Bissau":                        "Guinea-Bissau",
    "Sao Tome and Principe":                "São Tomé and Príncipe",
    "Saint Kitts and Nevis":                "St. Kitts and Nevis",
    "Saint Vincent and the Grenadines":     "St. Vincent and the Grenadines",
    "Bosnia and Herzegovina":               "Bosnia and Herz.",
    "Central African Republic":             "Central African Rep.",
    "South Sudan":                          "S. Sudan",
    "Equatorial Guinea":                    "Eq. Guinea",
    "Western Sahara":                       "W. Sahara",
    "Dominican Republic":                   "Dominican Rep.",
    "Solomon Islands":                      "Solomon Is.",
    "Kyrgyz Republic":                      "Kyrgyzstan",
    "Slovak Republic":                      "Slovakia",
    "Trinidad and Tobago":                  "Trinidad and Tobago",
    "Antigua and Barbuda":                  "Antigua and Barb.",
    "Marshall Islands":                     "Marshall Is.",
}


def _preparer_donnees(data, col_pays):
    df = data.copy()
    df["name"] = df[col_pays].replace(MAP_PAYS)
    df["pct"] = (df["I"] / df["population"].replace(0, 1) * 100).clip(0, 100).round(4)
    df["month"] = df["date"].dt.strftime("%Y-%m")
    pivot = df.groupby(["month", "name"])["pct"].mean().unstack(level=0).fillna(0)
    dates_list = sorted(pivot.columns.tolist())
    map_data = pivot.to_dict(orient="index")
    return map_data, dates_list


def choropleth_timelapse(data, geojson_path, out_file):
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    col_pays = "pays" if "pays" in data.columns else "country"
    map_data, dates_list = _preparer_donnees(data, col_pays)
    _ecrire_carte_html(geo, map_data, dates_list, "COVID-19 — Évolution mondiale", out_file)


def carte_simulation(data, geojson_path, out_file, titre="Simulation"):
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    map_data, dates_list = _preparer_donnees(data, "country")
    _ecrire_carte_html(geo, map_data, dates_list, titre, out_file)


def _ecrire_carte_html(geo, map_data, dates_list, titre, out_file):
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{titre}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; font-family: sans-serif; }}
        #map {{ height: calc(100vh - 60px); width: 100%; }}
        .ctrl {{ padding: 8px 16px; display: flex; align-items: center; gap: 12px;
                 background: #222; color: #eee; height: 60px; }}
        .ctrl b {{ min-width: 80px; font-size: 13px; }}
        input[type=range] {{ flex: 1; accent-color: #4A90D9; }}
        button {{ padding: 4px 14px; border: none; border-radius: 5px;
                  background: #4A90D9; color: white; cursor: pointer; font-size: 13px; }}
        button:hover {{ background: #357abd; }}
        .titre {{ font-size: 13px; color: #aaa; white-space: nowrap; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="ctrl">
        <button id="btn" onclick="togglePlay()">&#9654; Play</button>
        <b id="date_texte">—</b>
        <input type="range" id="curseur" min="0" value="0" oninput="majCarte(+this.value)">
        <span class="titre">{titre}</span>
    </div>
    <script>
        const MAP_DATA = {json.dumps(map_data)};
        const DATES    = {json.dumps(dates_list)};
        const GEO      = {json.dumps(geo)};
        let idx = 0, timer = null;

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

        const couche = L.geoJson(GEO, {{
            style: function(feat) {{
                return {{ fillColor: '#eeeeee', weight: 0.5, color: '#fff', fillOpacity: 0.8 }};
            }},
            onEachFeature: function(feat, layer) {{
                layer.bindTooltip('', {{ sticky: true }});
            }}
        }}).addTo(map);

        const layerIndex = {{}};
        couche.eachLayer(function(layer) {{
            layerIndex[layer.feature.properties.name] = layer;
        }});

        function majCarte(n) {{
            idx = Math.min(Math.max(0, n), DATES.length - 1);
            const d = DATES[idx];
            document.getElementById('date_texte').innerText = d;
            document.getElementById('curseur').value = idx;
            for (const nom in layerIndex) {{
                const pct = (MAP_DATA[nom] && MAP_DATA[nom][d]) ? MAP_DATA[nom][d] : 0;
                layerIndex[nom].setStyle({{ fillColor: couleur(pct) }});
                layerIndex[nom].setTooltipContent('<b>' + nom + '</b><br>Infectés : ' + pct.toFixed(3) + '%');
            }}
        }}

        function togglePlay() {{
            if (timer) {{
                clearInterval(timer); timer = null;
                document.getElementById('btn').innerText = '&#9654; Play';
            }} else {{
                document.getElementById('btn').innerText = '&#9646;&#9646; Pause';
                timer = setInterval(() => {{
                    if (idx >= DATES.length - 1) {{
                        clearInterval(timer); timer = null;
                        document.getElementById('btn').innerText = '&#9654; Play';
                        return;
                    }}
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