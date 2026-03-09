import json
import webbrowser
from pathlib import Path


def plot_sir_animated(data, title, out_html):

    data   = data.sort_values("date").reset_index(drop=True)
    dates  = [str(d)[:10] for d in data["date"]]
    S      = [round(float(v)) for v in data["S"]]
    I      = [round(float(v)) for v in data["I"]]
    R      = [round(float(v)) for v in data["R"]]

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>""" + title + """</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
    body {
        margin: 0;
        padding: 20px 30px;
        font-family: 'Courier New', monospace;
        background: #f5f2eb;
    }

    h2 {
        font-size: 15px;
        font-weight: normal;
        color: #444;
        border-bottom: 1px solid #ccc;
        padding-bottom: 6px;
        margin-bottom: 16px;
    }

    #wrap {
        background: white;
        border: 1px solid #bbb;
        padding: 16px;
        max-width: 900px;
    }

    #controls {
        max-width: 900px;
        margin-top: 10px;
        display: flex; flex-direction: column; gap: 7px;
    }

    #infos { font-size: 12px; color: #666; }

    #row {
        display: flex; align-items: center; gap: 10px;
    }

    input[type=range] { flex: 1; accent-color: #555; cursor: pointer; }

    button {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        background: white; border: 1px solid #888;
        padding: 4px 12px; cursor: pointer;
    }
    button:hover { background: #ebebeb; }

    select {
        font-family: 'Courier New', monospace;
        font-size: 12px; border: 1px solid #888;
        background: white; padding: 3px 6px; cursor: pointer;
    }
</style>
</head>
<body>

<h2>""" + title + """</h2>

<div id="wrap">
    <canvas id="c"></canvas>
</div>

<div id="controls">
    <div id="infos">--</div>
    <div id="row">
        <button id="restart">|&lt;</button>
        <button id="playpause">&gt; play</button>
        <input type="range" id="slider" min="0" value="0">
        <select id="vitesse">
            <option value="80">lent</option>
            <option value="25" selected>normal</option>
            <option value="6">rapide</option>
        </select>
    </div>
</div>

<script>

var DATES = """ + json.dumps(dates) + """;
var S     = """ + json.dumps(S) + """;
var I     = """ + json.dumps(I) + """;
var R     = """ + json.dumps(R) + """;

var chart = new Chart(document.getElementById('c').getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {label:'S susceptibles', data:[], borderColor:'#4a90d9', borderWidth:2, pointRadius:0, tension:0.1, fill:false},
            {label:'I infectes',     data:[], borderColor:'#c0392b', borderWidth:2, pointRadius:0, tension:0.1, fill:false},
            {label:'R retires',      data:[], borderColor:'#27ae60', borderWidth:2, pointRadius:0, tension:0.1, fill:false}
        ]
    },
    options: {
        animation: false,
        responsive: true,
        interaction: {mode:'index', intersect:false},
        scales: {
            x: {
                ticks: {maxTicksLimit:10, font:{family:'Courier New', size:11}, maxRotation:30},
                grid:  {color:'#eee'}
            },
            y: {
                ticks: {
                    font: {family:'Courier New', size:11},
                    callback: function(v) {
                        if (v >= 1e9) return (v/1e9).toFixed(1)+'G';
                        if (v >= 1e6) return (v/1e6).toFixed(1)+'M';
                        if (v >= 1e3) return (v/1e3).toFixed(0)+'k';
                        return v;
                    }
                },
                grid: {color:'#eee'}
            }
        },
        plugins: {
            legend: {labels: {font:{family:'Courier New', size:12}, boxWidth:18}},
            tooltip: {callbacks: {label: function(c) {
                return c.dataset.label + ': ' + Math.round(c.parsed.y).toLocaleString();
            }}}
        }
    }
});


function afficher(idx) {
    chart.data.labels           = DATES.slice(0, idx+1);
    chart.data.datasets[0].data = S.slice(0, idx+1);
    chart.data.datasets[1].data = I.slice(0, idx+1);
    chart.data.datasets[2].data = R.slice(0, idx+1);
    chart.update('none');

    document.getElementById('slider').value = idx;
    document.getElementById('infos').textContent =
        DATES[idx] + '   S:' + S[idx].toLocaleString() +
        '  I:' + I[idx].toLocaleString() +
        '  R:' + R[idx].toLocaleString();
}


var idx     = 0;
var en_cours = false;
var timer   = null;

var slider   = document.getElementById('slider');
var btn      = document.getElementById('playpause');
var vitesse  = document.getElementById('vitesse');

slider.max = DATES.length - 1;
afficher(0);


function stop() {
    en_cours = false;
    clearInterval(timer); timer = null;
    btn.textContent = '> play';
}

function play() {
    if (idx >= DATES.length - 1) idx = 0;
    en_cours = true;
    btn.textContent = '|| pause';
    timer = setInterval(function() {
        idx++;
        afficher(idx);
        if (idx >= DATES.length - 1) stop();
    }, parseInt(vitesse.value));
}


btn.addEventListener('click', function() { en_cours ? stop() : play(); });

document.getElementById('restart').addEventListener('click', function() {
    stop(); idx = 0; afficher(0);
});

slider.addEventListener('input', function() {
    stop(); idx = parseInt(slider.value); afficher(idx);
});

vitesse.addEventListener('change', function() {
    if (en_cours) { stop(); play(); }
});

</script>
</body>
</html>"""

    Path(out_html).write_text(html, encoding="utf-8")
    print("graphique -> " + out_html)


def out(html_path):
    import webbrowser
    webbrowser.open(Path(html_path).resolve().as_uri())