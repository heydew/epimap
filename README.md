# EpiMap

Projet de simulation d’épidémies avec le modèle SIR + visualisation sur carte (Folium).

## Lancer
1. Installer les dépendances:
   pip install -r requirements.txt
2. Mettre les CSV dans `data/`
3. (Optionnel) Ajouter `data/world_countries.geojson`
4. Exécuter:
   python src/main.py

## Sorties
- `out/sir_curves.png`
- `out/map.html`
