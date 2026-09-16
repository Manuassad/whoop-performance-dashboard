# -*- coding: utf-8 -*-
"""Performance Command Center — Whoop
Dashboard Streamlit présentant les résultats de l'EDA (notebooks 01-11) sur
les deux joueurs suivis, dans l'esprit du Performance Center de la plateforme
(fond sombre, jauges, fenêtres à surveiller, constats).

Lancer : .venv/Scripts/streamlit run dashboard/app.py
"""
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import (
    ATHLETES, load_daily, load_episodes, load_ecarts_foot,
    load_segments_fuseau, load_dictionnaire, journal_exploitable_cols,
)
from components import (
    inject_css, gauge, badge, section_title,
    BG, CARD, CARD_BORDER, ACCENT, TEAL, AMBER, TEXT, MUTED, PLOTLY_LAYOUT,
)

st.set_page_config(page_title="Performance Command Center — Whoop", layout="wide",
                    initial_sidebar_state="expanded")
inject_css()

HYP_KIND = {
    "maladie probable": "risk",
    "surcharge probable": "risk",
    "dette de sommeil aiguë": "warn",
    "lié à un changement de fuseau": "warn",
    "indéterminé": "warn",
}

# ----------------------------------------------------------------- SIDEBAR
with st.sidebar:
    st.markdown(
        f'<div style="font-size:1.4rem;font-weight:900;color:{TEXT};letter-spacing:.02em;">'
        f'PERFORMANCE<span style="color:{ACCENT};">.</span>WHOOP</div>'
        f'<div class="muted">Analyse de performance — données Whoop</div><hr>',
        unsafe_allow_html=True,
    )
    athlete_key = st.selectbox(
        "Joueur", options=list(ATHLETES.keys()),
        format_func=lambda k: ATHLETES[k]["label"],
    )
    info = ATHLETES[athlete_key]
    st.caption(f"{info['periode']} · {info['jours']} jours")

    page = st.radio(
        "Navigation",
        ["Command Center", "Joueur 360", "Détection d'anomalies",
         "Fuseau horaire", "Comparaison", "Méthodologie"],
    )
    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("Sources : notebooks 01 à 11 (EDA), aucune donnée recalculée ici.")

daily = load_daily(athlete_key)
episodes = load_episodes(athlete_key)
ecarts_foot = load_ecarts_foot(athlete_key)
segments_tz = load_segments_fuseau(athlete_key)
dico = load_dictionnaire(athlete_key)

derniere_date = daily.index[daily["bracelet_porte"]].max()

# ----------------------------------------------------------------- HELPERS

def period_selector(key_suffix=""):
    c1, c2 = st.columns([2, 3])
    with c1:
        fenetre = st.selectbox(
            "Fenêtre", ["7 derniers jours", "30 derniers jours", "90 derniers jours", "Toute la période"],
            index=1, key="fen" + key_suffix,
        )
    n = {"7 derniers jours": 7, "30 derniers jours": 30, "90 derniers jours": 90}.get(fenetre)
    with c2:
        ref = st.date_input(
            "Date de référence", value=derniere_date.date(),
            min_value=daily.index.min().date(), max_value=daily.index.max().date(),
            key="ref" + key_suffix,
        )
    ref = pd.Timestamp(ref)
    if n is None:
        deb = daily.index.min()
    else:
        deb = ref - timedelta(days=n - 1)
    return deb, ref, fenetre


def kpi_delta(series: pd.Series, deb, fin):
    cur = series.loc[deb:fin].mean()
    span = (fin - deb).days + 1
    prev_deb, prev_fin = deb - timedelta(days=span), deb - timedelta(days=1)
    prev = series.loc[prev_deb:prev_fin].mean()
    if pd.isna(cur):
        return np.nan, np.nan
    if pd.isna(prev) or prev == 0:
        return cur, np.nan
    return cur, (cur - prev) / abs(prev) * 100


def line_chart(df, cols, colors, names, title, yaxis="", height=260):
    fig = go.Figure()
    for c, color, name in zip(cols, colors, names):
        fig.add_trace(go.Scatter(x=df.index, y=df[c], mode="lines", name=name,
                                  line=dict(color=color, width=2)))
    fig.update_layout(title=title, height=height, yaxis_title=yaxis,
                       legend=dict(orientation="h", y=1.15, font=dict(size=10)),
                       xaxis=dict(showgrid=False), yaxis=dict(gridcolor=CARD_BORDER),
                       **PLOTLY_LAYOUT)
    return fig


def episode_badges(df: pd.DataFrame):
    if df.empty:
        st.info("Aucune fenêtre détectée sur la période.")
        return
    for _, r in df.iterrows():
        kind = HYP_KIND.get(r["hypothese"], "warn")
        st.markdown(
            f'<div class="card" style="display:flex;justify-content:space-between;align-items:center;">'
            f'<div><b>{r["debut"].strftime("%d %b %Y")} → {r["fin"].strftime("%d %b %Y")}</b>'
            f'<span class="muted"> · {int(r["n_jours"])} j · détection {r["detection"]}</span></div>'
            f'{badge(r["hypothese"], kind)}</div>',
            unsafe_allow_html=True,
        )


# =================================================================== PAGE 1
if page == "Command Center":
    deb, ref, fenetre = period_selector("_cc")
    seg = daily.loc[deb:ref]
    seg_bracelet = seg[seg["bracelet_porte"]]

    recup_cur, recup_delta = kpi_delta(daily["recup"], deb, ref)
    sommeil_cur, sommeil_delta = kpi_delta(daily["sommeil_min"], deb, ref)
    etat_forme_series = 0.5 * daily["recup"] + 0.5 * daily["sommeil_perf"]
    forme_cur, forme_delta = kpi_delta(etat_forme_series, deb, ref)
    charge_7j = daily["strain_seances"].loc[ref - timedelta(days=6):ref].sum()
    charge_7j_prev = daily["strain_seances"].loc[ref - timedelta(days=13):ref - timedelta(days=7)].sum()
    charge_delta = (charge_7j - charge_7j_prev) / charge_7j_prev * 100 if charge_7j_prev else np.nan

    # bandeau de synthèse (équivalent du "HIGHT AI Briefing", généré depuis les vraies données)
    actives = episodes[(episodes["debut"] <= ref) & (episodes["fin"] >= ref - timedelta(days=3))] if not episodes.empty else pd.DataFrame()
    acwr_now = daily["acwr"].loc[:ref].dropna()
    acwr_val = acwr_now.iloc[-1] if len(acwr_now) else np.nan
    briefing_bits = []
    if not actives.empty:
        briefing_bits.append(f"{len(actives)} fenêtre(s) à surveiller active(s) autour de la date de référence.")
    else:
        briefing_bits.append("Aucune fenêtre à surveiller active autour de la date de référence.")
    if pd.notna(acwr_val):
        zone = "dans la zone habituelle" if 0.8 <= acwr_val <= 1.3 else "hors zone habituelle"
        briefing_bits.append(f"ACWR à {acwr_val:.2f} ({zone}).")
    deficit = seg_bracelet["ecart_besoin_sommeil"].mean()
    if pd.notna(deficit) and deficit < 0:
        briefing_bits.append(f"Déficit de sommeil moyen de {abs(deficit):.0f} min sur la période.")

    st.markdown(
        f'<div class="eyebrow">{info["label"].upper()} / PERFORMANCE CENTER</div>'
        f'<h1 style="margin-top:-6px;">COMMAND CENTER</h1>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([2.3, 1])
    with c1:
        st.markdown(f'<div class="muted">{fenetre.upper()} · référence {ref.strftime("%d %B %Y")}</div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="card"><div class="eyebrow">Constat automatique</div>'
            f'<div style="font-size:0.92rem;">{" ".join(briefing_bits)}</div>'
            f'<div class="muted" style="margin-top:6px;">Calculé depuis les sorties EDA — pas un modèle temps réel.</div></div>',
            unsafe_allow_html=True,
        )

    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.plotly_chart(gauge(forme_cur if pd.notna(forme_cur) else 0, "État de forme", vmax=100, color=ACCENT),
                         width='stretch', config={"displayModeBar": False})
        st.markdown(f'<div class="kpi-label">État de forme</div>', unsafe_allow_html=True)
        if pd.notna(forme_delta):
            cls = "kpi-delta-up" if forme_delta >= 0 else "kpi-delta-down"
            st.markdown(f'<span class="{cls}">{forme_delta:+.0f} % vs période précédente</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with g2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.plotly_chart(gauge(recup_cur if pd.notna(recup_cur) else 0, "Récupération", vmax=100, color=TEAL),
                         width='stretch', config={"displayModeBar": False})
        st.markdown('<div class="kpi-label">Récupération (Whoop)</div>', unsafe_allow_html=True)
        if pd.notna(recup_delta):
            cls = "kpi-delta-up" if recup_delta >= 0 else "kpi-delta-down"
            st.markdown(f'<span class="{cls}">{recup_delta:+.0f} % vs période précédente</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with g3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{charge_7j:.0f}<span style="font-size:1rem;color:{MUTED};"> AU</span></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="kpi-label">Charge — 7 derniers jours</div>', unsafe_allow_html=True)
        if pd.notna(charge_delta):
            cls = "kpi-delta-up" if charge_delta >= 0 else "kpi-delta-down"
            st.markdown(f'<span class="{cls}">{charge_delta:+.0f} % vs 7 j précédents</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with g4:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        h = sommeil_cur / 60 if pd.notna(sommeil_cur) else 0
        st.markdown(f'<div class="kpi-value">{h:.1f}<span style="font-size:1rem;color:{MUTED};"> h</span></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="kpi-label">Sommeil moyen / nuit</div>', unsafe_allow_html=True)
        if pd.notna(sommeil_delta):
            cls = "kpi-delta-up" if sommeil_delta >= 0 else "kpi-delta-down"
            st.markdown(f'<span class="{cls}">{sommeil_delta:+.0f} % vs période précédente</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Comment le score « État de forme » est calculé"):
        st.write(
            "Indicateur construit pour ce dashboard — **pas** un score Whoop officiel : "
            "`0,5 × récupération + 0,5 × performance de sommeil`. Les deux variables sont déjà "
            "sur une échelle 0-100. Ce poids égal reprend le modèle de régression de l'étape 5 "
            "de l'EDA, où récupération et qualité de sommeil expliquent l'essentiel du score "
            "Whoop (R² 0,74-0,78 selon le joueur)."
        )

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        rolling = daily.loc[deb - timedelta(days=7):ref].copy()
        rolling["etat_forme_roll"] = (0.5 * rolling["recup"] + 0.5 * rolling["sommeil_perf"]).rolling(7, min_periods=3).mean()
        fig = line_chart(rolling.loc[deb:ref], ["etat_forme_roll"], [ACCENT], ["État de forme (moy. 7 j)"],
                          "État de forme — évolution", height=300)
        for _, r in (episodes.iterrows() if not episodes.empty else []):
            if r["fin"] >= deb and r["debut"] <= ref:
                fig.add_vrect(x0=max(r["debut"], deb), x1=min(r["fin"], ref),
                              fillcolor=ACCENT, opacity=0.12, line_width=0)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        st.caption("Bandes rouges = fenêtres à surveiller détectées (notebook 10).")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_r:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        n_port = int(seg["bracelet_porte"].sum())
        n_tot = len(seg)
        fig = go.Figure(go.Pie(
            labels=["Jours suivis", "Sans donnée"], values=[n_port, n_tot - n_port], hole=0.68,
            marker=dict(colors=[TEAL, "#2a2a30"]), textinfo="none",
        ))
        fig.add_annotation(text=f"{n_port}/{n_tot}", x=0.5, y=0.5, showarrow=False,
                            font=dict(size=22, color=TEXT))
        fig.update_layout(height=220, showlegend=True,
                           legend=dict(orientation="h", y=-0.1, font=dict(size=10)), **PLOTLY_LAYOUT)
        st.markdown('<div class="eyebrow">État global</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### Fenêtres à surveiller")
    fen_periode = episodes[(episodes["fin"] >= deb) & (episodes["debut"] <= ref)] if not episodes.empty else pd.DataFrame()
    episode_badges(fen_periode)

# =================================================================== PAGE 2
elif page == "Joueur 360":
    deb, ref, fenetre = period_selector("_360")
    seg = daily.loc[deb:ref]

    st.markdown(f'<div class="eyebrow">{info["label"].upper()} / JOUEUR 360</div><h1 style="margin-top:-6px;">VUE D\'ENSEMBLE</h1>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.plotly_chart(line_chart(seg, ["recup"], [ACCENT], ["Récupération"], "Récupération (0-100)"),
                         width='stretch', config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.plotly_chart(line_chart(seg, ["hrv"], [TEAL], ["HRV"], "HRV (ms)"),
                         width='stretch', config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        seg2 = seg.copy()
        seg2["sommeil_h"] = seg2["sommeil_min"] / 60
        seg2["besoin_h"] = seg2["besoin_min"] / 60
        st.plotly_chart(line_chart(seg2, ["sommeil_h", "besoin_h"], [TEAL, AMBER],
                                    ["Sommeil obtenu", "Besoin estimé"], "Sommeil vs besoin (h)"),
                         width='stretch', config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.plotly_chart(line_chart(seg, ["fc_repos"], [ACCENT], ["FC repos"], "FC repos (bpm)"),
                         width='stretch', config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Charge d\'entraînement</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=seg.index, y=seg["strain_seances"], name="Charge du jour", marker_color="#3a3a42"))
    fig.add_trace(go.Scatter(x=seg.index, y=seg["chronique"], name="Charge chronique (28j)", line=dict(color=AMBER, width=2)))
    fig2 = go.Figure(go.Scatter(x=seg.index, y=seg["acwr"], name="ACWR", line=dict(color=ACCENT, width=2)))
    fig2.add_hrect(y0=0.8, y1=1.3, fillcolor=TEAL, opacity=0.12, line_width=0)
    fig2.add_hline(y=1.5, line_dash="dash", line_color=ACCENT)
    col_a, col_b = st.columns(2)
    with col_a:
        fig.update_layout(height=260, title="Charge quotidienne vs chronique", **PLOTLY_LAYOUT)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    with col_b:
        fig2.update_layout(height=260, title="ACWR (bande verte = zone habituelle)", **PLOTLY_LAYOUT)
        st.plotly_chart(fig2, width='stretch', config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    jrn_cols = journal_exploitable_cols(daily)
    if jrn_cols:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">Journal comportemental — questions exploitables</div>', unsafe_allow_html=True)
        taux = (seg[jrn_cols].mean(numeric_only=True) * 100).sort_values(ascending=False)
        fig = go.Figure(go.Bar(x=taux.values, y=[c.replace("jrn_", "") for c in taux.index],
                                orientation="h", marker_color=TEAL))
        fig.update_layout(height=max(220, 26 * len(taux)), xaxis_title="% de oui sur la période",
                           **PLOTLY_LAYOUT)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Journal comportemental sans variance exploitable pour ce joueur (voir étape 9 de l'EDA).")

# =================================================================== PAGE 3
elif page == "Détection d'anomalies":
    st.markdown(f'<div class="eyebrow">{info["label"].upper()} / SANTÉ</div><h1 style="margin-top:-6px;">DÉTECTION D\'ANOMALIES</h1>',
                unsafe_allow_html=True)
    st.caption("Reprend telle quelle la méthode du notebook 10 : deux détecteurs (aigu / progressif) "
               "+ un angle indépendant (absence de football). Aucune fenêtre n'est une blessure confirmée.")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily.index, y=daily["lisse_aigu"], name="Score aigu (30 j)", line=dict(color=ACCENT, width=1.6)))
    fig.add_trace(go.Scatter(x=daily.index, y=daily["lisse_prog"], name="Score progressif (saison)", line=dict(color=TEAL, width=1.6)))
    for _, r in episodes.iterrows():
        fig.add_vrect(x0=r["debut"], x1=r["fin"], fillcolor=AMBER, opacity=0.12, line_width=0)
    fig.update_layout(height=320, title="Score de déviation quotidien", **PLOTLY_LAYOUT)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### Toutes les fenêtres détectées")
    episode_badges(episodes)

    st.markdown("#### Absence de football")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    fig = go.Figure(go.Bar(x=daily.index, y=daily["seance_foot"].fillna(False).astype(int),
                            marker_color=TEAL, name="Jour avec foot"))
    fig.update_layout(height=140, showlegend=False, yaxis=dict(visible=False), **PLOTLY_LAYOUT)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)
    if not ecarts_foot.empty:
        show = ecarts_foot.copy()
        show["debut"] = show["debut"].dt.strftime("%d %b %Y")
        show["fin"] = show["fin"].dt.strftime("%d %b %Y")
        st.dataframe(show, width='stretch', hide_index=True)

# =================================================================== PAGE 4
elif page == "Fuseau horaire":
    st.markdown(f'<div class="eyebrow">{info["label"].upper()} / VOYAGES</div><h1 style="margin-top:-6px;">FUSEAU HORAIRE</h1>',
                unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    fig = go.Figure(go.Scatter(x=daily.index, y=daily["tz_offset"], mode="lines+markers",
                                line=dict(color=ACCENT, width=1.6), marker=dict(size=3)))
    fig.update_layout(height=260, title="Décalage horaire (UTC) au fil du temps", **PLOTLY_LAYOUT)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    if athlete_key == "athlete1":
        st.info("Fuseau habituel France (+1 hiver / +2 été) ; grand voyage aux États-Unis en février 2026 "
                "(6 h de décalage) ; 2 longs séjours à l'étranger de 51 et 52 jours en été. Voir notebook 11.")
    else:
        st.info("Fuseau fixe à l'année (UTC+3, pas d'heure d'été) ; un seul déplacement progressif de "
                "68 jours à l'été 2025 (2 h de décalage maximum), sans effet santé mesurable. Voir notebook 11.")

    if not segments_tz.empty:
        show = segments_tz.copy()
        show["debut"] = show["debut"].dt.strftime("%d %b %Y")
        show["fin"] = show["fin"].dt.strftime("%d %b %Y")
        st.dataframe(show, width='stretch', hide_index=True)

# =================================================================== PAGE 5
elif page == "Comparaison":
    st.markdown('<div class="eyebrow">DEUX JOUEURS</div><h1 style="margin-top:-6px;">COMPARAISON</h1>', unsafe_allow_html=True)
    st.caption("2 joueurs seulement : chaque similitude est une hypothèse à tester sur un 3e cas, pas une règle.")

    d1 = load_daily("athlete1")
    d2 = load_daily("joueur2")
    p1 = d1[d1["bracelet_porte"]]
    p2 = d2[d2["bracelet_porte"]]

    rows = [
        ("Couverture bracelet", f'{d1["bracelet_porte"].mean()*100:.0f} %', f'{d2["bracelet_porte"].mean()*100:.0f} %'),
        ("Jours avec séance de foot", f'{d1["seance_foot"].mean()*100:.0f} %', f'{d2["seance_foot"].mean()*100:.0f} %'),
        ("Nuits sous le besoin de sommeil", f'{(p1["ecart_besoin_sommeil"]<0).mean()*100:.0f} %', f'{(p2["ecart_besoin_sommeil"]<0).mean()*100:.0f} %'),
        ("Déficit de sommeil médian", f'{p1["ecart_besoin_sommeil"].median():.0f} min', f'{p2["ecart_besoin_sommeil"].median():.0f} min'),
        ("Récupération moyenne*", f'{p1["recup"].mean():.1f}', f'{p2["recup"].mean():.1f}'),
        ("Charge hebdo médiane", f'{p1["strain_seances"].resample("W").sum().median():.0f} AU', f'{p2["strain_seances"].resample("W").sum().median():.0f} AU'),
        ("ACWR en zone sûre (0,8-1,3)", f'{d1["acwr"].between(0.8,1.3).mean()*100:.0f} %', f'{d2["acwr"].between(0.8,1.3).mean()*100:.0f} %'),
        ("Fenêtres à risque détectées", f'{len(load_episodes("athlete1"))}', f'{len(load_episodes("joueur2"))}'),
    ]
    df_compare = pd.DataFrame(rows, columns=["Indicateur", "Athlète 1", "Joueur 2"])
    st.dataframe(df_compare, width='stretch', hide_index=True)
    st.caption("*Récupération et HRV ne sont pas comparables en valeur absolue entre deux personnes "
               "(dépendent de l'algorithme et de la physiologie individuelle) — seules les proportions et corrélations le sont.")

    metrics = ["Couverture\nbracelet", "Jours avec\nfoot", "Nuits sous\nbesoin sommeil", "ACWR en\nzone sûre"]
    v1 = [d1["bracelet_porte"].mean()*100, d1["seance_foot"].mean()*100,
          (p1["ecart_besoin_sommeil"]<0).mean()*100, d1["acwr"].between(0.8,1.3).mean()*100]
    v2 = [d2["bracelet_porte"].mean()*100, d2["seance_foot"].mean()*100,
          (p2["ecart_besoin_sommeil"]<0).mean()*100, d2["acwr"].between(0.8,1.3).mean()*100]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=metrics, x=v1, name="Athlète 1", orientation="h", marker_color=ACCENT))
    fig.add_trace(go.Bar(y=metrics, x=v2, name="Joueur 2", orientation="h", marker_color=TEAL))
    fig.update_layout(barmode="group", height=340, xaxis_title="%", **PLOTLY_LAYOUT)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### Ce qui se répète")
    st.markdown("- Le sommeil est insuffisant chez les deux (signal le plus net des deux études).\n"
                "- L'ACWR ne prédit la récupération chez aucun des deux.\n"
                "- L'effet retardé le plus robuste de la charge porte sur la FC de repos du lendemain, pas la récupération.")
    st.markdown("#### Ce qui diffère")
    st.markdown("- Déficit de sommeil deux fois plus sévère chez le joueur 2.\n"
                "- Charge plus lourde et beaucoup moins variée chez le joueur 2 (risque de monotonie).\n"
                "- Coupure de foot de 9 semaines suspecte chez l'athlète 1 ; rien de comparable chez le joueur 2.\n"
                "- Fuseau horaire pertinent pour l'athlète 1 (heure d'été + grand voyage), quasi hors sujet pour le joueur 2.")

# =================================================================== PAGE 6
elif page == "Méthodologie":
    st.markdown('<div class="eyebrow">TRANSPARENCE</div><h1 style="margin-top:-6px;">MÉTHODOLOGIE</h1>', unsafe_allow_html=True)
    st.markdown(
        """
**Origine des données.** Export Whoop brut (4 fichiers CSV par joueur : cycles physiologiques,
sommeils, séances, journal). Aucune valeur n'est modifiée — seuls les en-têtes du joueur 2
(export en français) ont été traduits positionnellement vers le même schéma que l'athlète 1.

**Instance publique.** Ce dépôt ne contient que les tables déjà agrégées et anonymisées
(scores quotidiens, fenêtres détectées, segments de fuseau) — aucun export Whoop brut, aucun
notebook, aucun nom. Le pipeline complet (11 notebooks, données sources) vit dans un dépôt
privé séparé.

**Pipeline.** 11 notebooks, exécutés à l'identique sur les deux joueurs :
1-3 chargement, contrôle qualité, table analytique · 4-5 descriptif et corrélations ·
6-7 normalisation et structure multivariée · 8 charge d'entraînement · 9 synthèse ·
10 détection d'anomalies · 11 analyse de fuseau horaire.

**Ce dashboard ne recalcule rien** : il lit les tables et graphiques déjà produits par ces
notebooks (`outputs/interim/*.pkl`, `outputs/*.csv`). Le seul calcul propre à l'interface est
le score « État de forme » (0,5 × récupération + 0,5 × performance de sommeil), documenté
sur la page Command Center.

**Limites à garder à l'esprit :**
- Whoop ne loggue aucune blessure ni maladie — les fenêtres « à surveiller » sont des hypothèses
  statistiques, pas des diagnostics.
- 2 joueurs seulement : aucune conclusion n'est généralisable à un groupe.
- Récupération, HRV et les autres indices Whoop ne sont pas comparables en valeur absolue
  entre deux personnes (algorithme + physiologie individuelle) — seules les proportions,
  corrélations et évolutions relatives le sont.
- Les deux périodes ne se recouvrent pas complètement et n'ont pas la même longueur.

**Documents complets** (synthèses métier, comparaison détaillée, rapport technique) : disponibles
séparément, non inclus dans cette instance publique.
        """
    )
    if not dico.empty:
        with st.expander("Dictionnaire de données complet de ce joueur"):
            st.dataframe(dico, width='stretch', hide_index=True)
