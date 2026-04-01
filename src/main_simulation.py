import pandas as pd
from pathlib import Path

# Importations locales (assure-toi que ces fichiers existent dans ton projet)
from io_data import get_pop
from model import ConfigMaladie, MoteurSEIRDV
from scenarios import (
    Confinement, Vaccination, NouveauVariant,
    MesuresSanitaires, LeveeRestrictions, FermetureFrontieres
)
import viz_curves
import viz_map

# Configuration des chemins
OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(exist_ok=True)
GEO = Path(__file__).resolve().parents[1] / "data" / "world-countries.geojson"
POP = Path(__file__).resolve().parents[1] / "data" / "population.csv"



def lire_str(prompt):
    return input(prompt).strip()


def lire_float(prompt):
    while True:
        try:
            return float(input(prompt).strip())
        except ValueError:
            print(" Entrez un nombre (ex: 2.5)")


def lire_int(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print(" Entrez un nombre entier.")


def lire_date(prompt):
    while True:
        val = input(prompt).strip()
        try:
            pd.Timestamp(val)
            return val
        except Exception:
            print(" Format attendu: YYYY-MM-DD")


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
        # Recherche insensible à la casse
        match = next((p for p in pays_valides if p.lower() == val.lower()), None)
        if match:
            return match
        print(f" Pays introuvable. Vérifie l'orthographe (ex: 'France', 'China')")




def saisir_maladie(pays_valides):
    print("\n=== CONFIGURATION DE LA MALADIE ===")
    print("""
Exemples de maladies de référence:
  Grippe saisonnière : R0=1.3, incubation=2j, contagieux=5j, mortalité=0.001
  COVID-19           : R0=2.5, incubation=5j, contagieux=10j, mortalité=0.01
  Rougeole           : R0=15,  incubation=10j, contagieux=8j,  mortalité=0.002
  Ebola              : R0=1.8, incubation=9j,  contagieux=7j,  mortalité=0.50
""")
    nom = lire_str("Nom de la maladie: ")
    r0 = lire_float("R0 - taux de reproduction (grippe=1.3, COVID=2.5, rougeole=15): ")
    jours_incubation = lire_float("Durée d'incubation en jours (grippe=2, COVID=5, rougeole=10): ")
    jours_contagieux = lire_float("Durée de contagiosité en jours (grippe=5, COVID=10, ebola=7): ")
    taux_mortalite = lire_float("Taux de mortalité 0-1 (grippe=0.001, COVID=0.01, ebola=0.50): ")
    pays_origine = lire_pays_valide("Pays d'origine: ", pays_valides)
    date_debut = lire_date("Date du premier infecté (YYYY-MM-DD): ")
    date_fin = lire_date("Date de fin de simulation (YYYY-MM-DD): ")
    infectes_initiaux = lire_int("Nombre d'infectés au départ (ex: 10): ")
    vitesse_prop = lire_float("Vitesse de propagation internationale 0-1 (faible=0.1, normale=0.3, rapide=0.7): ")

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


TYPES_EVENEMENTS = {
    "1": "Confinement",
    "2": "Vaccination",
    "3": "Nouveau variant",
    "4": "Mesures sanitaires",
    "5": "Levee des restrictions",
    "6": "Fermeture des frontieres",
}


def saisir_pays_optionnel(pays_valides):
    mondial = lire_oui_non("S'applique a tous les pays?")
    if mondial:
        return None
    return lire_pays_valide("Pays cible: ", pays_valides)


def saisir_evenement(pays_valides):
    print("\n Types d'evenements:")
    for k, v in TYPES_EVENEMENTS.items():
        print(f" {k}. {v}")
    choix = input(" Choix (1-6): ").strip()

    date = lire_date(" Date de declenchement (YYYY-MM-DD): ")

    if choix == "1":
        reduction = lire_float(" Reduction de contagiosite 0-1 (ex: 0.6): ")
        duree = lire_int(" Duree en jours: ")
        pays = saisir_pays_optionnel(pays_valides)
        return Confinement(date, reduction, duree, pays)

    elif choix == "2":
        taux = lire_float(" Taux de vaccination quotidien 0-1: ")
        pays = saisir_pays_optionnel(pays_valides)
        return Vaccination(date, taux, pays)

    elif choix == "3":
        nouveau_r0 = None
        nouveau_ifr = None
        if lire_oui_non(" Modifier le R0?"):
            nouveau_r0 = lire_float(" Nouveau R0: ")
        if lire_oui_non(" Modifier le taux de mortalite?"):
            nouveau_ifr = lire_float(" Nouveau taux de mortalite 0-1: ")
        pays = saisir_pays_optionnel(pays_valides)
        return NouveauVariant(date, nouveau_r0, nouveau_ifr, pays)

    elif choix == "4":
        reduction = lire_float(" Reduction permanente de contagiosite 0-1: ")
        pays = saisir_pays_optionnel(pays_valides)
        return MesuresSanitaires(date, reduction, pays)

    elif choix == "5":
        pays = saisir_pays_optionnel(pays_valides)
        return LeveeRestrictions(date, pays)

    elif choix == "6":
        duree = lire_int(" Duree de fermeture en jours: ")
        pays = saisir_pays_optionnel(pays_valides)
        return FermetureFrontieres(date, duree, pays)

    return None


def saisir_evenements(pays_valides):
    print("\n=== EVENEMENTS ===")
    evenements = []
    while lire_oui_non("Ajouter un evenement?"):
        ev = saisir_evenement(pays_valides)
        if ev:
            evenements.append(ev)
            print(f" Evenement ajoute. ({len(evenements)} au total)")
    return evenements



if __name__ == "__main__":
    print("Chargement de la population...")
    pop = get_pop(p=str(POP))
    # On filtre pour ne garder que les pays significatifs pour la simulation
    pop = pop[pop["pop"] > 100_000].copy()
    pays_valides = set(pop["pays"].unique())

    # Saisie utilisateur
    maladie, date_fin = saisir_maladie(pays_valides)
    evenements = saisir_evenements(pays_valides)

    # Calcul de la plage temporelle
    plage = pd.date_range(start=maladie.date_debut, end=date_fin, freq="D")
    print(f"\nSimulation {maladie.nom} — {len(pop)} pays, {len(plage)} jours...")

    # Initialisation du moteur et simulation
    moteur = MoteurSEIRDV(maladie, pop, str(GEO))
    data = moteur.simuler(plage, evenements)

    # Aggrégation mondiale pour les statistiques
    world = data.groupby("date")[["S", "E", "I", "R", "D", "V"]].sum().reset_index()

    print(f"Pic infectes: {world['I'].max():,.0f} personnes")
    print(f"Deces totaux: {world['D'].iloc[-1]:,.0f}")

    # Export des visualisations
    f_courbes = str(OUT / "simulation_courbes.html")
    f_carte = str(OUT / "simulation_carte.html")

    viz_curves.tracer_seirdv(world, maladie.nom, f_courbes)
    viz_map.carte_simulation(data, str(GEO), f_carte, maladie.nom)

    print("\nSimulation terminée. Ouverture des résultats...")
    viz_curves.out(f_courbes)
    viz_map.out(f_carte)