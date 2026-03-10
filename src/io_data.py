import pandas as pd
import numpy as np
from pathlib import Path

# remonte le dossier de un pour avoir les datas
BASE = Path(__file__).resolve().parents[1] / "data"


def get_epi(p=None):
    p = p or (BASE / "epidemie.csv")
    df = pd.read_csv(p)

    # clean des noms de colonnes du csv qui sont chiant
    cols = {
        "Entity": "country", "Code": "code", "Day": "date"
    }
    for c in df.columns:
        low = c.lower()
        if "death" in low and "cumulative" in low: cols[c] = "cum_deaths"
        if "cases" in low and "cumulative" in low: cols[c] = "cum_cases"

    df = df.rename(columns=cols)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # enleve les lignes vides et les agrégats régionaux (pas de code ISO)
    df = df[df["code"].notna() & (df["code"] != "")]
    return df.sort_values(["country", "date"]).fillna(0)


def get_pop(p=None, codes=None):
    p = p or (BASE / "population.csv")
    df = pd.read_csv(p)

    # normalise les colonnes (World Bank style)
    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns={"country code": "code", "value": "pop"})

    # On garde que les pays qu'on a dans le fichier épidémie
    if codes:
        df = df[df["code"].isin(codes)]

    # prend juste la ligne la plus récente
    df = df.sort_values("year").groupby("code").last().reset_index()
    return df[["code", "pop"]]  # NOTE: merge sur 'code', plus sur 'country'


def run_sir(df, g=0.1):
    res = []
    for c, g_df in df.groupby("country"):
        g_df = g_df.sort_values("date").copy()
        n = float(g_df["population"].iloc[0])

        c_cases = g_df["cum_cases"].values
        # Diff pour avoir les nouveaux par jour
        new = np.diff(c_cases, prepend=c_cases[0])
        new[new < 0] = 0

        i, r = np.zeros(len(g_df)), np.zeros(len(g_df))
        i[0], r[0] = c_cases[0], g_df["cum_deaths"].iloc[0]

        for k in range(1, len(g_df)):
            recov = g * i[k - 1]
            i[k] = max(0, i[k - 1] + new[k] - recov)
            r[k] = min(r[k - 1] + recov, n - i[k])

        g_df["I"], g_df["R"] = i, r
        g_df["S"] = n - i - r
        res.append(g_df)
    return pd.concat(res)