import math
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Dict, Tuple



def haversine(c1: Tuple[float, float], c2: Tuple[float, float]) -> float:

    R = 6371
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    # FIXE: return manquant dans la version originale
    return R * 2 * math.asin(math.sqrt(a))


def _extraire_coords(geom: dict) -> list:

    t = geom.get("type", "")
    if t == "Polygon":
        return geom["coordinates"][0]
    elif t == "MultiPolygon":
        pts = []
        for poly in geom["coordinates"]:
            pts.extend(poly[0])
        return pts
    return []


def lire_centroides_geojson(geojson_path: str) -> Dict[str, Tuple[float, float]]:

    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)

    centroides = {}
    for feature in geo["features"]:
        nom = feature["properties"].get("name", "")
        if not nom:
            continue
        coords = _extraire_coords(feature["geometry"])
        if coords:
            lats = [c[1] for c in coords]
            lons = [c[0] for c in coords]
            centroides[nom] = (sum(lats) / len(lats), sum(lons) / len(lons))
    return centroides


@dataclass
class ConfigMaladie:

    nom: str
    r0: float
    jours_incubation: float
    jours_contagieux: float
    taux_mortalite: float
    pays_origine: str
    date_debut: str
    infectes_initiaux: int = 10
    vitesse_propagation: float = 0.3
    saisonnalite: float = 0.0


class MoteurSEIRDV:


    def __init__(self, config: ConfigMaladie, population_df: pd.DataFrame, geojson_path: str):
        self.cfg = config
        self.pop_df = population_df.copy()
        self.pays = list(population_df["pays"].unique())

        self.sigma = 1.0 / config.jours_incubation
        self.gamma = 1.0 / config.jours_contagieux

        self.centroides = lire_centroides_geojson(geojson_path)
        self._construire_matrice_connexion()
        self._initialiser_etats()

        self.beta_override: Dict[str, Optional[float]] = {p: None for p in self.pays}
        self.taux_vaccination: Dict[str, float] = {p: 0.0 for p in self.pays}

    def _construire_matrice_connexion(self):
        self.conn: Dict[str, Dict[str, float]] = {}
        for p1 in self.pays:
            self.conn[p1] = {}
            coord1 = self.centroides.get(p1)
            for p2 in self.pays:
                if p1 == p2:
                    self.conn[p1][p2] = 0.0
                    continue
                coord2 = self.centroides.get(p2)
                if coord1 and coord2:
                    dist = haversine(coord1, coord2)
                    self.conn[p1][p2] = math.exp(-dist / 5000)
                else:
                    self.conn[p1][p2] = 0.01

        for p1 in self.pays:
            total = sum(self.conn[p1].values())
            if total > 0:
                for p2 in self.pays:
                    self.conn[p1][p2] /= total

    def _initialiser_etats(self):
        self.etats: Dict[str, Dict[str, float]] = {}
        for _, row in self.pop_df.iterrows():
            p = row["pays"]
            n = float(row["pop"])
            self.etats[p] = {"S": n, "E": 0.0, "I": 0.0, "R": 0.0, "D": 0.0, "V": 0.0, "pop": n}

        origine = self.cfg.pays_origine
        if origine in self.etats:
            n = self.etats[origine]["pop"]
            i0 = min(self.cfg.infectes_initiaux, n)
            self.etats[origine]["I"] = i0
            self.etats[origine]["S"] = n - i0

    def _get_beta(self, pays: str, date: pd.Timestamp) -> float:
        base = self.cfg.r0 * self.gamma
        if self.beta_override[pays] is not None:
            base = self.beta_override[pays]
        if self.cfg.saisonnalite > 0:
            facteur = 1 + self.cfg.saisonnalite * math.sin(2 * math.pi * date.day_of_year / 365)
            base *= facteur

        return min(base, 0.99)

    def _etape_pays(self, pays: str, date: pd.Timestamp) -> Dict[str, float]:
        st = self.etats[pays]
        n = st["pop"]
        if n <= 0:
            return st

        S, E, I, R, D, V = st["S"], st["E"], st["I"], st["R"], st["D"], st["V"]
        beta = self._get_beta(pays, date)

#vaccination
        nb_sous_pas = max(1, math.ceil(max(beta, self.sigma, self.gamma) / 0.25))
        dt = 1.0 / nb_sous_pas

        taux_vax = self.taux_vaccination[pays]

        for _ in range(nb_sous_pas):
            # S
            exp_brut = beta * S * I / n * dt
            vax_brut = taux_vax * S * dt
            total_sortie_S = exp_brut + vax_brut
            if total_sortie_S > S and total_sortie_S > 0:
                facteur = S / total_sortie_S
                exp_brut *= facteur
                vax_brut *= facteur

            #E
            inf_brut = self.sigma * E * dt
            inf_brut = min(inf_brut, E)

            # I
            ret_brut = self.gamma * (1 - self.cfg.taux_mortalite) * I * dt
            dec_brut = self.gamma * self.cfg.taux_mortalite * I * dt
            total_sortie_I = ret_brut + dec_brut
            if total_sortie_I > I and total_sortie_I > 0:
                fi = I / total_sortie_I
                ret_brut *= fi
                dec_brut *= fi

            S = max(S - exp_brut - vax_brut, 0)
            E = max(E + exp_brut - inf_brut, 0)
            I = max(I + inf_brut - ret_brut - dec_brut, 0)
            R = max(R + ret_brut, 0)
            D = max(D + dec_brut, 0)
            V = max(V + vax_brut, 0)

        # S+E+I+R+V = pop - D
        pop_vivante = S + E + I + R + V
        pop_cible   = max(n - D, 0)
        if pop_vivante > 0 and abs(pop_vivante - pop_cible) > 0.5:
            S = max(S + (pop_cible - pop_vivante), 0)

        return {"S": S, "E": E, "I": I, "R": R, "D": D, "V": V, "pop": n}

    def _propager_entre_pays(self, rng: np.random.Generator):
        #compter combien partent
        seeds: Dict[str, float] = {}   # = total arrivant dans pays dst

        for p_src in self.pays:
            I_src = self.etats[p_src]["I"]
            pop_src = self.etats[p_src]["pop"]
            if I_src < 1 or pop_src <= 0:
                continue

            taux_voyage = self.cfg.vitesse_propagation * 1e-5
            lambda_voyage = pop_src * taux_voyage * (I_src / pop_src)
            voyageurs = int(rng.poisson(lambda_voyage))
            if voyageurs == 0:
                continue
            # calma calma
            voyageurs = min(voyageurs, int(I_src))

            poids = np.array([self.conn[p_src].get(p2, 0) for p2 in self.pays])
            if poids.sum() == 0:
                continue
            poids /= poids.sum()
            destinations = rng.choice(len(self.pays), size=voyageurs, p=poids)

            partis = 0
            for idx in destinations:
                p_dst = self.pays[idx]
                if p_dst != p_src:
                    seeds[p_dst] = seeds.get(p_dst, 0) + 1
                    partis += 1

            # elever infectés
            if partis > 0:
                self.etats[p_src]["I"] = max(self.etats[p_src]["I"] - partis, 0)

        for p_dst, n_seed in seeds.items():
            s_dispo = self.etats[p_dst]["S"]
            seed = min(n_seed, s_dispo)
            if seed <= 0:
                continue
            self.etats[p_dst]["S"] -= seed
            self.etats[p_dst]["E"] += seed

    def simuler(self, plage_dates: pd.DatetimeIndex, evenements: list, graine: int = 42) -> pd.DataFrame:

        rng = np.random.default_rng(graine)
        date_debut = pd.Timestamp(self.cfg.date_debut)
        resultats = []

        for date in plage_dates:
            for ev in evenements:
                ev.appliquer(date, self)

            nouveaux_etats = {}
            for pays in self.pays:
                if date < date_debut and pays != self.cfg.pays_origine:
                    nouveaux_etats[pays] = self.etats[pays]
                else:
                    nouveaux_etats[pays] = self._etape_pays(pays, date)
            self.etats = nouveaux_etats

            if date >= date_debut:
                self._propager_entre_pays(rng)

            for pays in self.pays:
                st = self.etats[pays]
                resultats.append({
                    "country": pays, "date": date,
                    "S": st["S"], "E": st["E"], "I": st["I"],
                    "R": st["R"], "D": st["D"], "V": st["V"],
                    "population": st["pop"]
                })

        return pd.DataFrame(resultats)