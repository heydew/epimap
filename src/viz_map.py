from __future__ import annotations
import json
import os
import webbrowser
from pathlib import Path

import folium
import pandas as pd


COUNTRY_NAME_MAP = {
    "United States":                      "United States of America",
    "USA":                                "United States of America",
    "US":                                 "United States of America",
    "Congo":                              "Republic of the Congo",
    "Democratic Republic of Congo":       "Democratic Republic of the Congo",
    "DR Congo":                           "Democratic Republic of the Congo",
    "Czechia":                            "Czech Republic",
    "Timor":                              "East Timor",
    "Timor-Leste":                        "East Timor",
    "Cote d'Ivoire":                      "Ivory Coast",
    "Cape Verde":                         "Cabo Verde",
    "Swaziland":                          "eSwatini",
    "North Macedonia":                    "Macedonia",
    "Burma":                              "Myanmar",
    "Korea, South":                       "South Korea",
    "Korea, North":                       "North Korea",
    "Russian Federation":                 "Russia",
    "Iran (Islamic Republic of)":         "Iran",
    "Syrian Arab Republic":               "Syria",
    "Tanzania":                           "United Republic of Tanzania",
    "Viet Nam":                           "Vietnam",
    "Bolivia (Plurinational State of)":   "Bolivia",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
    "Lao People's Democratic Republic":   "Laos",
    "Palestinian Territory":              "West Bank",
    "Guinea-Bissau":                      "Guinea Bissau",
}

def _norm(name: str) -> str:
    return COUNTRY_NAME_MAP.get(name, name)


def _load_geojson(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"geojson introuvable: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _color(pct: float) -> str:
    if not pct or pct <= 0: return "#f0ece4"
    if pct < 0.001: return "#f7d9c4"
    if pct < 0.01:  return "#f0aa80"
    if pct < 0.05:  return "#e07840"
    if pct < 0.1:   return "#c85020"
    if pct < 0.5:   return "#a03010"
    if pct < 1.0:   return "#7a1e08"
    if pct < 2.0:   return "#5a1005"
    return "#3a0800"


def choropleth_timelapse(
    data_sir: pd.DataFrame,
    geojson_path: str,
    out_html: str,
    date_step: str = "MS",
    key_prop: str = "name",
) -> None:
    geo = _load_geojson(geojson_path)

    df = data_sir.copy()
    df["country_geo"] = df["country"].apply(_norm)
    df["pct"] = (df["I"] / df["population"] * 100).clip(0, 100).round(4)

    all_dates = pd.date_range(df["date"].min(), df["date"].max(), freq=date_step)

    pivot = (
        df.groupby(["date", "country_geo"])["pct"]
        .mean().reset_index()
        .pivot(index="date", columns="country_geo", values="pct")
        .reindex(all_dates, method="ffill")
    )

    frames_data: dict = {}
    for date in all_dates:
        ds = date.strftime("%Y-%m")
        frames_data[ds] = {}
        for country in pivot.columns:
            if date in pivot.index:
                v = pivot.loc[date, country]
                frames_data[ds][country] = float(v) if pd.notna(v) else 0.0

    date_labels = list(frames_data.keys())
    base_features = [
        {"name": f["properties"].get(key_prop, ""), "geometry": f["geometry"]}
        for f in geo["features"]
    ]

    frames_json   = json.dumps(frames_data,   ensure_ascii=False)
    base_geo_json = json.dumps(base_features, ensure_ascii=False)
    dates_json    = json.dumps(date_labels)

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>timelapse epidemie</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Courier New', monospace; background: #f5f2eb; }
    #map { width: 100vw; height: calc(100vh - 90px); }

    #controls {
        position: fixed; bottom: 0; left: 0; right: 0; height: 90px;
        background: #f5f2eb;
        border-top: 1px solid #bbb;
        display: flex; align-items: center;
        gap: 12px; padding: 0 24px;
        z-index: 9999;
    }
    #date-display {
        font-size: 14px; color: #333; width: 80px; flex-shrink: 0;
    }
    #slider {
        flex: 1; cursor: pointer; accent-color: #555;
    }
    button {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        background: white; border: 1px solid #888;
        padding: 5px 14px; cursor: pointer; color: #222;
        flex-shrink: 0;
    }
    button:hover { background: #e8e8e8; }
    select {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        border: 1px solid #888; padding: 4px 8px;
        background: white; cursor: pointer;
        flex-shrink: 0;
    }

    #legend {
        position: absolute; top: 12px; right: 12px; z-index: 9000;
        background: rgba(245,242,235,0.95);
        border: 1px solid #bbb;
        padding: 10px 14px; font-size: 12px;
        font-family: 'Courier New', monospace;
        line-height: 1.9;
    }
    .lr { display: flex; align-items: center; gap: 7px; }
    .lb { width: 16px; height: 14px; border: 1px solid #ccc; flex-shrink: 0; }
</style>
</head>
<body>
<div id="map"></div>
<div id="controls">
    <span id="date-display">--</span>
    <button id="btn-restart">|&lt;</button>
    <button id="btn-play">&gt; play</button>
    <input type="range" id="slider" min="0" value="0">
    <select id="speed-select">
        <option value="1200">lent</option>
        <option value="500" selected>normal</option>
        <option value="200">rapide</option>
        <option value="60">tres rapide</option>
    </select>
</div>

<div id="legend">
    % infectes<br>
    <div class="lr"><div class="lb" style="background:#f0ece4"></div> 0%</div>
    <div class="lr"><div class="lb" style="background:#f7d9c4"></div> &lt;0.001%</div>
    <div class="lr"><div class="lb" style="background:#e07840"></div> 0.05%</div>
    <div class="lr"><div class="lb" style="background:#a03010"></div> 0.5%</div>
    <div class="lr"><div class="lb" style="background:#3a0800"></div> &gt;2%</div>
    <div class="lr"><div class="lb" style="background:#ccc"></div> n/a</div>
</div>

<script>
const FRAMES   = """ + frames_json + """;
const BASE_GEO = """ + base_geo_json + """;
const DATES    = """ + dates_json + """;

const map = L.map('map').setView([20, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors', maxZoom: 18
}).addTo(map);

function color(pct) {
    if (!pct || pct <= 0) return '#f0ece4';
    if (pct < 0.001) return '#f7d9c4';
    if (pct < 0.01)  return '#f0aa80';
    if (pct < 0.05)  return '#e07840';
    if (pct < 0.1)   return '#c85020';
    if (pct < 0.5)   return '#a03010';
    if (pct < 1.0)   return '#7a1e08';
    if (pct < 2.0)   return '#5a1005';
    return '#3a0800';
}

const geojsonData = {
    type: 'FeatureCollection',
    features: BASE_GEO.map(f => ({
        type: 'Feature', geometry: f.geometry,
        properties: { name: f.name, pct: undefined }
    }))
};

const geoLayer = L.geoJSON(geojsonData, {
    style: f => ({
        fillColor: color(f.properties.pct),
        fillOpacity: 0.75, color: '#999', weight: 0.5
    }),
    onEachFeature: (feature, layer) => {
        layer.bindTooltip(() => {
            const p = feature.properties.pct;
            const s = (p !== undefined && p > 0) ? p.toFixed(3) + '%' : 'aucun cas';
            return feature.properties.name + ' : ' + s;
        }, { sticky: true });
    }
}).addTo(map);

function applyFrame(idx) {
    const ds   = DATES[idx];
    const data = FRAMES[ds] || {};
    document.getElementById('date-display').textContent = ds;
    document.getElementById('slider').value = idx;
    geoLayer.eachLayer(layer => {
        const name = layer.feature.properties.name;
        const pct  = data[name];
        layer.feature.properties.pct = pct;
        layer.setStyle({
            fillColor: (pct !== undefined && pct > 0) ? color(pct) : '#ccc',
            fillOpacity: 0.75
        });
    });
}

let idx = 0, playing = false, timer = null;
const slider  = document.getElementById('slider');
const btnPlay = document.getElementById('btn-play');
const speed   = document.getElementById('speed-select');
slider.max = DATES.length - 1;
applyFrame(0);

function stop() {
    playing = false; clearInterval(timer); timer = null;
    btnPlay.textContent = '> play';
}
function play() {
    if (idx >= DATES.length - 1) idx = 0;
    playing = true; btnPlay.textContent = '|| pause';
    timer = setInterval(() => {
        idx++; applyFrame(idx);
        if (idx >= DATES.length - 1) stop();
    }, parseInt(speed.value));
}

btnPlay.addEventListener('click', () => playing ? stop() : play());
document.getElementById('btn-restart').addEventListener('click', () => { stop(); idx = 0; applyFrame(0); });
slider.addEventListener('input', () => { stop(); idx = parseInt(slider.value); applyFrame(idx); });
speed.addEventListener('change', () => { if (playing) { stop(); play(); } });
</script>
</body>
</html>"""

    Path(out_html).write_text(html, encoding="utf-8")
    print(f"[viz] -> {out_html}")


def out(html_path: str) -> None:
    path = Path(html_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"introuvable: {path}")
    webbrowser.open(path.as_uri())