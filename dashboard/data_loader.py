# -*- coding: utf-8 -*-
"""Chargement des tables agrégées (sorties des notebooks 01-11) pour les deux joueurs.

Dépôt public : seules les tables déjà agrégées/anonymisées sont présentes ici
(data/athlete1/, data/joueur2/) — pas les CSV bruts Whoop, pas les notebooks.
Ne recalcule rien : lit uniquement outputs/interim/*.pkl et outputs/*.csv.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent

ATHLETES = {
    "athlete1": {
        "label": "Athlète 1",
        "root": ROOT / "data" / "athlete1",
        "periode": "22 mai 2025 → 17 juillet 2026",
        "jours": 422,
    },
    "joueur2": {
        "label": "Joueur 2",
        "root": ROOT / "data" / "joueur2",
        "periode": "27 août 2024 → 17 mars 2026",
        "jours": 568,
    },
}

# les 5 questions de journal de l'athlète 1 (aucune variance, cf. étape 9) ->
# on ne les affiche pas comme signal exploitable dans le dashboard
JRN_SANS_VARIANCE = {"jrn_alcool", "jrn_cafeine", "jrn_hydrate", "jrn_repas_tardif",
                     "jrn_ecran_lit", "jrn_celibataire", "jrn_ains", "jrn_sauna",
                     "jrn_hammam", "jrn_avion"}


@st.cache_data(show_spinner=False)
def load_daily(athlete_key: str) -> pd.DataFrame:
    """Table quotidienne enrichie : cluster (07) + charge/ACWR (08) + score
    d'anomalie (10), toutes indexées sur le calendrier complet du joueur."""
    root = ATHLETES[athlete_key]["root"]
    interim = root / "outputs" / "interim"

    dn = pd.read_pickle(interim / "07_daily_clusters.pkl")
    charge = pd.read_pickle(interim / "08_charge.pkl")
    score = pd.read_pickle(interim / "10_score_anomalie.pkl")

    df = dn.join(charge, rsuffix="_charge").join(score, rsuffix="_score")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # les colonnes jrn_* sont stockées en objet (True/False/NaN mêlés) par le
    # pivot du notebook 03 -> repassées en float pour permettre moyennes/graphes
    for c in df.columns:
        if c.startswith("jrn_") and df[c].dtype == object:
            df[c] = df[c].astype(float)

    # type de journée, reconstruit ici (pas persisté par les notebooks) à partir
    # des colonnes qui, elles, le sont : jour_off et seance_foot
    def _type_jour(r):
        if r.get("jour_off"):
            return "repos"
        return "foot" if r.get("seance_foot") else "autre séance"

    df["type_jour"] = df.apply(_type_jour, axis=1)
    return df


@st.cache_data(show_spinner=False)
def load_episodes(athlete_key: str) -> pd.DataFrame:
    """Fenêtres d'anomalie détectées (notebook 10, §2-4)."""
    root = ATHLETES[athlete_key]["root"]
    path = root / "outputs" / "10_episodes_detectes.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["debut", "fin"])
    return df.sort_values("debut")


@st.cache_data(show_spinner=False)
def load_ecarts_foot(athlete_key: str) -> pd.DataFrame:
    """Coupures de foot >= 6 jours (notebook 10, §7)."""
    root = ATHLETES[athlete_key]["root"]
    path = root / "outputs" / "10_ecarts_foot.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["debut", "fin"])
    return df.sort_values("jours_sans_foot", ascending=False)


@st.cache_data(show_spinner=False)
def load_segments_fuseau(athlete_key: str) -> pd.DataFrame:
    root = ATHLETES[athlete_key]["root"]
    path = root / "outputs" / "11_segments_fuseau.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["debut", "fin"])


@st.cache_data(show_spinner=False)
def load_dictionnaire(athlete_key: str) -> pd.DataFrame:
    root = ATHLETES[athlete_key]["root"]
    path = root / "outputs" / "09_dictionnaire_donnees.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def journal_exploitable_cols(df: pd.DataFrame) -> list:
    """Colonnes jrn_* à variance réelle (exclut celles listées comme constantes)."""
    cols = [c for c in df.columns if c.startswith("jrn_") and c != "jrn_rempli"]
    return [c for c in cols if c not in JRN_SANS_VARIANCE and df[c].nunique(dropna=True) > 1]
