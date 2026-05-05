import pandas as pd
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from model import Simulation


class Event:
    def __init__(self, date, pays=None):
        self.date_trigger = pd.Timestamp(date)
        self.pays = pays
        self.declenche = False


    def cibles(self, sim):
        if self.pays:
            return [self.pays] if self.pays in sim.pays else []
        return sim.pays

    def appliquer(self, date, sim):
        if not self.declenche and date >= self.date_trigger:
            self.trigger(sim)
            self.declenche = True

    def trigger(self, sim):
        raise NotImplementedError




class Confinement(Event):

    def __init__(self, date, reduction, duree_jours, pays=None):
        super().__init__(date, pays)
        self.reduction = reduction
        self.duree = duree_jours
        self.date_fin = pd.Timestamp(date) + pd.Timedelta(days=duree_jours)
        self.leve = False

    def appliquer(self, date, sim):
        if not self.declenche and date >= self.date_trigger:
            self.trigger(sim)
            self.declenche = True
        # remet beta à None quand c'est fini = retour à la normale
        if self.declenche and not self.leve and date >= self.date_fin:
            for p in self.cibles(sim):
                sim.beta_override[p] = None
            self.leve = True



    def trigger(self, sim):
        beta_base = sim.cfg.r0 * sim.gamma
        for p in self.cibles(sim):
            sim.beta_override[p] = beta_base * (1 - self.reduction)


class Vaccination(Event):

    def __init__(self, date, taux_quotidien, pays=None):
        super().__init__(date, pays)
        self.taux = taux_quotidien

    def trigger(self, sim):
        for p in self.cibles(sim):
            sim.taux_vaccination[p] = self.taux


class NouveauVariant(Event):

    def __init__(self, date, nouveau_r0=None, nouveau_ifr=None, pays=None):
        super().__init__(date, pays)
        self.nouveau_r0 = nouveau_r0
        self.nouveau_ifr = nouveau_ifr

    def trigger(self, sim):
        if self.nouveau_r0 is not None:
            sim.cfg.r0 = self.nouveau_r0
            # reset les overrides sinon le nouveau r0 est ignoré là où il y avait un confinement
            for p in self.cibles(sim):
                sim.beta_override[p] = None
        if self.nouveau_ifr is not None:
            sim.cfg.taux_mortalite = self.nouveau_ifr


class MesuresSanitaires(Event):
    # comme confinement mais permanent=pas de date de fin

    def __init__(self, date, reduction, pays=None):
        super().__init__(date, pays)
        self.reduction = reduction

    def trigger(self, sim):
        beta_base = sim.cfg.r0 * sim.gamma
        for p in self.cibles(sim):
            sim.beta_override[p] = beta_base * (1 - self.reduction)


class LeveeRestrictions(Event):

    def __init__(self, date, pays=None):
        super().__init__(date, pays)

    def trigger(self, sim):
        for p in self.cibles(sim):
            sim.beta_override[p] = None


class FermetureFrontieres(Event):

    def __init__(self, date, duree_jours, pays=None):
        super().__init__(date, pays)
        self.duree = duree_jours
        self.date_fin = pd.Timestamp(date) + pd.Timedelta(days=duree_jours)
        self.leve = False
        self.vitesse_orig = None  # sauvegarde la vitesse avant fermeture pour la remettre après

    def appliquer(self, date, sim):
        if not self.declenche and date >= self.date_trigger:
            self.vitesse_orig = sim.cfg.vitesse_propagation
            sim.cfg.vitesse_propagation *= 0.05  # 95% de réduction des voyages
            self.declenche = True
        if self.declenche and not self.leve and date >= self.date_fin:
            sim.cfg.vitesse_propagation = self.vitesse_orig
            self.leve = True

    def trigger(self, sim):
        pass


# inshallah
Evenement = Event