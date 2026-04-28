

# pas fini, decommente pour lancer
"""import pandas as pd
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from model import MoteurSEIRDV


class Evenement:


    def __init__(self, date: str, pays: Optional[str] = None):
        self.date_declenchement = pd.Timestamp(date)
        self.pays = pays
        self._declenche = False


    def _cibles(self, moteur: "MoteurSEIRDV") -> list:
        if self.pays:
            return [self.pays] if self.pays in moteur.pays else []
        return moteur.pays

    def appliquer(self, date_courante: pd.Timestamp, moteur: "MoteurSEIRDV"):
        if not self._declenche and date_courante >= self.date_declenchement:
            self._declencher(moteur)
            self._declenche = True

    def _declencher(self, moteur: "MoteurSEIRDV"):
        raise NotImplementedError


class Confinement(Evenement):


    def __init__(self, date: str, reduction: float, duree_jours: int, pays: Optional[str] = None):
        super().__init__(date, pays)
        self.reduction = reduction
        self.duree_jours = duree_jours
        self.date_fin = pd.Timestamp(date) + pd.Timedelta(days=duree_jours)
        self._leve = False

    def appliquer(self, date_courante: pd.Timestamp, moteur: "MoteurSEIRDV"):
        if not self._declenche and date_courante >= self.date_declenchement:
            self._declencher(moteur)
            self._declenche = True
        if self._declenche and not self._leve and date_courante >= self.date_fin:
            for p in self._cibles(moteur):
                moteur.beta_override[p] = None
            self._leve = True

    def _declencher(self, moteur: "MoteurSEIRDV"):
        beta_base = moteur.cfg.r0 * moteur.gamma
        nouveau_beta = beta_base * (1 - self.reduction)
        for p in self._cibles(moteur):
            moteur.beta_override[p] = nouveau_beta


class Vaccination(Evenement):


    def __init__(self, date: str, taux_quotidien: float, pays: Optional[str] = None):
        super().__init__(date, pays)
        self.taux_quotidien = taux_quotidien

    def _declencher(self, moteur: "MoteurSEIRDV"):
        for p in self._cibles(moteur):
            moteur.taux_vaccination[p] = self.taux_quotidien


class NouveauVariant(Evenement):


    def __init__(self, date: str, nouveau_r0: Optional[float] = None,
                 nouveau_ifr: Optional[float] = None, pays: Optional[str] = None):
        super().__init__(date, pays)
        self.nouveau_r0 = nouveau_r0
        self.nouveau_ifr = nouveau_ifr

    def _declencher(self, moteur: "MoteurSEIRDV"):
        if self.nouveau_r0 is not None:
            moteur.cfg.r0 = self.nouveau_r0
            for p in self._cibles(moteur):
                moteur.beta_override[p] = None
        if self.nouveau_ifr is not None:
            moteur.cfg.taux_mortalite = self.nouveau_ifr


class MesuresSanitaires(Evenement):


    def __init__(self, date: str, reduction: float, pays: Optional[str] = None):
        super().__init__(date, pays)
        self.reduction = reduction

    def _declencher(self, moteur: "MoteurSEIRDV"):
        beta_base = moteur.cfg.r0 * moteur.gamma
        for p in self._cibles(moteur):
            moteur.beta_override[p] = beta_base * (1 - self.reduction)


class LeveeRestrictions(Evenement):


    def __init__(self, date: str, pays: Optional[str] = None):
        super().__init__(date, pays)

    def _declencher(self, moteur: "MoteurSEIRDV"):
        for p in self._cibles(moteur):
            moteur.beta_override[p] = None


class FermetureFrontieres(Evenement):


    def __init__(self, date: str, duree_jours: int, pays: Optional[str] = None):
        super().__init__(date, pays)
        self.duree_jours = duree_jours
        self.date_fin = pd.Timestamp(date) + pd.Timedelta(days=duree_jours)
        self._leve = False
        self._vitesse_originale = None

    def appliquer(self, date_courante: pd.Timestamp, moteur: "MoteurSEIRDV"):
        if not self._declenche and date_courante >= self.date_declenchement:
            self._vitesse_originale = moteur.cfg.vitesse_propagation
            moteur.cfg.vitesse_propagation *= 0.05
            self._declenche = True
        if self._declenche and not self._leve and date_courante >= self.date_fin:
            moteur.cfg.vitesse_propagation = self._vitesse_originale
            self._leve = True

    def _declencher(self, moteur: "MoteurSEIRDV"):
        pass