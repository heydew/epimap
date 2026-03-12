import pandas as pd
import numpy as np



DOSSIER_DATA = "../data"


def get_epi(p=None):
    if p is None:
        p = DOSSIER_DATA + "/epidemie.csv"
    df = pd.read_csv(p)




 # ptit rename des colones pour que ca soit moins chianr
    colonnes = {
        "Entity": "pays", "Code": "code", "Day": "date"
    }
    for c in df.columns:
        minuscule = c.lower()
        if "death" in minuscule and "cumulative" in minuscule: colonnes[c] = "deces_cum"
        if "cases" in minuscule and "cumulative" in minuscule: colonnes[c] = "cas_cum"

    df = df.rename(columns=colonnes)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

 # enleve les trucs genre afrique, europe etc(si ya pas de code ISO c pas un vrai pays)
    df = df[df["code"].notna() & (df["code"] != "")]
    return df.sort_values(["pays", "date"]).fillna(0)

def get_pop(p=None, codes=None):
    if p is None:
        p = DOSSIER_DATA + "/population.csv"
    df = pd.read_csv(p)

    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns={"country code": "code", "value": "pop"})

    if codes:
        df = df[df["code"].isin(codes)]

# derniere annee dispo par pays
    df = df.sort_values("year").groupby("code").last().reset_index()
    return df[["code", "pop"]]



def run_sir(df, g=0.1):  # g = estimation de temps guerison(10j)
    resultats = []
    for pays, groupe in df.groupby("pays"):
        groupe = groupe.sort_values("date").copy()
        nb_pop = float(groupe["population"].iloc[0])

        cas_cumules = groupe["cas_cum"].values
        nouveaux = np.diff(cas_cumules, prepend=cas_cumules[0])
        nouveaux[nouveaux < 0] = 0

        infectes = np.zeros(len(groupe))
        retablis = np.zeros(len(groupe))
        infectes[0] = cas_cumules[0]
        retablis[0] = groupe["deces_cum"].iloc[0]

        for k in range(1, len(groupe)):
            gueris = g * infectes[k - 1]
            infectes[k] = max(0, infectes[k - 1] + nouveaux[k] - gueris)
            retablis[k] = min(retablis[k - 1] + gueris, nb_pop - infectes[k])


        groupe["I"] = infectes
        groupe["R"] = retablis
        groupe["S"] = nb_pop - infectes - retablis
        resultats.append(groupe)


    return pd.concat(resultats)