import json
import pandas as pd
from pathlib import Path
import webbrowser

# C'est les pays qui marchaient pas yen manque encore et ca marche toujours pas, faut debug jsp comment
MAP_PAYS = {
    "United States": "United States of America",
    "USA": "United States of America",
    "US":  "United States of America",
    "Congo":  "Republic of the Congo",
    "Democratic Republic of Congo":  "Democratic Republic of the Congo",
    "Czechia": "Czech Republic",
    "Cote d'Ivoire": "Ivory Coast",

}


def choropleth_timelapse(data, geojson_path, out_file):
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)

#  % d'infectés par pays
    df = data.copy()
    df["name"] = df["country"].replace(MAP_PAYS)
    df["pct"] = (df["I"] / df["population"] * 100)

# fait par mois
    df['month'] = df['date'].dt.strftime('%Y-%m')
    pivot = df.groupby(['month', 'name'])['pct'].mean().unstack(level=0).fillna(0)

#Leaflet
    dates_list = sorted(pivot.columns.tolist())
    map_data = pivot.to_dict(orient='index')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CARTE COVID</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ 
                height: 550px; 
                width: 100%; 
                border: 2px solid gray; 
            }}
            .info_box {{ 
                padding: 8px; 
                background: white; 
                border: 1px solid silver; 
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div style="padding: 15px;">
            <b id="date_texte">---</b> 
            <input type="range" id="curseur" style="width:75%" oninput="maj_carte(this.value)">
        </div>

        <script>
            const data = {json.dumps(map_data)};
            const dates = {json.dumps(dates_list)};
            const geo = {json.dumps(geo)};

            const map = L.map('map').setView([25, 10], 2);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);


            function couleur_pays(p) {{
                if (p > 1.0) return 'darkred';
                if (p > 0.5) return 'red';
                if (p > 0.1) return 'darkorange';
                if (p > 0.05) return 'orange';
                if (p > 0.01) return 'yellow';
                return 'lightgrey';
            }}

            let couche;
            function maj_carte(n) {{
                const d = dates[n];
                document.getElementById('date_texte').innerText = "Date : " + d;

                console.log("update date:", d); // petit log de test

                if(couche) map.removeLayer(couche);

                couche = L.geoJson(geo, {{
                    style: function(feature) {{
                        var pct = 0;
                        if (data[feature.properties.name]) {{
                            pct = data[feature.properties.name][d];
                        }}
                        return {{ 
                            fillColor: couleur_pays(pct), 
                            weight: 1, 
                            color: 'white', 
                            fillOpacity: 0.8 
                        }};
                    }}
                }}).addTo(map);
            }}

            document.getElementById('curseur').max = dates.length - 1;
            maj_carte(0);
        </script>
    </body>
    </html>
    """
    Path(out_file).write_text(html, encoding="utf-8")
# Va falloir animer la carte mais avk le slider on va dire que ca marche

def out(p):
    webbrowser.open(Path(p).resolve().as_uri())