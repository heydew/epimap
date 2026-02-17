import pandas as pd

# 1. Chargement des fichiers CSV

epidemie_path = "data/epidemie.csv"
population_path = "data/population.csv"

epidemie_df = pd.read_csv(epidemie_path)
population_df = pd.read_csv(population_path)

print("=== Données épidémiologiques ===")
print(epidemie_df.head(), "\n")

print("=== Données de population ===")
print(population_df.head(), "\n")


# 2. Fusion des données (épidémie + population)

data = epidemie_df.merge(population_df, on="country", how="left")

print("=== Données combinées ===")
print(data.head(), "\n")


# 3. Calcul SIR (jsp si cest bon encore)

# I = infectés actifs
data["I"] = data["cases"]

# R = guéris + décès
data["R"] = data["recovered"] + data["deaths"]

# S = population - I - R
data["S"] = data["population"] - data["I"] - data["R"]

# Sécurité : éviter valeurs négatives
data["S"] = data["S"].clip(lower=0)

print("=== Compartiments SIR calculés ===")
print(data[["date", "country", "S", "I", "R"]].head(), "\n")

# 4. Résumé par pays (état final)

latest_data = data.sort_values("date").groupby("country").last().reset_index()

print("=== État final par pays ===")
print(latest_data[["country", "S", "I", "R"]])
