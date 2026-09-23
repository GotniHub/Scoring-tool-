"""Advent+ Africa decision-workspace landing page."""

import streamlit as st

from brand_scorecard import (
    ALL_CRITERIA,
    APP_VERSION,
    DESCRIPTIVE_CRITERIA,
    LOGO_MARK_PATH,
    LOGO_PATH,
    MINDMAP_SOURCE,
    STRATEGIC_CRITERIA,
    STRATEGIC_GROUPS,
    apply_theme,
)


st.set_page_config(
    page_title="Advent+ Africa · Brand Intelligence",
    page_icon=str(LOGO_MARK_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()
st.logo(str(LOGO_PATH), icon_image=str(LOGO_MARK_PATH))

st.markdown(
    """
    <div class="app-hero">
        <div class="eyebrow">Advent+ Africa</div>
        <h1>Brand intelligence workspace</h1>
        <p>A structured decision tool for screening brand opportunities, comparing strategic fit and preparing portfolio reviews.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.35, 1], gap="large")
with left:
    st.subheader("From assessment to decision")
    st.write(
        "The scorecard translates the shared BRAND ANALYSIS mind map into one guided, auditable workflow. "
        "Every assessment separates descriptive brand strength from strategic and execution fit."
    )
    st.page_link("pages/Scorecard.py", label="Open Brand Scorecard", icon="📊")
    st.link_button("View source mind map", MINDMAP_SOURCE)

with right:
    metric_cols = st.columns(2)
    metric_cols[0].metric("Criteria", len(ALL_CRITERIA))
    metric_cols[1].metric("Strategic pillars", len(STRATEGIC_GROUPS))
    metric_cols[0].metric("Descriptive", len(DESCRIPTIVE_CRITERIA))
    metric_cols[1].metric("Strategic", len(STRATEGIC_CRITERIA))

st.divider()
cols = st.columns(3)
with cols[0]:
    st.markdown("### Assess")
    st.write("Capture category, market presence, export readiness and the full strategic framework.")
with cols[1]:
    st.markdown("### Compare")
    st.write("Rank brands, inspect criterion heatmaps and compare strategic pillars consistently.")
with cols[2]:
    st.markdown("### Share")
    st.write("Export a formatted Excel review pack with portfolio data, methodology and settings.")

st.caption(f"Brand Scorecard v{APP_VERSION} · Framework aligned with the shared MindManager source")
