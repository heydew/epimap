"""
model.py — Moteur de simulation épidémiologique SEIRD+V
Compartiments: S -> E -> I -> R + D (Décès) + V (Vaccinés)
"""

import math
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Dict, Tuple


HUBS_AERIENS = {
    "United States of America", "China", "United Kingdom", "Germany", "France",
    "United Arab Emirates", "Singapore", "Japan", "Netherlands", "Turkey"
}


def haversine(c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
    """Distance en km entre deux coordonnées (lat, lon)."""
    R = 6371
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    # FIXE: return manquant dans la version originale
    return R * 2 * math.asin(math.sqrt(a))


def _extraire_coords(geom: dict) -> list:
    """Extrait toutes les coordonnées d'une géométrie GeoJSON."""
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
    """Retourne {nom_pays: (lat, lon)} depuis le GeoJSON."""
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
    """Paramètres de la maladie définis par l'utilisateur."""
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
    """Simule une épidémie SEIRD+V sur tous les pays."""

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
                    score_geo = math.exp(-dist / 5000)
                else:
                    score_geo = 0.01
                bonus_hub = 2.5 if (p1 in HUBS_AERIENS or p2 in HUBS_AERIENS) else 1.0
                self.conn[p1][p2] = score_geo * bonus_hub

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
        return base

    def _etape_pays(self, pays: str, date: pd.Timestamp) -> Dict[str, float]:
        st = self.etats[pays]
        n = st["pop"]
        if n <= 0:
            return st

        S, E, I, R, D, V = st["S"], st["E"], st["I"], st["R"], st["D"], st["V"]

        # securite: recapiter avant de calculer (au cas ou propagation aurait depasse N)
        total = S + E + I + R + D + V
        if total > n and total > 0:
            facteur = n / total
            S *= facteur; E *= facteur; I *= facteur
            R *= facteur; D *= facteur; V *= facteur

        beta = self._get_beta(pays, date)

        nouveaux_exposes  = min(beta * S * I / n, S)
        nouveaux_infectes = min(self.sigma * E, E)
        nouveaux_retablis = min(self.gamma * (1 - self.cfg.taux_mortalite) * I, I)
        nouveaux_deces    = min(self.gamma * self.cfg.taux_mortalite * I, I - nouveaux_retablis)
        nouveaux_vaccines = min(self.taux_vaccination[pays] * S, max(S - nouveaux_exposes, 0))

        new_E = max(E + nouveaux_exposes - nouveaux_infectes, 0)
        new_I = max(I + nouveaux_infectes - nouveaux_retablis - nouveaux_deces, 0)
        new_R = max(R + nouveaux_retablis, 0)
        new_D = max(D + nouveaux_deces, 0)
        new_V = max(V + nouveaux_vaccines, 0)
        # S derive de la conservation stricte: evite toute accumulation de masse
        new_S = max(n - new_E - new_I - new_R - new_D - new_V, 0)

        return {
            "S": new_S, "E": new_E, "I": new_I,
            "R": new_R, "D": new_D, "V": new_V, "pop": n
        }

    def _propager_entre_pays(self, rng: np.random.Generator):
        seeds: Dict[str, float] = {}
        n_pays = max(len(self.pays), 1)

        # Total infectes dans le monde -> taux de base global
        total_infectes = sum(self.etats[p]["I"] for p in self.pays)
        pop_mondiale = sum(self.etats[p]["pop"] for p in self.pays)
        # Taux de base: chaque pays recoit un tout petit flux proportionnel
        # aux infectes mondiaux, independamment de la distance
        # ~0.0001% des infectes mondiaux se dispersent uniformement
        taux_base_global = self.cfg.vitesse_propagation * 0.00005 / max(n_pays, 1)

        for p_src in self.pays:
            I_src = self.etats[p_src]["I"]
            if I_src < 1:
                continue
            n_src = self.etats[p_src]["pop"]

            # Propagation géographique (comme avant mais plafond relevé)
            taux_voyage = self.cfg.vitesse_propagation / (500 * n_pays)
            max_voyageurs = max(2, n_src * 0.00005)
            voyageurs = min(rng.poisson(max(I_src * taux_voyage, 0.1)), max_voyageurs)
            if voyageurs > 0:
                poids = np.array([self.conn[p_src].get(p2, 0) for p2 in self.pays])
                if poids.sum() > 0:
                    poids /= poids.sum()
                    destinations = rng.choice(len(self.pays), size=int(voyageurs), p=poids)
                    for idx in destinations:
                        p_dst = self.pays[idx]
                        if p_dst != p_src and self.etats[p_dst]["S"] > 1:
                            seeds[p_dst] = seeds.get(p_dst, 0) + 1

            # Propagation de base globale: chaque pays infecté envoie
            # un micro-flux vers TOUS les autres pays
            flux_base = I_src * taux_base_global
            if flux_base >= 0.01:
                for p_dst in self.pays:
                    if p_dst != p_src and self.etats[p_dst]["S"] > 1:
                        seeds[p_dst] = seeds.get(p_dst, 0) + flux_base

        for p_dst, n_seed in seeds.items():
            s_dispo = self.etats[p_dst]["S"]
            seed = min(n_seed, s_dispo)
            if seed <= 0:
                continue
            self.etats[p_dst]["S"] -= seed
            self.etats[p_dst]["E"] += seed

    def simuler(self, plage_dates: pd.DatetimeIndex, evenements: list, graine: int = 42) -> pd.DataFrame:
        """Lance la simulation. Retourne un DataFrame (country, date, S, E, I, R, D, V, population)."""
        rng = np.random.default_rng(graine)
        date_debut = pd.Timestamp(self.cfg.date_debut)
        resultats = []

        pop_mondiale = sum(self.etats[p]["pop"] for p in self.pays)
        if pop_mondiale > 15_000_000_000:
            # probablement des doublons ou mauvaise unite -> normaliser
            facteur = 8_000_000_000 / pop_mondiale
            for p in self.pays:
                n = self.etats[p]["pop"] * facteur
                self.etats[p]["pop"] = n
                self.etats[p]["S"] = n
                self.etats[p]["I"] = 0.0
                self.etats[p]["E"] = 0.0
            # reinitialiser infectes initiaux
            if self.cfg.pays_origine in self.etats:
                n = self.etats[self.cfg.pays_origine]["pop"]
                i0 = min(self.cfg.infectes_initiaux, n)
                self.etats[self.cfg.pays_origine]["I"] = i0
                self.etats[self.cfg.pays_origine]["S"] = n - i0

        for date in plage_dates:
            for ev in evenements:
                ev.appliquer(date, self)

            if date >= date_debut:
                self._propager_entre_pays(rng)

            nouveaux_etats = {}
            for pays in self.pays:
                if date < date_debut and pays != self.cfg.pays_origine:
                    nouveaux_etats[pays] = self.etats[pays]
                else:
                    nouveaux_etats[pays] = self._etape_pays(pays, date)
            self.etats = nouveaux_etats

            for pays in self.pays:
                st = self.etats[pays]
                resultats.append({
                    "country": pays, "date": date,
                    "S": st["S"], "E": st["E"], "I": st["I"],
                    "R": st["R"], "D": st["D"], "V": st["V"],
                    "population": st["pop"]
                })

        return pd.DataFrame(resultats)