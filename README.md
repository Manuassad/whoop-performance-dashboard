# Performance Command Center — Whoop (démo publique)

Dashboard Streamlit présentant les résultats d'une analyse exploratoire (EDA) de données
Whoop sur deux joueurs de football, dans l'esprit visuel d'un centre de performance
(fond sombre, jauges, fenêtres à surveiller, constats automatiques).

**Ce dépôt est volontairement limité aux données déjà agrégées et anonymisées** — scores
quotidiens (récupération, sommeil, charge, ACWR...), fenêtres de déviation détectées, segments
de fuseau horaire. Il ne contient **aucun** export Whoop brut, aucun notebook d'analyse, aucun
nom : voir `data/athlete1/` et `data/joueur2/`. Le pipeline complet (11 notebooks, données
sources) vit dans un dépôt privé séparé.

## Lancer en local

```
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Contenu

- `dashboard/app.py` — 6 pages : Command Center, Joueur 360, Détection d'anomalies, Fuseau
  horaire, Comparaison, Méthodologie
- `dashboard/data_loader.py` — chargement des tables (dict `ATHLETES`, un joueur = un dossier
  sous `data/`)
- `dashboard/components.py` — thème sombre, jauges, badges
- `data/athlete1/`, `data/joueur2/` — tables agrégées uniquement
- `.streamlit/config.toml` — thème sombre natif Streamlit

## Le score « État de forme »

Affiché sur la page Command Center : `0,5 × récupération + 0,5 × performance de sommeil`.
C'est un indicateur construit pour ce dashboard — **pas** un score Whoop officiel — documenté
dans l'application (page Méthodologie).

## Limites

Whoop ne loggue aucune blessure ni maladie : les « fenêtres à surveiller » sont des hypothèses
statistiques, pas des diagnostics. Deux joueurs seulement — aucune conclusion n'est
généralisable à un groupe. Les indices Whoop (récupération, HRV...) ne sont pas comparables en
valeur absolue entre deux personnes.
