import json
import pandas as pd
from pathlib import Path
import webbrowser

# fait un dictionnaire pour les pays qui ont noms diff, ya pas cote d'ivoire dans le csv tho
NOM_CSV_VERS_GEO = {
    "Guinea-Bissau": "Guinea Bissau",
    "Congo": "Republic of the Congo",
    "Democratic Republic of Congo": "Democratic Republic of the Congo",
    "Eswatini": "Swaziland",
    "Tanzania": "United Republic of Tanzania",
    "Bahamas": "The Bahamas",
    "Serbia": "Republic of Serbia",
    "North Macedonia": "Macedonia",
    "Czechia": "Czech Republic",
    "United States": "United States of America",
}


def carte_covid(donnees, chemin_geojson, fichier_sortie):
    with open(chemin_geojson, "r", encoding="utf-8") as f:
        geo = json.load(f)

    df = donnees.copy()
    df["nom"] = df["pays"].replace(NOM_CSV_VERS_GEO)
    df["pct"] = (df["I"] / df["population"] * 100)

#fait par mois sinon le fichier html est trop chargé
    df['mois'] = df['date'].dt.strftime('%Y-%m')
    temp = df.groupby(['mois', 'nom'])['pct'].mean()
    temp = temp.unstack(level=0)
    temp = temp.fillna(0)
    liste_dates = sorted(temp.columns.tolist())
    data_carte = {}
    for pays in temp.index:
        data_carte[pays] = {}
        for m in liste_dates:
            data_carte[pays][m] = temp.loc[pays, m]

# prend les dates par AAAA-MM-JJ comme ca ya pas d'heures ni de sec
    sir_par_pays = {}
    for nom, groupe in df.groupby('nom'):
        groupe = groupe.sort_values('date')
        dates_pays = [str(d)[:10] for d in groupe['date']]
# smooth sur 7 jours
        I_smooth = groupe['I'].rolling(7).mean().fillna(0)
        S_smooth = groupe['S'].rolling(7).mean().fillna(0)
        R_smooth = groupe['R'].rolling(7).mean().fillna(0)
        sir_par_pays[nom] = {
            'dates': dates_pays,
            'I': [int(x) for x in I_smooth],
            'S': [int(x) for x in S_smooth],
            'R': [int(x) for x in R_smooth],
        }

    html = f"""<!DOCTYPE html>
<html>
<head>
<title>CARTE COVID</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {{ margin: 0; font-family: Arial; }}
#carte {{ width: 100%; height: calc(100vh - 50px); }}
.ctrls {{ display: flex; align-items: center; gap: 10px; padding: 8px 15px; }}
#popup {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999; }}
#popup-box {{ background:white; width:550px; margin-left:400px; margin-top:100px; padding:20px; }}
#popup-box canvas {{ max-height:280px; }}
</style>
</head>
<body>

<div id="carte"></div>
<div class="ctrls">
    <button onclick="jouer()">Play/Pause</button>
    <span id="txt">—</span>
    <input type="range" id="curseur" style="flex:1" oninput="set_idx(this.value)">
</div>

<div id="popup">
<div id="popup-box">
    <p id="popup-titre" style="font-weight:bold">—</p>
    <canvas id="popup-graph"></canvas>
    <br><button onclick="document.getElementById('popup').style.display='none'">Fermer</button>
</div>
</div>

<script>

//les variables
var data_carte = {json.dumps(data_carte)};
var liste_dates = {json.dumps(liste_dates)};
var geo = {json.dumps(geo)};
var sir_par_pays = {json.dumps(sir_par_pays)};
var nb_dates = liste_dates.length;


// cree la carte avk leaflet
var carte = L.map('carte').setView([20, 10], 2);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
attribution: '© OpenStreetMap contributors'
}}).addTo(carte);

//return une differente couleur selon le pourcentage de la pop infecté
function couleur_pays(p) {{
if (p > 1) return 'darkred';
else if (p > 0.5) return 'red';
else if (p > 0.1) return 'darkorange';
else if (p > 0.05) return 'orange';
else if (p > 0.001) return 'yellow';
else return 'lightgrey';
}}

var couche_active = null;
var idx_courant = 0;
var minuterie = null;

//met a jour la carte pour la date n
function maj_carte(n) {{
var d = liste_dates[n];
document.getElementById('txt').innerText = d;
document.getElementById('curseur').value = n;

// faut enlever l'ancienne couche avant sinon ca s'enpile 
if (couche_active) {{
carte.removeLayer(couche_active);
}}

couche_active = L.geoJson(geo, {{
    style: function(feature) {{
        var nom = feature.properties.name;
        var pct = 0;
        if (data_carte[nom] && data_carte[nom][d]) {{
            pct = data_carte[nom][d];
        }}
        return {{
            fillColor: couleur_pays(pct),
            weight: 1,
            color: 'white',
            fillOpacity: 0.75
            }};
        }},
        onEachFeature: function(feature, layer) {{
            var nom = feature.properties.name;
            layer.on('click', function() {{
                console.log(nom);
                ouvrir_graphique(nom);
            }});
        layer.on('mouseover', function(e) {{
            var val = 'no data';
                if (data_carte[nom] && data_carte[nom][liste_dates[idx_courant]]) {{
                val = data_carte[nom][liste_dates[idx_courant]].toFixed(2) + '%';
            }}
            layer.bindTooltip(nom + ' : ' + val, {{sticky:true}}).openTooltip(e.latlng);
        }});
    }}
}}).addTo(carte);
}}

var graph_sir = null;

// ouvre le popup avec la courbe sir du pays
function ouvrir_graphique(nom) {{
var data = sir_par_pays[nom];
    document.getElementById('popup-titre').innerText = nom;
    document.getElementById('popup').style.display = 'block';

//faut detruire le chart avant d'en refaire un sinon ca marche pas
if (graph_sir) {{
    graph_sir.destroy();
}}

var ctx = document.getElementById('popup-graph').getContext('2d');
    graph_sir = new Chart(ctx, {{
    type: 'line',
        data: {{
        labels: data.dates,
        datasets: [
        {{label: 'Infectes', data: data.I, borderColor: 'red', fill: false, pointRadius: 0}},
        {{label: 'Retablis', data: data.R, borderColor: 'green', fill: false, pointRadius: 0}},
        {{label: 'Susceptibles', data: data.S, borderColor: 'blue', fill: false, pointRadius: 0}}
        ]
    }},
    options: {{ animation: false, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
}}

function set_idx(v)
{{
idx_courant = parseInt(v);
    maj_carte(idx_courant);
}}

// fait pause a la simulation quand on clique sur play/pause
function jouer()
{{
if (minuterie) {{
    clearInterval(minuterie);
    minuterie = null;
}}
else {{
    minuterie = setInterval(function() {{
    idx_courant++;
        if (idx_courant >= nb_dates) {{
        clearInterval(minuterie);
            minuterie = null;
        return;
        }}
    set_idx(idx_courant);
    }}, 200);
}}
}}

//faut mettre le max sinon le curseur marche pas
document.getElementById('curseur').max = nb_dates - 1;
maj_carte(0);

</script>
</body>
</html>"""
    Path(fichier_sortie).write_text(html, encoding="utf-8")


def out(p):
    webbrowser.open(Path(p).resolve().as_uri())