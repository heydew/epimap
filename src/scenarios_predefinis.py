from model import ConfigMaladie
from scenarios import Confinement, Vaccination, NouveauVariant, FermetureFrontieres, MesuresSanitaires


def covid19():
    config = ConfigMaladie(
        nom="COVID-19",
        r0=2.5,
        jours_incubation=5,
        jours_contagieux=10,
        taux_mortalite=0.01,
        pays_origine="China",
        date_debut="2019-12-01",
        infectes_initiaux=67,
        vitesse_propagation=0.3,
        saisonnalite=0.0,
    )
    date_fin = "2022-01-01"
    evenements = [
        FermetureFrontieres("2020-01-23", duree_jours=90, pays="China"),
        Confinement("2020-03-15",       reduction=0.5, duree_jours=90),
        MesuresSanitaires("2020-06-15", reduction=0.25),
        Vaccination("2020-12-15",       taux_quotidien=0.008),
        NouveauVariant("2021-05-01",    nouveau_r0=5),
        NouveauVariant("2021-11-15",    nouveau_r0=8.0, nouveau_ifr=0.002),
    ]
    return config, date_fin, evenements


def h1n1():
    config = ConfigMaladie(
        nom="H1N1 (2009)",
        r0=1.4,
        jours_incubation=2,
        jours_contagieux=5,
        taux_mortalite=0.0002,
        pays_origine="Mexico",
        date_debut="2009-03-01",
        infectes_initiaux=100,
        vitesse_propagation=0.4,
        saisonnalite=0.0,
    )
    date_fin = "2010-06-01"
    evenements = [
        MesuresSanitaires("2009-04-25", reduction=0.2),
        Confinement("2009-04-30",       reduction=0.4, duree_jours=45, pays="Mexico"),
        Vaccination("2009-10-01",       taux_quotidien=0.005),
    ]
    return config, date_fin, evenements


def ebola():
    config = ConfigMaladie(
        nom="Ébola (2014)",
        r0=1.8,
        jours_incubation=8,
        jours_contagieux=7,
        taux_mortalite=0.50,
        pays_origine="Guinea",
        date_debut="2014-02-01",
        infectes_initiaux=10,
        vitesse_propagation=0.05,
        saisonnalite=0.0,
    )
    date_fin = "2016-01-01"
    evenements = [
        FermetureFrontieres("2014-07-01", duree_jours=400),
        MesuresSanitaires("2014-08-01",   reduction=0.5),
        Confinement("2014-08-20",         reduction=0.6, duree_jours=180, pays="Guinea"),
        Confinement("2014-08-20",         reduction=0.6, duree_jours=180, pays="Sierra Leone"),
        Confinement("2014-08-20",         reduction=0.6, duree_jours=180, pays="Liberia"),
    ]
    return config, date_fin, evenements


SCENARIOS = {
    "1": ("COVID-19",      covid19),
    "2": ("H1N1 (2009)",   h1n1),
    "3": ("Ébola (2014)",  ebola),
}