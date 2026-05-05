import pandas as pd
import numpy as np

data_folder = "../data"

def get_epi(p=None):
    if p is None:
        p = data_folder + "/epidemie.csv"
    df = pd.read_csv(p)

    #code iso for the win
    cols = {"Entity": "pays", "Code": "code", "Day": "date"}
    for c in df.columns:
        low = c.lower()
        if "death" in low and "cumulative" in low:
            cols[c] = "deces_cum"
        if "cases" in low and "cumulative" in low:
            cols[c] = "cas_cum"

    df = df.rename(columns=cols)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # sans code iso = agrégats régionaux (genre "Europe"), on veut pas ça
    df = df[df["code"].notna() & (df["code"] != "")]
    return df.sort_values(["pays", "date"]).fillna(0)


def get_pop(p=None, codes=None):
    if p is None:
        p = data_folder + "/population.csv"
    df = pd.read_csv(p)

    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns={"country name": "pays", "country code": "code", "value": "pop"})

    if codes:
        df = df[df["code"].isin(codes)]

    # prend la dernière année dispo par pays
    df = df.sort_values("year").groupby("code").last().reset_index()

    # si un pays a plusieurs codes on garde le plus peuplé
    df = df.sort_values("pop", ascending=False).groupby("pays").first().reset_index()

    df["pop"] = pd.to_numeric(df["pop"], errors="coerce").fillna(0)

    return df[["pays", "code", "pop"]]


def calc_sir(df, g=0.1):
    # repart des cas cumulés pour refaire I et R
    # g=0.1 = environ 10 jours de maladie, semble ok pour covid

    out = []
    for pays, grp in df.groupby("pays"):
        grp = grp.sort_values("date").copy()
        N = float(grp["population"].iloc[0])
        if N <= 0:
            continue

        cum = grp["cas_cum"].values.astype(float)
        nouveaux = np.diff(cum, prepend=cum[0])
        nouveaux = np.clip(nouveaux, 0, None)  # corrections négatives -> on ignore

        I = np.zeros(len(grp))
        R = np.zeros(len(grp))
        I[0] = cum[0]
        R[0] = grp["deces_cum"].iloc[0]  # TODO: R devrait être guéris pas décès, mais on a pas les données

        for k in range(1, len(grp)):
            gueris = g * I[k-1]
            I[k] = max(0.0, I[k-1] + nouveaux[k] - gueris)
            R[k] = min(R[k-1] + gueris, N - I[k])

        grp["I"] = I
        grp["R"] = R
        grp["S"] = np.clip(N - I - R, 0, N)
        out.append(grp)

    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True)


# flemme de changer partout
run_sir = calc_sir