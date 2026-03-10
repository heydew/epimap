import json
import webbrowser
from pathlib import Path


def plot_sir_animated(data, title, out_html):

    data   = data.sort_values("date").reset_index(drop=True)
    dates  = [str(d)[:10] for d in data["date"]]
    I_raw  = data["I"].rolling(window=10, min_periods=1, center=True).mean()
    I      = [round(float(v)) for v in I_raw]

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>""" + title + """</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
    body { margin: 20px; font-family: monospace; background: white; }
    #controls { margin-top: 8px; display: flex; align-items: center; gap: 8px; }
    input[type=range] { flex: 1; }
</style>
</head>
<body>

<p id="infos">--</p>
<canvas id="c"></canvas>
<div id="controls">
    <button id="playpause">play</button>
    <input type="range" id="slider" min="0" value="0">
    <select id="vitesse">
        <option value="80">lent</option>
        <option value="25" selected>normal</option>
        <option value="6">rapide</option>
    </select>
</div>

<script>

var DATES = """ + json.dumps(dates) + """;
var I     = """ + json.dumps(I) + """;

var peakI   = Math.max(...I);
var peakIdx = I.indexOf(peakI);

var chart = new Chart(document.getElementById('c').getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'I infectes',
                data: [],
                borderColor: '#c0392b',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1,
                fill: true,
                backgroundColor: 'rgba(192,57,43,0.08)'
            }
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
            }}},
            annotation: {}
        }
    },
    plugins: [{
        id: 'peak-line',
        afterDraw: function(chart) {
            var ctx = chart.ctx;
            var currentLen = chart.data.labels.length;
            if (currentLen <= peakIdx) return;

            var meta = chart.getDatasetMeta(0);
            if (!meta.data[peakIdx]) return;

            var x = meta.data[peakIdx].x;
            var topY = chart.chartArea.top;
            var botY = chart.chartArea.bottom;

            ctx.save();
            ctx.setLineDash([4, 4]);
            ctx.strokeStyle = 'rgba(192,57,43,0.45)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, topY);
            ctx.lineTo(x, botY);
            ctx.stroke();

            ctx.setLineDash([]);
            ctx.fillStyle = '#c0392b';
            ctx.font = '11px Courier New';
            ctx.fillText('pic: ' + Math.round(peakI).toLocaleString(), x + 5, topY + 14);
            ctx.restore();
        }
    }]
});


function afficher(idx) {
    chart.data.labels           = DATES.slice(0, idx+1);
    chart.data.datasets[0].data = I.slice(0, idx+1);
    chart.update('none');

    document.getElementById('slider').value = idx;
    document.getElementById('infos').textContent =
        DATES[idx] + '   I infectes: ' + I[idx].toLocaleString();
}


var idx      = 0;
var en_cours = false;
var timer    = null;

var slider  = document.getElementById('slider');
var btn     = document.getElementById('playpause');
var vitesse = document.getElementById('vitesse');

slider.max = DATES.length - 1;
afficher(0);


function stop() {
    en_cours = false;
    clearInterval(timer); timer = null;
    btn.textContent = 'play';
}

function play() {
    if (idx >= DATES.length - 1) idx = 0;
    en_cours = true;
    btn.textContent = 'pause';
    timer = setInterval(function() {
        idx++;
        afficher(idx);
        if (idx >= DATES.length - 1) stop();
    }, parseInt(vitesse.value));
}


btn.addEventListener('click', function() { en_cours ? stop() : play(); });

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