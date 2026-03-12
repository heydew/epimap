import json
import webbrowser
from pathlib import Path


def plot_sir_anime(donnees, titre, fichier_html):
# tri par date
    df = donnees.sort_values("date")
    liste_dates = [str(d)[:10] for d in df["date"]]

# smooth la courbe sinn c laid
    nb_infectes = df["I"].rolling(7).mean().fillna(0).astype(int).tolist()

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>COURBES INFECTES</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {{ font-family: Arial; margin: 20px; }}
canvas {{ max-height: 500px; }}
.ctrls {{ margin-top: 15px; display: flex; gap: 10px; align-items: center; }}
</style>
</head>
<body>

<h3>{titre}</h3>
<p id="txt"></p>
<canvas id="graphique"></canvas>

<div class="ctrls">
    <button onclick="jouer()">Play/Pause</button>
    <input type="range" id="curseur" style="flex:1" oninput="set_idx(this.value)">
</div>

<script>

//on nomme nos variables 
var dates = {json.dumps(liste_dates)};
var valeurs = {json.dumps(nb_infectes)};
var nb_dates = dates.length;
var idx = 0;
var en_train_de_jouer = false;
var minuterie = null;

// creation graphique avk Chart.js
var ctx = document.getElementById('graphique').getContext('2d');
var graphique = new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: [],
      datasets: [{{
      label: 'Infectes',
      data: [],
      borderColor: 'red',
      fill: false
    }}]
  }},
  options: {{
    animation: false,
        scales: {{ y: {{ beginAtZero: true }} }}
  }}
}});

// met a jour le graphique quand on bouge la souris
function set_idx(v) {{
idx = parseInt(v);
  console.log('idx: ' + idx);
  document.getElementById('txt').innerText = dates[idx] + " - infectes: " + valeurs[idx];
  graphique.data.labels = dates.slice(0, idx + 1);
    graphique.data.datasets[0].data = valeurs.slice(0, idx + 1);
  graphique.update();
}}

//arrete la simulation quand on appuie sur play/pause
function jouer()
{{
  if (minuterie) {{
    clearInterval(minuterie);
      minuterie = null;
  }}
  else {{
    minuterie = setInterval(function() {{
      idx++;
      if (idx >= nb_dates) {{
          clearInterval(minuterie);
          minuterie = null;
          return;
      }}
        document.getElementById('curseur').value = idx;
      set_idx(idx);
    }}, 50);
  }}
}}

// faut mettre le max du range sinon ca marche pas
document.getElementById('curseur').max = nb_dates - 1;
set_idx(0);

</script>
</body>
</html>
"""
    Path(fichier_html).write_text(html, encoding="utf-8")
    print(f"le graphique infectés: {fichier_html}")


def out(p):
    webbrowser.open(Path(p).resolve().as_uri())