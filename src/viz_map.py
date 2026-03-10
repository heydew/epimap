import json
import pandas as pd
from pathlib import Path
import webbrowser

# Mapping CSV (epidemie.csv) → GeoJSON (world-countries.geojson)
# Clé = nom dans epidemie.csv
# Valeur = nom dans world-countries.geojson
CSV_TO_GEO = {
    "Guinea-Bissau":                    "Guinea Bissau",
    "Congo":                            "Republic of the Congo",
    "Democratic Republic of Congo":     "Democratic Republic of the Congo",
    "Eswatini":                         "Swaziland",
    "Tanzania":                         "United Republic of Tanzania",
    "Bahamas":                          "The Bahamas",
    "Serbia":                           "Republic of Serbia",
    "North Macedonia":                  "Macedonia",
    "Czechia":                          "Czech Republic",
    "United States":                    "United States of America",
    # Ivory Coast n'a aucun équivalent dans le CSV — pas de données disponibles
}


def choropleth_timelapse(data, geojson_path, out_file):
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)

    df = data.copy()
    df["name"] = df["country"].replace(CSV_TO_GEO)
    df["pct"] = (df["I"] / df["population"] * 100)

    # Données mensuelles pour la carte choroplèthe
    df['month'] = df['date'].dt.strftime('%Y-%m')
    pivot = df.groupby(['month', 'name'])['pct'].mean().unstack(level=0).fillna(0)
    dates_list = sorted(pivot.columns.tolist())
    map_data = pivot.to_dict(orient='index')

    # Données SIR complètes par pays pour les graphiques au clic (smooth 7j)
    sir_by_country = {}
    for name, g in df.groupby('name'):
        g = g.sort_values('date')
        sir_by_country[name] = {
            'dates': [str(d)[:10] for d in g['date']],
            'I': g['I'].rolling(7).mean().fillna(0).astype(int).tolist(),
            'S': g['S'].rolling(7).mean().fillna(0).astype(int).tolist(),
            'R': g['R'].rolling(7).mean().fillna(0).astype(int).tolist(),
        }

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>CARTE COVID</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ margin: 0; font-family: sans-serif; }}
        #map {{ height: 560px; width: 100%; }}
        #controls {{
            padding: 10px 15px;
            display: flex;
            align-items: center;
            gap: 12px;
            background: #f5f5f5;
            border-top: 1px solid #ddd;
        }}
        #btn_play {{
            padding: 6px 18px; font-size: 15px; cursor: pointer;
            background: #2c7bb6; color: white; border: none; border-radius: 4px;
        }}
        #curseur {{ flex: 1; }}
        #modal {{
            display: none; position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 9999;
            justify-content: center; align-items: center;
        }}
        #modal.visible {{ display: flex; }}
        #modal_box {{
            background: white; border-radius: 8px;
            padding: 20px 24px; width: 640px; max-width: 95vw;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        #modal_titre {{ font-size: 18px; font-weight: bold; margin-bottom: 14px; }}
        #modal_fermer {{
            float: right; cursor: pointer; font-size: 22px;
            color: #aaa; border: none; background: none; line-height: 1;
        }}
        #modal_fermer:hover {{ color: #333; }}
        #modal_canvas {{ max-height: 320px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="controls">
        <button id="btn_play" onclick="toggle_play()">&#9654; Play</button>
        <b id="date_texte" style="min-width: 90px;">---</b>
        <input type="range" id="curseur" oninput="set_idx(this.value)">
        <span style="font-size:12px; color:#888;">&#128065; Cliquer sur un pays pour son graphique</span>
    </div>

    <div id="modal" onclick="fermer_modal(event)">
        <div id="modal_box">
            <button id="modal_fermer" onclick="document.getElementById('modal').classList.remove('visible')">&#10005;</button>
            <div id="modal_titre">---</div>
            <canvas id="modal_canvas"></canvas>
        </div>
    </div>

    <script>
        const map_data = {json.dumps(map_data)};
        const dates = {json.dumps(dates_list)};
        const geo = {json.dumps(geo)};
        const sir_data = {json.dumps(sir_by_country)};

        const map = L.map('map').setView([25, 10], 2);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

        function couleur_pays(p) {{
            if (p > 1.0) return 'darkred';
            if (p > 0.5) return 'red';
            if (p > 0.1) return 'darkorange';
            if (p > 0.05) return 'orange';
            if (p > 0.001) return 'yellow';
            return 'lightgrey';
        }}

        let couche;
        function maj_carte(n) {{
            const d = dates[n];
            document.getElementById('date_texte').innerText = d;
            document.getElementById('curseur').value = n;

            if (couche) map.removeLayer(couche);

            couche = L.geoJson(geo, {{
                style: function(feature) {{
                    var pct = 0;
                    const nom = feature.properties.name;
                    if (map_data[nom]) pct = map_data[nom][d] || 0;
                    return {{ fillColor: couleur_pays(pct), weight: 1, color: 'white', fillOpacity: 0.8 }};
                }},
                onEachFeature: function(feature, layer) {{
                    const nom = feature.properties.name;
                    layer.on('click', function() {{
                        ouvrir_graphique(nom);
                    }});
                    layer.on('mouseover', function(e) {{
                        const pct = (map_data[nom] && map_data[nom][dates[idx]])
                            ? map_data[nom][dates[idx]].toFixed(3) + '%'
                            : 'pas de donnees';
                        layer.bindTooltip('<b>' + nom + '</b><br>Infectes: ' + pct, {{sticky: true}}).openTooltip(e.latlng);
                    }});
                }}
            }}).addTo(map);
        }}

        // graphique pour chaque pays quand on fait clique gauche dessus sur le pays
        let chart_instance = null;

        function ouvrir_graphique(nom) {{
            const d = sir_data[nom];
            if (!d) {{
                alert('Pas de données SIR pour : ' + nom);
                return;
            }}
            document.getElementById('modal_titre').innerText = nom + ' \u2014 Courbe SIR';
            document.getElementById('modal').classList.add('visible');

            if (chart_instance) {{ chart_instance.destroy(); chart_instance = null; }}

            const ctx = document.getElementById('modal_canvas').getContext('2d');
            chart_instance = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: d.dates,
                    datasets: [
                        {{ label: 'Infectes (I)', data: d.I, borderColor: 'crimson',    backgroundColor: 'rgba(220,20,60,0.07)',  fill: true, pointRadius: 0, tension: 0.3 }},
                        {{ label: 'Retablis (R)', data: d.R, borderColor: 'seagreen',   backgroundColor: 'rgba(46,139,87,0.07)', fill: true, pointRadius: 0, tension: 0.3 }},
                        {{ label: 'Susceptibles (S)', data: d.S, borderColor: '#2c7bb6', backgroundColor: 'rgba(44,123,182,0.07)', fill: true, pointRadius: 0, tension: 0.3 }}
                    ]
                }},
                options: {{
                    animation: false,
                    responsive: true,
                    plugins: {{ legend: {{ position: 'top' }} }},
                    scales: {{
                        x: {{ ticks: {{ maxTicksLimit: 8 }} }},
                        y: {{ beginAtZero: true }}
                    }}
                }}
            }});
        }}

        function fermer_modal(e) {{
            if (e.target === document.getElementById('modal'))
                document.getElementById('modal').classList.remove('visible');
        }}

        // Play/Stop
        function set_idx(v) {{ idx = parseInt(v); maj_carte(idx); }}

        let idx = 0, timer = null;

        function toggle_play() {{
            if (timer) {{
                clearInterval(timer); timer = null;
                document.getElementById('btn_play').innerHTML = '&#9654; Play';
            }} else {{
                if (idx >= dates.length - 1) idx = 0;
                document.getElementById('btn_play').innerHTML = '&#9646;&#9646; Stop';
                timer = setInterval(() => {{
                    idx++;
                    maj_carte(idx);
                    if (idx >= dates.length - 1) {{
                        clearInterval(timer); timer = null;
                        document.getElementById('btn_play').innerHTML = '&#9654; Play';
                    }}
                }}, 200);
            }}
        }}

        document.getElementById('curseur').max = dates.length - 1;
        maj_carte(0);
    </script>
</body>
</html>"""
    Path(out_file).write_text(html, encoding="utf-8")


def out(p):
    webbrowser.open(Path(p).resolve().as_uri())