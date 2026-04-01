import json
import webbrowser
from pathlib import Path


def plot_sir_animated(data, titre, out_html):
    """Courbes SIR animées pour le pipeline COVID réel."""
    df = data.sort_values("date")
    dates = [str(d)[:10] for d in df["date"]]

    # lissage 7 jours
    infectes = df["I"].rolling(7, min_periods=1).mean().fillna(0).astype(int).tolist()

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Courbes infectés</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        canvas {{ max-height: 500px; }}
        .ctrls {{ margin-top: 15px; display: flex; gap: 10px; align-items: center; }}
        button {{ padding: 5px 14px; cursor: pointer; }}
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
            data: {{ labels: [], datasets: [{{ label: 'Infectés', data: [], borderColor: 'red', fill: false, pointRadius: 0 }}] }},
            options: {{ animation: false, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        function set_idx(v) {{
            idx = parseInt(v);
            document.getElementById('txt').innerText = D[idx] + " — Infectés: " + V[idx].toLocaleString();
            chart.data.labels = D.slice(0, idx + 1);
            chart.data.datasets[0].data = V.slice(0, idx + 1);
            chart.update('none');
        }}

        function play() {{
            if (timer) {{ clearInterval(timer); timer = null; }}
            else {{
                timer = setInterval(() => {{
                    idx++;
                    if (idx >= D.length) {{ clearInterval(timer); timer = null; return; }}
                    document.getElementById('tick').value = idx;
                    set_idx(idx);
                }}, 50);
            }}
        }}

        document.getElementById('tick').max = D.length - 1;
        set_idx(0);
    </script>
</body>
</html>"""
    Path(out_html).write_text(html, encoding="utf-8")
    print(f"Graphique exporté : {out_html}")


def tracer_seirdv(world_df, titre, out_html):
    """Courbes SEIRD+V animées pour le pipeline simulation."""
    df = world_df.sort_values("date")
    dates = [str(d)[:10] for d in df["date"]]

    # FIXE: lisser() était appelée avant d'être définie dans la version originale
    def lisser(col):
        return df[col].rolling(7, min_periods=1).mean().fillna(0).astype(int).tolist()

    E = lisser("E")
    I = lisser("I")
    R = lisser("R")
    D = lisser("D")
    V = lisser("V") if "V" in df.columns else [0] * len(df)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Courbes {titre}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        canvas {{ max-height: 500px; }}
        .ctrls {{ margin-top: 15px; display: flex; gap: 10px; align-items: center; }}
        button {{ padding: 5px 14px; cursor: pointer; }}
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
        const D  = {json.dumps(dates)};
        const vE = {json.dumps(E)};
        const vI = {json.dumps(I)};
        const vR = {json.dumps(R)};
        const vD = {json.dumps(D)};
        const vV = {json.dumps(V)};
        let idx = 0, timer = null;

        const ctx = document.getElementById('chart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: [],
                datasets: [
                    {{ label: 'E (Exposés)',   data: [], borderColor: 'orange',    fill: false, pointRadius: 0 }},
                    {{ label: 'I (Infectés)',  data: [], borderColor: 'red',       fill: false, pointRadius: 0 }},
                    {{ label: 'R (Rétablis)', data: [], borderColor: 'green',     fill: false, pointRadius: 0 }},
                    {{ label: 'D (Décès)',    data: [], borderColor: 'purple',    fill: false, pointRadius: 0 }},
                    {{ label: 'V (Vaccinés)', data: [], borderColor: 'teal',      fill: false, pointRadius: 0 }},
                ]
            }},
            options: {{ animation: false, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        function set_idx(v) {{
            idx = parseInt(v);
            document.getElementById('txt').innerText = D[idx]
                + "  E:" + vE[idx].toLocaleString()
                + "  I:" + vI[idx].toLocaleString()
                + "  R:" + vR[idx].toLocaleString()
                + "  D:" + vD[idx].toLocaleString()
                + "  V:" + vV[idx].toLocaleString();
            chart.data.labels = D.slice(0, idx + 1);
            chart.data.datasets[0].data = vE.slice(0, idx + 1);
            chart.data.datasets[1].data = vI.slice(0, idx + 1);
            chart.data.datasets[2].data = vR.slice(0, idx + 1);
            chart.data.datasets[3].data = vD.slice(0, idx + 1);
            chart.data.datasets[4].data = vV.slice(0, idx + 1);
            chart.update('none');
        }}

        function play() {{
            if (timer) {{ clearInterval(timer); timer = null; }}
            else {{
                timer = setInterval(() => {{
                    idx++;
                    if (idx >= D.length) {{ clearInterval(timer); timer = null; return; }}
                    document.getElementById('tick').value = idx;
                    set_idx(idx);
                }}, 50);
            }}
        }}

        document.getElementById('tick').max = D.length - 1;
        set_idx(0);
    </script>
</body>
</html>"""
    Path(out_html).write_text(html, encoding="utf-8")
    print(f"Courbes exportées : {out_html}")


def out(p):
    webbrowser.open(Path(p).resolve().as_uri())