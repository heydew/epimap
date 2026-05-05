import pandas as pd
from pathlib import Path
from io_data import get_pop
from model import ConfigMaladie, MoteurSEIRDV
from scenarios import (
    Confinement, Vaccination, NouveauVariant,
    MesuresSanitaires, LeveeRestrictions, FermetureFrontieres
)
import viz_curves
import viz_map

OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(exist_ok=True)
GEO = Path(__file__).resolve().parents[1] / "data" / "world-countries.geojson"
POP = Path(__file__).resolve().parents[1] / "data" / "population.csv"


#  saisie utilisateur

def lire_str(prompt):
    return input(prompt).strip()


def lire_float(prompt):
    while True:
        try:
            return float(input(prompt).strip())
        except ValueError:
            print("nombre invalide, réessaie (ex: 2.5)")


def lire_int(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("entier attendu")


def lire_date(prompt):
    while True:
        val = input(prompt).strip()
        try:
            pd.Timestamp(val)
            return val
        except Exception:
            print("format attendu: YYYY-MM-DD")


def lire_oui_non(prompt):
    while True:
        val = input(prompt + " (o/n): ").strip().lower()
        if val in ("o", "oui", "y", "yes"):
            return True
        if val in ("n", "non", "no"):
            return False


def lire_pays_valide(prompt, pays_valides):
    while True:
        val = input(prompt).strip()
        if val in pays_valides:
            return val
        # essaie en ignorant la casse
        match = next((p for p in pays_valides if p.lower() == val.lower()), None)
        if match:
            return match
        print(f"pays introuvable, vérifie l'orthographe (ex: 'France', 'China')")


#maladie

def saisir_maladie(pays_valides):
    print("config maladie custom:")

    nom = lire_str("nom: ")
    r0 = lire_float("R0 (grippe=1.3, covid=2.5, rougeole=15): ")
    jours_incubation = lire_float("incubation en jours (grippe=2, covid=5, rougeole=10): ")
    jours_contagieux = lire_float("contagiosité en jours (grippe=5, covid=10, ebola=7): ")
    taux_mortalite = lire_float("mortalité 0-1 (grippe=0.001, covid=0.01, ebola=0.50): ")
    pays_origine = lire_pays_valide("pays d'origine: ", pays_valides)
    date_debut = lire_date("date du premier infecté (YYYY-MM-DD): ")
    date_fin = lire_date("date de fin de simulation (YYYY-MM-DD): ")
    infectes_initiaux = lire_int("infectés au départ (ex: 67): ")
    vitesse_prop = lire_float("vitesse propagation internationale 0-1 (lente=0.1, normale=0.3, rapide=0.7): ")

    config = ConfigMaladie(
        nom=nom,
        r0=r0,
        jours_incubation=jours_incubation,
        jours_contagieux=jours_contagieux,
        taux_mortalite=taux_mortalite,
        pays_origine=pays_origine,
        date_debut=date_debut,
        infectes_initiaux=infectes_initiaux,
        vitesse_propagation=vitesse_prop,
        saisonnalite=0.0,
    )
    return config, date_fin


# evenements

TYPES_EVENEMENTS = {
    "1": "Confinement",
    "2": "Vaccination",
    "3": "Nouveau variant",
    "4": "Mesures sanitaires",
    "5": "Levée des restrictions",
    "6": "Fermeture des frontières",
}


def saisir_pays_optionnel(pays_valides):
    if lire_oui_non("s'applique à tous les pays?"):
        return None
    return lire_pays_valide("pays cible: ", pays_valides)


def saisir_evenement(pays_valides):
    print("\névénements disponibles:")
    for k, v in TYPES_EVENEMENTS.items():
        print(f"  {k}. {v}")
    choix = input("choix (1-6): ").strip()

    date = lire_date("date de déclenchement (YYYY-MM-DD): ")

    if choix == "1":
        reduction = lire_float("réduction de contagiosité 0-1 (ex: 0.6): ")
        duree = lire_int("durée en jours: ")
        pays = saisir_pays_optionnel(pays_valides)
        return Confinement(date, reduction, duree, pays)

    elif choix == "2":
        taux = lire_float("taux de vaccination quotidien 0-1: ")
        pays = saisir_pays_optionnel(pays_valides)
        return Vaccination(date, taux, pays)

    elif choix == "3":
        nouveau_r0 = None
        nouveau_ifr = None
        if lire_oui_non("modifier le R0?"):
            nouveau_r0 = lire_float("nouveau R0: ")
        if lire_oui_non("modifier le taux de mortalité?"):
            nouveau_ifr = lire_float("nouveau taux de mortalité 0-1: ")
        pays = saisir_pays_optionnel(pays_valides)
        return NouveauVariant(date, nouveau_r0, nouveau_ifr, pays)

    elif choix == "4":
        reduction = lire_float("réduction permanente de contagiosité 0-1: ")
        pays = saisir_pays_optionnel(pays_valides)
        return MesuresSanitaires(date, reduction, pays)

    elif choix == "5":
        pays = saisir_pays_optionnel(pays_valides)
        return LeveeRestrictions(date, pays)

    elif choix == "6":
        duree = lire_int("durée de fermeture en jours: ")
        pays = saisir_pays_optionnel(pays_valides)
        return FermetureFrontieres(date, duree, pays)

    # choix invalide, on retourne None, saisir_evenements() gère ça
    return None


def saisir_evenements(pays_valides):
    evs = []
    while lire_oui_non("ajouter un événement?"):
        ev = saisir_evenement(pays_valides)
        if ev:
            evs.append(ev)
            print(f"ok, {len(evs)} événement(s) au total")
    return evs


#  main

if __name__ == "__main__":
    print("chargement population...")
    pop = get_pop(p=str(POP))
    pop = pop[pop["pop"] > 100_000].copy()  # ignore les mini pays c chiant
    pays_valides = set(pop["pays"].unique())

    from scenarios_predefinis import SCENARIOS
    print("\nquel scénario?")
    print("  0. personnalisé")
    for k, (nom, _) in SCENARIOS.items():
        print(f"  {k}. {nom}")
    choix = input("\nchoix: ").strip()

    if choix in SCENARIOS:
        _, fn = SCENARIOS[choix]
        maladie, date_fin, evenements = fn()
        print(f"scénario chargé: {maladie.nom}")
    else:
        maladie, date_fin = saisir_maladie(pays_valides)
        evenements = saisir_evenements(pays_valides)

    plage = pd.date_range(start=maladie.date_debut, end=date_fin, freq="D")
    print(f"\nlancement: {maladie.nom} — {len(pop)} pays, {len(plage)} jours")

    moteur = MoteurSEIRDV(maladie, pop, str(GEO))
    data = moteur.simuler(plage, evenements)

    world = data.groupby("date")[["S", "E", "I", "R", "D", "V"]].sum().reset_index()

    print(f"pic infectés : {world['I'].max():,.0f}")
    print(f"décès totaux : {world['D'].iloc[-1]:,.0f}")

    f_courbes = str(OUT / "simulation_courbes.html")
    f_carte = str(OUT / "simulation_carte.html")

    viz_curves.tracer_seirdv(world, maladie.nom, f_courbes)
    viz_map.carte_simulation(data, str(GEO), f_carte, maladie.nom)

    print("\nouverture des résultats...")
    viz_curves.out(f_courbes)
    viz_map.out(f_carte)