import math
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Dict, Tuple


# hubs = les gens voyagent plus depuis/vers là
#  plus gros aéroports mondiaux
gros_hubs = {
    "United States of America", "China", "United Kingdom", "Germany", "France",
    "United Arab Emirates", "Singapore", "Japan", "Netherlands", "Turkey"
}



def dist_km(c1, c2):
    # haversine = tient compte de la courbure de la terre
    R = 6371
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def extraire_coords(geom):
    t = geom.get("type", "")
    if t == "Polygon":
        return geom["coordinates"][0]
    elif t == "MultiPolygon":
        pts = []
        for poly in geom["coordinates"]:
            pts.extend(poly[0])
        return pts
    return []


def charger_centres(geojson_path):
    # centre de chaque pays = moyenne des coords du contour
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)

    res = {}
    for feat in geo["features"]:
        nom = feat["properties"].get("name", "")
        if not nom:
            continue
        coords = extraire_coords(feat["geometry"])
        if coords:
            lats = [c[1] for c in coords]
            lons = [c[0] for c in coords]
            res[nom] = (sum(lats)/len(lats), sum(lons)/len(lons))
    return res




@dataclass
class Maladie:
    nom: str
    r0: float
    jours_incubation: float
    jours_contagieux: float
    taux_mortalite: float
    pays_origine: str
    date_debut: str
    infectes_initiaux: int = 10
    vitesse_propagation: float = 0.3


class Simulation:

    def __init__(self, maladie, pop_df, geojson_path):
        self.cfg = maladie
        self.pop_df = pop_df.copy()
        self.pays = list(pop_df["pays"].unique())

        self.sigma = 1.0 / maladie.jours_incubation
        self.gamma = 1.0 / maladie.jours_contagieux

        self.centres = charger_centres(geojson_path)
        self.build_connexions()
        self.init_etats()

        self.beta_override = {p: None for p in self.pays}
        self.taux_vaccination = {p: 0.0 for p in self.pays}

    def build_connexions(self):
        #score de propagation basé sur distance
        # valeur 5000 dans score trouvée par essai/erreur, donne des résultats qui semblent ok
        self.conn = {}
        for p1 in self.pays:
            self.conn[p1] = {}
            c1 = self.centres.get(p1)
            for p2 in self.pays:
                if p1 == p2:
                    self.conn[p1][p2] = 0.0
                    continue
                c2 = self.centres.get(p2)
                if c1 and c2:
                    d = dist_km(c1, c2)
                    score = math.exp(-d / 5000)
                else:
                    score = 0.01  # pays sans coords dans le geojson, valeur arbitraire
                bonus = 2.5 if (p1 in gros_hubs or p2 in gros_hubs) else 1.0
                self.conn[p1][p2] = score * bonus

        # normalise pour que la somme des poids = 1 par pays depart
        for p1 in self.pays:
            total = sum(self.conn[p1].values())
            if total > 0:
                for p2 in self.pays:
                    self.conn[p1][p2] /= total

    def init_etats(self):
        self.etats = {}
        for _, row in self.pop_df.iterrows():
            p = row["pays"]
            n = float(row["pop"])
            self.etats[p] = {"S": n, "E": 0.0, "I": 0.0, "R": 0.0, "D": 0.0, "V": 0.0, "pop": n}

        # patient zéro dans le pays d'origine
        origine = self.cfg.pays_origine
        if origine in self.etats:
            n = self.etats[origine]["pop"]
            i0 = min(self.cfg.infectes_initiaux, n)
            self.etats[origine]["I"] = i0
            self.etats[origine]["S"] = n - i0

    def get_beta(self, pays, date):
        base = self.cfg.r0 * self.gamma
        if self.beta_override[pays] is not None:
            base = self.beta_override[pays]  # confinement ou mesure sanitaire en cours
        return base

    def step_pays(self, pays, date):
        st = self.etats[pays]
        n = st["pop"]
        if n <= 0:
            return st

        S, E, I, R, D, V = st["S"], st["E"], st["I"], st["R"], st["D"], st["V"]

        # correction si les categories vont au dessus de N
        total = S + E + I + R + D + V
        if total > n and total > 0:
            f = n / total
            S *= f; E *= f; I *= f
            R *= f; D *= f; V *= f

        beta = self.get_beta(pays, date)

        new_exposes  = min(beta * S * I / n, S)
        new_infectes = min(self.sigma * E, E)
        new_retablis = min(self.gamma * (1 - self.cfg.taux_mortalite) * I, I)
        new_deces    = min(self.gamma * self.cfg.taux_mortalite * I, I - new_retablis)
        new_vaccines = min(self.taux_vaccination[pays] * S, max(S - new_exposes, 0))

        nE = max(E + new_exposes - new_infectes, 0)
        nI = max(I + new_infectes - new_retablis - new_deces, 0)
        nR = max(R + new_retablis, 0)
        nD = max(D + new_deces, 0)
        nV = max(V + new_vaccines, 0)
        nS = max(n - nE - nI - nR - nD - nV, 0)

        return {"S": nS, "E": nE, "I": nI, "R": nR, "D": nD, "V": nV, "pop": n}

    def propager(self, rng):
        seeds = {}
        n_pays = max(len(self.pays), 1)

        # ajoute un flux de voyage dans le monde pour que tlmd soit touché
        # 0.00005 psk testé avec 0.001 = trop rapide
        # avec 0.00001 = trop lent
        # 0.00005 donne 2-3 mois avant que tous les pays soient touché
        #TODO( peut etre ameliorer)
        taux_global = self.cfg.vitesse_propagation * 0.00005 / max(n_pays, 1)

        for p_src in self.pays:
            I_src = self.etats[p_src]["I"]
            if I_src < 1:
                continue
            n_src = self.etats[p_src]["pop"]

            taux = self.cfg.vitesse_propagation / (500 * n_pays)
            max_voy = max(2, n_src * 0.00005)  # envoie petite partie pop dans chaque pays
            voy = min(rng.poisson(max(I_src * taux, 0.1)), max_voy)
            if voy > 0:
                poids = np.array([self.conn[p_src].get(p2, 0) for p2 in self.pays])
                if poids.sum() > 0:
                    poids /= poids.sum()
                    dests = rng.choice(len(self.pays), size=int(voy), p=poids)
                    for idx in dests:
                        p_dst = self.pays[idx]
                        if p_dst != p_src and self.etats[p_dst]["S"] > 1:
                            seeds[p_dst] = seeds.get(p_dst, 0) + 1




            flux = I_src * taux_global
            if flux >= 0.01:
                for p_dst in self.pays:
                    if p_dst != p_src and self.etats[p_dst]["S"] > 1:
                        seeds[p_dst] = seeds.get(p_dst, 0) + flux

        for p_dst, n_seed in seeds.items():
            s = min(n_seed, self.etats[p_dst]["S"])
            if s <= 0:
                continue
            self.etats[p_dst]["S"] -= s
            self.etats[p_dst]["E"] += s

    def simuler(self, plage_dates, evenements, graine=42):
        rng = np.random.default_rng(graine)
        date_debut = pd.Timestamp(self.cfg.date_debut)
        rows = []




        # si la pop totale dépasse 15 milliards c'est qu'il y a des erreurs (a corriger vite fait)
        # on rescale à ~8 milliards (pop mondiale réelle)
        pop_tot = sum(self.etats[p]["pop"] for p in self.pays)
        if pop_tot > 15_000_000_000:
            f = 8_000_000_000 / pop_tot
            for p in self.pays:
                n = self.etats[p]["pop"] * f
                self.etats[p] = {"S": n, "E": 0, "I": 0, "R": 0, "D": 0, "V": 0, "pop": n}
            if self.cfg.pays_origine in self.etats:
                n = self.etats[self.cfg.pays_origine]["pop"]
                i0 = min(self.cfg.infectes_initiaux, n)
                self.etats[self.cfg.pays_origine]["I"] = i0
                self.etats[self.cfg.pays_origine]["S"] = n - i0

        for date in plage_dates:
            for ev in evenements:
                ev.appliquer(date, self)

            if date >= date_debut:
                self.propager(rng)

            new_etats = {}
            for pays in self.pays:
                if date < date_debut and pays != self.cfg.pays_origine:
                    new_etats[pays] = self.etats[pays]
                else:
                    new_etats[pays] = self.step_pays(pays, date)
            self.etats = new_etats

            for pays in self.pays:
                st = self.etats[pays]
                rows.append({
                    "country": pays, "date": date,
                    "S": st["S"], "E": st["E"], "I": st["I"],
                    "R": st["R"], "D": st["D"], "V": st["V"],
                    "population": st["pop"]
                })

        return pd.DataFrame(rows)


# l'erreur du scieclee
ConfigMaladie = Maladie
MoteurSEIRDV = Simulation