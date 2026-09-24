"""Advent+ Africa Brand Scorecard landing page."""

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
    compute_scores,
    init_state,
)
from database import database_backend


def section_heading(eyebrow: str, title: str, description: str = "") -> None:
    content = (
        '<div class="section-heading">'
        f'<div class="section-heading__eyebrow">{eyebrow}</div>'
        f"<h2>{title}</h2>"
    )
    if description:
        content += f"<p>{description}</p>"
    st.markdown(content + "</div>", unsafe_allow_html=True)


st.set_page_config(
    page_title="Advent+ Africa · Brand Intelligence",
    page_icon=str(LOGO_MARK_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()
st.logo(str(LOGO_PATH), icon_image=str(LOGO_MARK_PATH))
init_state()

st.markdown(
    """
    <div class="home-hero">
      <div class="home-hero__content">
        <div class="eyebrow">Advent+ Africa · Decision workspace</div>
        <h1>Brand decisions,<br>made clearer.</h1>
        <p>Evaluate brands with one consistent framework, compare strategic fit,
        and turn assessments into clear portfolio recommendations.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

action_left, action_right, _ = st.columns([1.15, 1, 2.2], gap="small")
with action_left:
    if st.button("Open the scorecard  →", type="primary", use_container_width=True):
        st.switch_page("pages/Scorecard.py")
with action_right:
    st.link_button("View scoring source", MINDMAP_SOURCE, use_container_width=True)

portfolio = st.session_state.portfolio_df
portfolio = portfolio.loc[
    portfolio["Brand name"].notna()
    & portfolio["Brand name"].astype(str).str.strip().ne("")
].copy()
scored = compute_scores(
    portfolio,
    st.session_state.weights,
    st.session_state.use_weighted,
    st.session_state.thresholds,
)

section_heading(
    "Live portfolio",
    "Workspace at a glance",
    "A quick view of the assessments already saved in the workspace.",
)
metric_columns = st.columns(4, gap="medium")
metric_columns[0].metric("Brands in portfolio", len(scored))
metric_columns[1].metric(
    "Scored brands",
    int((scored["Descriptive score"].notna() | scored["Strategic score"].notna()).sum())
    if not scored.empty else 0,
)
metric_columns[2].metric(
    "Ready for review",
    int(scored["Status"].eq("Ready for review").sum()) if not scored.empty else 0,
)
metric_columns[3].metric(
    "Priority recommendations",
    int(scored["Recommendation"].eq("Priority").sum()) if not scored.empty else 0,
)

section_heading(
    "How it works",
    "One flow from assessment to decision",
    "The same definitions and thresholds are used across every brand.",
)
step_columns = st.columns(3, gap="medium")
steps = [
    (
        "01 / CAPTURE", "Assess the brand",
        "Record category, brand profile, market fit, operational capacity and supporting evidence.",
    ),
    (
        "02 / ANALYSE", "Compare the scores",
        "Review descriptive strength and strategic fit separately, then compare brands side by side.",
    ),
    (
        "03 / DECIDE", "Share a recommendation",
        "Use the decision matrix, document the status and export a review-ready portfolio.",
    ),
]
for column, (number, title, description) in zip(step_columns, steps):
    with column:
        st.markdown(
            '<div class="step-card">'
            f'<div class="step-card__number">{number}</div>'
            f"<h3>{title}</h3><p>{description}</p>"
            "</div>",
            unsafe_allow_html=True,
        )

left, right = st.columns([1.48, 1], gap="large")
with left:
    section_heading("Recent view", "Portfolio snapshot")
    if scored.empty:
        st.info("No brands yet. Open the scorecard to create the first assessment.")
    else:
        snapshot = scored[
            [
                "Brand name", "Descriptive score", "Strategic score",
                "Recommendation", "Status",
            ]
        ].sort_values("Brand name").head(6)
        st.dataframe(
            snapshot.style.format(
                {"Descriptive score": "{:.2f}", "Strategic score": "{:+.2f}"},
                na_rep="—",
            ),
            use_container_width=True,
            hide_index=True,
            height=min(330, 66 + 35 * len(snapshot)),
        )
with right:
    section_heading("Methodology", "Built for consistent reviews")
    st.markdown(
        '<div class="callout-card">'
        f"<p><strong>{len(ALL_CRITERIA)} criteria</strong> across "
        f"{len(STRATEGIC_GROUPS)} strategic pillars.</p>"
        f"<p style='margin-top:.75rem'>"
        f"{len(DESCRIPTIVE_CRITERIA)} descriptive criteria score brand strength from 1 to 4. "
        f"{len(STRATEGIC_CRITERIA)} strategic criteria score fit from −2 to +2. "
        "Thresholds turn both results into a recommendation.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

connection_status = (
    f"{database_backend()} connected" if st.session_state.get("database_available")
    else "Session mode · database unavailable"
)
st.caption(f"{connection_status} · Brand Scorecard v{APP_VERSION} · Advent+ Africa")
