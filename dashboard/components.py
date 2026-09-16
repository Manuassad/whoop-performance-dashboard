# -*- coding: utf-8 -*-
"""Composants visuels réutilisables, dans l'esprit du Performance Command
Center (fond sombre, accent rouge, cartes, jauges circulaires)."""
import plotly.graph_objects as go
import streamlit as st

BG = "#0B0B0D"
CARD = "#151519"
CARD_BORDER = "#26262c"
ACCENT = "#E4002B"
TEAL = "#12C39A"
AMBER = "#E8A33D"
TEXT = "#F2F2F3"
MUTED = "#8C8C93"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=CARD,
    plot_bgcolor=CARD,
    font=dict(color=TEXT, family="Arial, sans-serif"),
    margin=dict(l=10, r=10, t=30, b=10),
)


def inject_css():
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {BG}; }}
        section[data-testid="stSidebar"] {{ background-color: #0F0F12; border-right: 1px solid {CARD_BORDER}; }}
        h1, h2, h3 {{ color: {TEXT} !important; font-weight: 800 !important; letter-spacing: .02em; }}
        p, span, label, div {{ color: {TEXT}; }}
        .muted {{ color: {MUTED} !important; font-size: 0.85rem; }}
        .eyebrow {{ color: {ACCENT}; font-weight: 700; letter-spacing: .12em; font-size: 0.78rem;
                    text-transform: uppercase; margin-bottom: 2px; }}
        .card {{ background-color: {CARD}; border: 1px solid {CARD_BORDER}; border-radius: 10px;
                 padding: 18px 20px; margin-bottom: 14px; }}
        .badge {{ display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 0.78rem;
                  font-weight: 700; letter-spacing: .03em; }}
        .badge-ok {{ background: rgba(18,195,154,0.15); color: {TEAL}; }}
        .badge-warn {{ background: rgba(232,163,61,0.18); color: {AMBER}; }}
        .badge-risk {{ background: rgba(228,0,43,0.18); color: {ACCENT}; }}
        .kpi-value {{ font-size: 2.4rem; font-weight: 800; color: {TEXT}; line-height: 1; }}
        .kpi-label {{ color: {MUTED}; font-size: 0.8rem; text-transform: uppercase; letter-spacing: .05em; }}
        .kpi-delta-up {{ color: {TEAL}; font-weight: 700; font-size: 0.85rem; }}
        .kpi-delta-down {{ color: {ACCENT}; font-weight: 700; font-size: 0.85rem; }}
        div[data-testid="stMetric"] {{ background-color: {CARD}; border: 1px solid {CARD_BORDER};
            border-radius: 10px; padding: 14px 16px; }}
        hr {{ border-color: {CARD_BORDER}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "ok") -> str:
    cls = {"ok": "badge-ok", "warn": "badge-warn", "risk": "badge-risk"}.get(kind, "badge-ok")
    return f'<span class="badge {cls}">{text}</span>'


def gauge(value: float, label: str, suffix: str = "", vmax: float = 100,
          color: str = ACCENT, spark_color: str = None) -> go.Figure:
    """Jauge circulaire compacte, façon 'ÉTAT DE FORME 79/100'."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": suffix, "font": {"size": 34, "color": TEXT}},
            gauge={
                "axis": {"range": [0, vmax], "visible": False},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "#232328",
                "borderwidth": 0,
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(height=150, **{**PLOTLY_LAYOUT, "margin": dict(l=6, r=6, t=6, b=6)})
    return fig


def section_title(eyebrow: str, title: str):
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.markdown(f"### {title}")
