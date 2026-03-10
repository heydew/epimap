import json
import webbrowser
from pathlib import Path


def plot_sir_animated(data, titre, out_html):
# tri par date
    df = data.sort_values("date")
    dates = [str(d)[:10] for d in df["date"]]

# Smooth la courbe sinn c laid
    infectes = df["I"].rolling(7).mean().fillna(0).astype(int).tolist()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>COURBES INFECTES</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        canvas {{ max-height: 500px; }}
        .ctrls {{ margin-top: 15px; display: flex; gap: 10px; align-items: center; }}
    </style>
</head>
<body>
    <h3>{titre}</h3>
    <p id="txt">Chargement...</p>
    <canvas id="chart"></canvas>

    <div class="ctrls">
        <button onclick="play()">Play/Pause</button>
        <input type="range" id="tick" style="flex:1" oninput="set_idx(this.value)">
    </div>

    <script>
        const D = {json.dumps(dates)};
        const V = {json.dumps(infectes)};
        let idx = 0, timer = null;

        const ctx = document.getElementById('chart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{ labels: [], datasets: [{{ label: 'I', data: [], borderColor: 'red', fill: false }}] }},
            options: {{ animation: false, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        function set_idx(v) {{
            idx = parseInt(v);
            document.getElementById('txt').innerText = D[idx] + " - Infectés: " + V[idx].toLocaleString();
            chart.data.labels = D.slice(0, idx + 1);
            chart.data.datasets[0].data = V.slice(0, idx + 1);
            chart.update();
        }}

        function play() {{
            if(timer) {{ clearInterval(timer); timer = null; }}
            else {{
                timer = setInterval(() => {{
                    idx++;
                    if(idx >= D.length) {{ clearInterval(timer); timer = null; return; }}
                    document.getElementById('tick').value = idx;
                    set_idx(idx);
                }}, 50);
            }}
        }}

        document.getElementById('tick').max = D.length - 1;
        set_idx(0);
    </script>
</body>
</html>
"""
    Path(out_html).write_text(html, encoding="utf-8")
    print(f" le graphique: {out_html}")


def out(p):
    webbrowser.open(Path(p).resolve().as_uri())