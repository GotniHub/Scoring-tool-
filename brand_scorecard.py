"""Advent+ Africa brand scorecard.

The scoring framework is aligned with the BRAND ANALYSIS MindManager map shared
for this project.  UI code is kept in this module so both the Streamlit page and
the standalone entry point use exactly the same scoring engine.
"""

from __future__ import annotations

import ast
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import (
    database_info,
    delete_assessment,
    initialize_database,
    load_assessments,
    load_setting,
    rename_assessment_status,
    save_setting,
    upsert_assessment,
    upsert_assessments,
)


APP_VERSION = "2.8"
ROOT_DIR = Path(__file__).resolve().parent
LOGO_PATH = ROOT_DIR / "LOGO.png"
LOGO_MARK_PATH = ROOT_DIR / "Logom.png"
MINDMAP_SOURCE = (
    "https://share.mindmanager.com/#publish/"
    "crPS52oBYDln6uaoz556mwVFSp8IEoF17WOyNBl6"
)

NAVY = "#182541"
BLUE = "#2C4694"
MID_BLUE = "#506BB4"
SILVER = "#B7BDC9"
PALE_BLUE = "#EEF2FF"
INK = "#152039"
MUTED = "#64748B"
GREEN = "#16856A"
AMBER = "#C47A18"
RED = "#C34343"
PROFILE_COLORS = [BLUE, GREEN, AMBER, RED, "#7C3AED", "#0891B2", "#DB2777", "#65A30D"]


# Mind-map hierarchy ---------------------------------------------------------
CATEGORIES_FAMILIES = {
    "Retail": ["Chocolate", "Biscuits", "Mixology", "Confectionery"],
    "Beverage": ["Topping", "Syrups", "Powder", "Concentrate", "Sparkling wines"],
    "Food service": ["Chocolate", "Vanilla / aroma", "Fruit purées", "Tart shells", "Adjacent"],
}
ADD_CATEGORY_OPTION = "Other / Add a new category"

DESCRIPTIVE_SCALES: dict[str, dict[str, int]] = {
    "Positioning": {
        "Discount brand": 1,
        "Mass-market brand": 2,
        "Premium brand": 3,
        "Iconic brand": 4,
    },
    "Sizing": {
        "S brand · up to €25M": 1,
        "M brand · €25M–€50M": 2,
        "L brand · €50M–€75M": 3,
        "XL brand · more than €75M": 4,
    },
    "Product Portfolio": {
        "S portfolio · 1–5 families": 1,
        "M portfolio · 6–10 families": 2,
        "L portfolio · 11–16 families": 3,
        "XL portfolio · more than 16 families": 4,
    },
    "Award / Recognition": {
        "No award or recognized label": 1,
        "Recognized label or local recognition": 2,
        "Notable national or sector award": 3,
        "Multiple international awards or iconic recognition": 4,
    },
    "Export Turnover (%)": {
        "0%–5%": 1,
        ">5%–10%": 2,
        ">10%–50%": 3,
        ">50%": 4,
    },
    "Country Presence": {
        "0–10 countries": 1,
        "11–20 countries": 2,
        "21–40 countries": 3,
        "More than 40 countries": 4,
    },
    "Export Structure": {
        "Basic · sales only": 1,
        "Medium · sales, customer service and logistics": 2,
        "Confirmed · dedicated export team or agent": 3,
        "Expert · full export organization with marketing support": 4,
    },
}

STRATEGIC_SCALES: dict[str, dict[str, int]] = {
    "Performance": {
        "Declining faster than the market": -2,
        "Declining in line with the market": -1,
        "Growing in line with the market": 1,
        "Growing faster than the market": 2,
    },
    "Product Acceptance": {
        "Product is misaligned with the market and quality is poor": -2,
        "Product is aligned with the market but quality is poor": -1,
        "Product is aligned with the market and quality is acceptable": 0,
        "Product is strongly aligned with the market and quality is acceptable": 1,
        "Product is strongly aligned with the market and quality is good": 2,
    },
    "DNA Convergence": {
        "No product know-how and no relevant network": -2,
        "Product and customer are known, but the offer fully competes with the portfolio": -1,
        "Product and customer are known; fit is neutral": 0,
        "Product and customer are known and a clear opportunity exists": 1,
        "GTM, product and opportunity are known, with a strategic advantage to develop": 2,
    },
    "Strategy Compatibility": {
        "No match with the portfolio, target countries or local capabilities": -2,
        "Limited match with the portfolio or target-country coverage": -1,
        "Partial fit that requires validation": 0,
        "Good fit with the portfolio and local teams or agents": 1,
        "Strong fit with the portfolio, priority countries and local capabilities": 2,
    },
    "Industrial Capacity for Volumes": {
        "No reliable capacity information": -2,
        "Up to 10% volume increase possible": -1,
        "Up to 25% volume increase possible": 0,
        "Up to 50% volume increase possible": 1,
        "Production can approximately double": 2,
    },
    "Logistics Capacity": {
        "No reliable logistics-capacity information": -2,
        "Up to 10% increase can be supported": -1,
        "Up to 25% increase can be supported": 0,
        "Up to 50% increase can be supported": 1,
        "Logistics can support approximately double the volume": 2,
    },
    "Human Resources": {
        "Critical dependency on one person or unavailable resources": -2,
        "Resources are difficult to mobilize": -1,
        "Normal working relationship and adequate availability": 0,
        "Dedicated manager": 1,
        "Dedicated cross-functional team": 2,
    },
    "Industrial Flexibility": {
        "No adaptation is possible": -2,
        "Adaptation is possible but requires substantial work": -1,
        "Adaptation is possible with advance planning": 0,
        "Flexible operating model": 1,
        "Tailor-made production is available": 2,
    },
    "Cashflow Capacity": {
        "No capacity to fund required investment": -2,
        "Limited investment capacity": -1,
        "Investment requires advance cashflow planning": 0,
        "Investment capacity exists with some restrictions": 1,
        "Investment is fully fundable from available cashflow": 2,
    },
    "Certifications": {
        "Products are not compliant with target requirements": -2,
        "No recognized quality certification": -1,
        "One relevant certification or credential": 0,
        "Two relevant certifications or credentials": 1,
        "Strong quality, sustainability, award and standards coverage": 2,
    },
    "Sales Relationship": {
        "Actively works against the proposed development": -2,
        "Poor pricing, product or customer-information flow": -1,
        "Normal commercial working relationship": 0,
        "Collaborative sales relationship": 1,
        "High involvement, initiative and joint ownership": 2,
    },
    "Marketing Relationship": {
        "No export marketing strategy or activity": -2,
        "No marketing support is allocated": -1,
        "Normal working relationship": 0,
        "Dedicated budget is allocated": 1,
        "Funded marketing plan with growth actions": 2,
    },
    "Data Relationship": {
        "Refuses to share relevant data": -2,
        "Data quality and communication are poor": -1,
        "Basic data flow": 0,
        "Full relevant-data sharing": 1,
        "Data, diagnosis and action plans are shared": 2,
    },
    "Organization Relationship": {
        "Poor organization and unwillingness to follow a process": -2,
        "Insufficient staff for the opportunity": -1,
        "Organization covers the basic requirements": 0,
        "Dedicated problem-solving contacts are available": 1,
        "Full collaboration with a strong department structure": 2,
    },
    "Financial Relationship": {
        "Material payment delays or disputes over amounts due": -2,
        "Recurring late payments": -1,
        "Invoices are paid according to agreed terms": 0,
        "Payments include agreed development expenses": 1,
        "Funds marketing, listing fees and flexible customer terms": 2,
    },
    "EBITDA / Profit": {
        "Structural losses and material financial risk": -2,
        "Temporary negative profitability": -1,
        "Positive but below-sector profitability": 0,
        "Profitability is in line with the sector": 1,
        "Profitability is above the sector": 2,
    },
    "Seniority": {
        "Less than 5 years": -2,
        "5–9 years": -1,
        "10–14 years": 0,
        "15–20 years": 1,
        "More than 20 years": 2,
    },
    "Complexity": {
        "No technical know-how and no market knowledge": -2,
        "Market knowledge but no technical know-how": -1,
        "Technical and market knowledge are available": 0,
        "Strong market knowledge with a limited technical gap": 1,
        "Strong market knowledge and strong technical know-how": 2,
    },
    "Energy": {
        "All teams must mobilize with a significant time commitment": -2,
        "Several teams must mobilize with a significant time commitment": -1,
        "Team mobilization and time commitment are acceptable": 0,
        "Minimal team mobilization with an acceptable time commitment": 1,
        "Minimal team mobilization and minimal time commitment": 2,
    },
    "Convergence": {
        "No relationship with the brand or current portfolio clients": -2,
        "Limited relationship with the brand or current clients": -1,
        "Neutral relationship with the brand and current clients": 0,
        "Positive relationship with the brand and current clients": 1,
        "Strategic, constructive relationship with the brand and current clients": 2,
    },
}

STRATEGIC_GROUPS = {
    "Attractiveness and strategic fit": [
        "Performance",
        "Product Acceptance",
        "DNA Convergence",
        "Strategy Compatibility",
    ],
    "Operation Capacity": [
        "Industrial Capacity for Volumes",
        "Logistics Capacity",
        "Human Resources",
        "Industrial Flexibility",
        "Cashflow Capacity",
        "Certifications",
    ],
    "Partnerships / Relationships": [
        "Sales Relationship",
        "Marketing Relationship",
        "Data Relationship",
        "Organization Relationship",
        "Financial Relationship",
    ],
    "Solvability": ["EBITDA / Profit", "Seniority"],
    "Execution fit": ["Complexity", "Energy", "Convergence"],
}

CRITERION_DESCRIPTIONS = {
    "Award / Recognition": "External recognition that supports brand attractiveness.",
    "Country Presence": "Number of countries where the brand is commercially present.",
    "Export Turnover (%)": "Percentage of turnover generated through export markets.",
    "Strategy Compatibility": (
        "Map the countries where the brand is present and test the overlap with the "
        "existing portfolio, local teams and agent network."
    ),
    "Operation Capacity": (
        "Industrial volume, logistics, people, flexibility, cashflow and certification readiness."
    ),
    "Partnerships / Relationships": (
        "Quality of collaboration across sales, marketing, data, organization and financials."
    ),
    "Solvability": "Profitability and operating history of the brand owner.",
    "Complexity": "Availability of market knowledge and technical know-how.",
    "Energy": "Team mobilization and time commitment required to develop the opportunity.",
    "Convergence": "Relationship with the brand and current portfolio clients.",
}

DESCRIPTIVE_CRITERIA = list(DESCRIPTIVE_SCALES)
STRATEGIC_CRITERIA = list(STRATEGIC_SCALES)
ALL_CRITERIA = DESCRIPTIVE_CRITERIA + STRATEGIC_CRITERIA
IDENTITY_COLUMNS = ["Brand name", "Commercial owner", "Strategic category", "Brand family"]
TRAILING_COLUMNS = ["Comments", "Status"]
INPUT_COLUMNS = IDENTITY_COLUMNS + ALL_CRITERIA + TRAILING_COLUMNS
STATUS_VALUES = ["To complete", "In progress", "Ready for review", "Validated"]
STATUS_ALIASES = {"Review required": "Ready for review"}
MULTI_VALUE_SEPARATOR = " | "

DEFAULT_WEIGHTS = {criterion: 1.0 for criterion in ALL_CRITERIA}
DEFAULT_THRESHOLDS = {
    "desc_low": 2.0,
    "desc_strong": 3.0,
    "desc_leading": 3.5,
    "strat_priority": 1.0,
    "strat_opportunity": 0.25,
    "strat_low": -0.25,
    "strat_reject": -1.0,
}

COLUMN_ALIASES = {
    "Brand Attractiveness": "Award / Recognition",
    "Export Turnover %": "Export Turnover (%)",
    "Country Location": "Country Presence",
    "Industrial Capacity for volume production": "Industrial Capacity for Volumes",
    "Logistic Capacity": "Logistics Capacity",
    "Financials Relationship": "Financial Relationship",
}


# Pure data and scoring helpers ---------------------------------------------
def empty_portfolio() -> pd.DataFrame:
    return pd.DataFrame(columns=INPUT_COLUMNS)


def migrate_portfolio(data: pd.DataFrame | None) -> pd.DataFrame:
    """Bring older CSV/XLSX exports into the v2 column model without losing data."""
    if data is None or not isinstance(data, pd.DataFrame):
        return empty_portfolio()
    result = data.copy()
    for old, new in COLUMN_ALIASES.items():
        if old in result.columns and new not in result.columns:
            result = result.rename(columns={old: new})
    for column in INPUT_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    result = result[INPUT_COLUMNS].copy()
    for column in ["Strategic category", "Brand family"]:
        result[column] = result[column].map(serialize_multi_value)
    result["Status"] = result["Status"].replace(STATUS_ALIASES)
    result["Status"] = result["Status"].where(result["Status"].isin(STATUS_VALUES), "To complete")
    return result


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if bool(pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value.strip() == ""


def parse_multi_value(value: Any) -> list[str]:
    """Read scalar, delimited, or list-like category/family values."""
    if isinstance(value, (list, tuple, set, np.ndarray, pd.Series)):
        raw_values = list(value)
    else:
        if _is_blank(value):
            return []
        text = str(value).strip()
        raw_values: list[Any]
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = ast.literal_eval(text)
            except (SyntaxError, ValueError):
                parsed = None
            raw_values = list(parsed) if isinstance(parsed, (list, tuple, set)) else [text]
        else:
            raw_values = re.split(r"\s*(?:\||;|,)\s*", text)

    values: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        if _is_blank(raw_value):
            continue
        cleaned = str(raw_value).strip()
        if cleaned and cleaned not in seen:
            values.append(cleaned)
            seen.add(cleaned)
    return values


def serialize_multi_value(value: Any) -> Any:
    """Store multi-select values as an interoperable CSV/Excel-safe string."""
    values = parse_multi_value(value)
    return MULTI_VALUE_SEPARATOR.join(values) if values else pd.NA


def normalize_category_names(values: Any) -> list[str]:
    """Return clean, unique custom category names while preserving their order."""
    normalized: list[str] = []
    seen = {category.casefold() for category in CATEGORIES_FAMILIES}
    for value in parse_multi_value(values):
        cleaned = value.strip()
        key = cleaned.casefold()
        if not cleaned or key in seen or cleaned == ADD_CATEGORY_OPTION:
            continue
        normalized.append(cleaned)
        seen.add(key)
    return normalized


def strategic_category_options(
    custom_categories: Any = None,
    portfolio: pd.DataFrame | None = None,
) -> list[str]:
    """Combine built-in, saved and already-used categories without duplicates."""
    options = list(CATEGORIES_FAMILIES)
    candidates = normalize_category_names(custom_categories)
    if isinstance(portfolio, pd.DataFrame) and "Strategic category" in portfolio.columns:
        candidates.extend(
            category
            for value in portfolio["Strategic category"]
            for category in parse_multi_value(value)
        )
    seen = {category.casefold() for category in options}
    for category in candidates:
        cleaned = str(category).strip()
        key = cleaned.casefold()
        if cleaned and key not in seen and cleaned != ADD_CATEGORY_OPTION:
            options.append(cleaned)
            seen.add(key)
    return options


def _unique_multi_values(series: pd.Series) -> list[str]:
    values = {item for value in series for item in parse_multi_value(value)}
    return sorted(values)


def _contains_any_multi_value(value: Any, selected: list[str]) -> bool:
    return bool(set(parse_multi_value(value)).intersection(selected))


def score_value(criterion: str, value: Any) -> float:
    """Resolve raw labels, legacy decorated labels and numeric imports."""
    if _is_blank(value):
        return np.nan
    scale = DESCRIPTIVE_SCALES.get(criterion) or STRATEGIC_SCALES.get(criterion)
    if scale is None:
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
        return numeric if numeric in set(scale.values()) else np.nan
    text = str(value).strip()
    if text in scale:
        return float(scale[text])
    decorated = re.search(r"Score\s*:\s*([+-]?\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if decorated:
        numeric = float(decorated.group(1))
        return numeric if numeric in set(scale.values()) else np.nan
    return np.nan


def score_matrix(data: pd.DataFrame, criteria: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            criterion: data[criterion].map(lambda value, c=criterion: score_value(c, value))
            for criterion in criteria
        },
        index=data.index,
    )


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    mask = ~np.isnan(values)
    if not mask.any() or np.sum(weights[mask]) <= 0:
        return np.nan
    return float(np.average(values[mask], weights=weights[mask]))


def descriptive_tier(score: float, thresholds: dict[str, float]) -> str:
    if pd.isna(score):
        return "Not assessed"
    if score < thresholds["desc_low"]:
        return "Low"
    if score < thresholds["desc_strong"]:
        return "Developing"
    if score < thresholds["desc_leading"]:
        return "Attractive"
    return "Leading"


def strategic_decision(score: float, thresholds: dict[str, float]) -> str:
    if pd.isna(score):
        return "Not assessed"
    if score >= thresholds["strat_priority"]:
        return "Priority"
    if score >= thresholds["strat_opportunity"]:
        return "Opportunity"
    if score >= thresholds["strat_low"]:
        return "Investigate"
    if score > thresholds["strat_reject"]:
        return "Low priority"
    return "Do not prioritize"


def matrix_recommendation(desc: float, strat: float, thresholds: dict[str, float]) -> str:
    if pd.isna(desc) or pd.isna(strat):
        return "Not assessed"
    attractive = desc >= thresholds["desc_strong"]
    opportunity = strat >= thresholds["strat_opportunity"]
    if attractive and opportunity:
        return "Priority"
    if attractive:
        return "Validate risks"
    if opportunity:
        return "Develop opportunity"
    return "Do not prioritize"


def compute_scores(
    data: pd.DataFrame,
    weights: dict[str, float] | None = None,
    use_weighted: bool = False,
    thresholds: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calculate descriptive, strategic and completeness results for every brand."""
    result = migrate_portfolio(data)
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    desc = score_matrix(result, DESCRIPTIVE_CRITERIA)
    strat = score_matrix(result, STRATEGIC_CRITERIA)

    if result.empty:
        for column in [
            "Descriptive score",
            "Strategic score",
            "Descriptive total",
            "Strategic total",
            "Descriptive tier",
            "Decision",
            "Recommendation",
            "Completeness (%)",
        ]:
            result[column] = pd.Series(dtype="float64" if "score" in column.lower() else "object")
        return result

    if use_weighted:
        desc_weights = np.array([weights[c] for c in DESCRIPTIVE_CRITERIA], dtype=float)
        strat_weights = np.array([weights[c] for c in STRATEGIC_CRITERIA], dtype=float)
        result["Descriptive score"] = desc.apply(
            lambda row: _weighted_mean(row.to_numpy(dtype=float), desc_weights), axis=1
        )
        result["Strategic score"] = strat.apply(
            lambda row: _weighted_mean(row.to_numpy(dtype=float), strat_weights), axis=1
        )
    else:
        result["Descriptive score"] = desc.mean(axis=1, skipna=True)
        result["Strategic score"] = strat.mean(axis=1, skipna=True)

    result["Descriptive total"] = desc.sum(axis=1, min_count=1)
    result["Strategic total"] = strat.sum(axis=1, min_count=1)
    result["Descriptive tier"] = result["Descriptive score"].map(
        lambda score: descriptive_tier(score, thresholds)
    )
    result["Decision"] = result["Strategic score"].map(
        lambda score: strategic_decision(score, thresholds)
    )
    result["Recommendation"] = result.apply(
        lambda row: matrix_recommendation(
            row["Descriptive score"], row["Strategic score"], thresholds
        ),
        axis=1,
    )
    assessed = pd.concat([desc, strat], axis=1).notna().sum(axis=1)
    result["Completeness (%)"] = (assessed / len(ALL_CRITERIA) * 100).round(0)
    return result


def group_score_matrix(data: pd.DataFrame) -> pd.DataFrame:
    scored_groups: dict[str, pd.Series] = {}
    for group, criteria in STRATEGIC_GROUPS.items():
        scored_groups[group] = score_matrix(data, criteria).mean(axis=1, skipna=True)
    return pd.DataFrame(scored_groups, index=data.index)


def criteria_table() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for criterion, scale in DESCRIPTIVE_SCALES.items():
        for label, score in scale.items():
            rows.append(
                {"Pillar": "Descriptive", "Criterion": criterion, "Definition": label, "Score": score}
            )
    for group, criteria in STRATEGIC_GROUPS.items():
        for criterion in criteria:
            for label, score in STRATEGIC_SCALES[criterion].items():
                rows.append(
                    {"Pillar": group, "Criterion": criterion, "Definition": label, "Score": score}
                )
    return pd.DataFrame(rows)


def build_excel_export(
    portfolio: pd.DataFrame,
    weights: dict[str, float],
    thresholds: dict[str, float],
    use_weighted: bool,
) -> bytes:
    """Build a formatted, audit-friendly multi-sheet Excel export."""
    scored = compute_scores(portfolio, weights, use_weighted, thresholds)
    framework = criteria_table()
    settings = pd.DataFrame(
        [{"Setting": "Calculation mode", "Value": "Weighted mean" if use_weighted else "Simple mean"}]
        + [{"Setting": f"Weight · {key}", "Value": value} for key, value in weights.items()]
        + [{"Setting": f"Threshold · {key}", "Value": value} for key, value in thresholds.items()]
    )
    methodology = pd.DataFrame(
        {
            "Item": ["Framework", "Source", "Descriptive scale", "Strategic scale", "Generated"],
            "Detail": [
                "Advent+ Africa Brand Analysis",
                MINDMAP_SOURCE,
                "1 (low) to 4 (leading)",
                "-2 (material risk) to +2 (strong fit)",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ],
        }
    )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        scored.to_excel(writer, sheet_name="Portfolio", index=False)
        ranking_columns = [
            "Brand name",
            "Commercial owner",
            "Strategic category",
            "Brand family",
            "Descriptive score",
            "Strategic score",
            "Completeness (%)",
            "Recommendation",
            "Status",
        ]
        scored.sort_values(
            ["Strategic score", "Descriptive score"], ascending=False, na_position="last"
        )[ranking_columns].to_excel(writer, sheet_name="Ranking", index=False)
        framework.to_excel(writer, sheet_name="Scoring framework", index=False)
        settings.to_excel(writer, sheet_name="Settings", index=False)
        methodology.to_excel(writer, sheet_name="Methodology", index=False)

        workbook = writer.book
        header = workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": NAVY, "border": 0, "valign": "vcenter"}
        )
        body = workbook.add_format({"font_color": INK, "valign": "top"})
        wrapped = workbook.add_format({"font_color": INK, "valign": "top", "text_wrap": True})
        score_format = workbook.add_format({"num_format": "0.00", "align": "right"})
        pct_format = workbook.add_format({"num_format": "0\"%\"", "align": "right"})
        source_format = workbook.add_format({"font_color": BLUE, "underline": 1})

        for sheet_name, dataframe in {
            "Portfolio": scored,
            "Ranking": scored[ranking_columns],
            "Scoring framework": framework,
            "Settings": settings,
            "Methodology": methodology,
        }.items():
            worksheet = writer.sheets[sheet_name]
            worksheet.hide_gridlines(2)
            worksheet.freeze_panes(1, 1 if sheet_name in {"Portfolio", "Ranking"} else 0)
            worksheet.set_row(0, 28, header)
            worksheet.set_default_row(21)
            worksheet.autofilter(0, 0, max(len(dataframe), 1), max(len(dataframe.columns) - 1, 0))
            for index, column in enumerate(dataframe.columns):
                values = dataframe[column].astype(str) if len(dataframe) else pd.Series(dtype=str)
                max_length = max([len(str(column)), *(values.map(len).head(250).tolist())])
                width = min(max(max_length + 2, 12), 44)
                cell_format = wrapped if width >= 35 else body
                if "score" in str(column).lower() or "total" in str(column).lower():
                    cell_format = score_format
                if column == "Completeness (%)":
                    cell_format = pct_format
                worksheet.set_column(index, index, width, cell_format)

        portfolio_ws = writer.sheets["Portfolio"]
        ranking_ws = writer.sheets["Ranking"]
        for worksheet, dataframe in [(portfolio_ws, scored), (ranking_ws, scored[ranking_columns])]:
            if len(dataframe):
                for score_column, minimum, maximum in [
                    ("Descriptive score", 1, 4),
                    ("Strategic score", -2, 2),
                    ("Completeness (%)", 0, 100),
                ]:
                    if score_column in dataframe.columns:
                        column = dataframe.columns.get_loc(score_column)
                        worksheet.conditional_format(
                            1,
                            column,
                            len(dataframe),
                            column,
                            {
                                "type": "3_color_scale",
                                "min_type": "num",
                                "min_value": minimum,
                                "min_color": "#F6C9C9",
                                "mid_type": "num",
                                "mid_value": (minimum + maximum) / 2,
                                "mid_color": "#FFF1BE",
                                "max_type": "num",
                                "max_value": maximum,
                                "max_color": "#BFE7D9",
                            },
                        )
        writer.sheets["Methodology"].write_url(2, 1, MINDMAP_SOURCE, source_format, "Open MindManager source")
    return output.getvalue()


# Streamlit presentation ----------------------------------------------------
def apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        :root {{ --navy: {NAVY}; --blue: {BLUE}; --ink: {INK}; --muted: {MUTED}; }}
        .stApp {{ background: linear-gradient(180deg, #F8FAFF 0%, #F4F6FA 100%); color: var(--ink);
            font-family: "Segoe UI", Arial, sans-serif; }}
        .block-container {{ max-width: 1440px; padding-top: 2.2rem; padding-bottom: 4rem; }}
        [data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #E5E9F2; }}
        [data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}
        h1, h2, h3 {{ color: var(--navy); letter-spacing: -0.025em; font-family: "Segoe UI", Arial, sans-serif; }}
        p, label, button, input, textarea, [data-testid="stCaptionContainer"] {{
            color: var(--muted); font-family: "Segoe UI", Arial, sans-serif; }}
        .app-hero {{
            background: linear-gradient(125deg, {NAVY} 0%, {BLUE} 72%, {MID_BLUE} 100%);
            border-radius: 22px; padding: 2.2rem 2.4rem; color: #FFFFFF;
            box-shadow: 0 18px 40px rgba(24, 37, 65, 0.16); margin-bottom: 1.5rem;
        }}
        .app-hero .eyebrow {{ font-size: .76rem; text-transform: uppercase; letter-spacing: .14em;
            font-weight: 700; opacity: .72; margin-bottom: .55rem; }}
        .app-hero h1 {{ color: #FFFFFF; margin: 0; font-size: 2.15rem; line-height: 1.12; }}
        .app-hero p {{ color: rgba(255,255,255,.78); max-width: 760px; margin: .7rem 0 0; font-size: 1rem; }}
        .section-note {{ border-left: 3px solid {BLUE}; background: #FFFFFF; border-radius: 0 12px 12px 0;
            padding: .85rem 1rem; color: {MUTED}; margin: .25rem 0 1rem; }}
        div[data-testid="stMetric"] {{ background: #FFFFFF; border: 1px solid #E4E9F2; border-radius: 16px;
            padding: 1rem 1.05rem; box-shadow: 0 8px 24px rgba(24,37,65,.055); }}
        div[data-testid="stMetric"] label {{ color: {MUTED}; font-weight: 600; }}
        div[data-testid="stMetricValue"] {{ color: {NAVY}; font-weight: 700; }}
        div[data-testid="stForm"], div[data-testid="stExpander"] {{
            background: rgba(255,255,255,.92); border: 1px solid #E4E9F2; border-radius: 16px;
        }}
        .stButton > button, .stDownloadButton > button {{ border-radius: 10px; font-weight: 650; min-height: 2.7rem; }}
        .stButton > button[kind="primary"] {{ background: {BLUE}; border-color: {BLUE}; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: .45rem; background: #EDF1F7; border-radius: 12px; padding: .35rem; }}
        .stTabs [data-baseweb="tab"] {{ border-radius: 9px; padding: .55rem .9rem; }}
        .stTabs [aria-selected="true"] {{ background: #FFFFFF; color: {NAVY}; box-shadow: 0 3px 10px rgba(24,37,65,.08); }}
        [data-testid="stDataFrame"] {{ border: 1px solid #E4E9F2; border-radius: 14px; overflow: hidden; }}
        .score-legend {{ display:flex; gap:.8rem; flex-wrap:wrap; font-size:.82rem; color:{MUTED}; margin:.5rem 0 1rem; }}
        .score-legend span {{ background:#FFFFFF; border:1px solid #E4E9F2; border-radius:999px; padding:.35rem .65rem; }}
        a {{ color: {BLUE}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, description: str, eyebrow: str = "Brand intelligence") -> None:
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="eyebrow">{eyebrow}</div>
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    if not st.session_state.get("database_loaded"):
        legacy_data = st.session_state.get("portfolio_df", st.session_state.get("brands_df"))
        legacy_portfolio = migrate_portfolio(legacy_data)
        try:
            initialize_database()
            rename_assessment_status("Review required", "Ready for review")
            persisted = migrate_portfolio(pd.DataFrame(load_assessments()))
            if persisted.empty and not legacy_portfolio.empty:
                upsert_assessments(legacy_portfolio.to_dict(orient="records"))
                persisted = migrate_portfolio(pd.DataFrame(load_assessments()))
            st.session_state.portfolio_df = persisted
            stored_settings = load_setting("scorecard_configuration", {}) or {}
            st.session_state.weights = {
                **DEFAULT_WEIGHTS,
                **stored_settings.get("weights", st.session_state.get("weights", {})),
            }
            st.session_state.thresholds = {
                **DEFAULT_THRESHOLDS,
                **stored_settings.get("thresholds", st.session_state.get("thresholds", {})),
            }
            st.session_state.use_weighted = bool(
                stored_settings.get("use_weighted", st.session_state.get("use_weighted", False))
            )
            st.session_state.custom_strategic_categories = normalize_category_names(
                load_setting("strategic_categories", [])
            )
            st.session_state.database_available = True
            st.session_state.database_error = None
        except Exception as exc:  # database boundary; session mode remains usable
            st.session_state.portfolio_df = legacy_portfolio
            st.session_state.weights = {**DEFAULT_WEIGHTS, **st.session_state.get("weights", {})}
            st.session_state.thresholds = {**DEFAULT_THRESHOLDS, **st.session_state.get("thresholds", {})}
            st.session_state.use_weighted = bool(st.session_state.get("use_weighted", False))
            st.session_state.custom_strategic_categories = normalize_category_names(
                st.session_state.get("custom_strategic_categories", [])
            )
            st.session_state.database_available = False
            st.session_state.database_error = str(exc)
        st.session_state.database_loaded = True
    else:
        st.session_state.portfolio_df = migrate_portfolio(st.session_state.portfolio_df)
        if "custom_strategic_categories" not in st.session_state:
            st.session_state.custom_strategic_categories = []


def _reload_database() -> None:
    st.session_state.portfolio_df = migrate_portfolio(pd.DataFrame(load_assessments()))


def _persist_configuration() -> None:
    if not st.session_state.get("database_available"):
        return
    save_setting(
        "scorecard_configuration",
        {
            "weights": st.session_state.weights,
            "thresholds": st.session_state.thresholds,
            "use_weighted": st.session_state.use_weighted,
        },
    )


def _portfolio_with_names() -> pd.DataFrame:
    portfolio = migrate_portfolio(st.session_state.portfolio_df)
    mask = portfolio["Brand name"].notna() & portfolio["Brand name"].astype(str).str.strip().ne("")
    return portfolio.loc[mask].reset_index(drop=True)


def _load_upload(uploaded: Any) -> tuple[pd.DataFrame | None, str | None]:
    try:
        payload = uploaded.getvalue()
        if uploaded.name.lower().endswith(".csv"):
            data = pd.read_csv(io.BytesIO(payload))
        else:
            workbook = pd.ExcelFile(io.BytesIO(payload))
            preferred = "Portfolio" if "Portfolio" in workbook.sheet_names else workbook.sheet_names[0]
            data = pd.read_excel(workbook, sheet_name=preferred)
        return migrate_portfolio(data), None
    except Exception as exc:  # user-facing boundary
        return None, f"The file could not be imported: {exc}"


def render_sidebar() -> str:
    st.logo(str(LOGO_PATH), icon_image=str(LOGO_MARK_PATH))
    st.sidebar.markdown("### Brand Scorecard")
    st.sidebar.caption(f"Decision workspace · v{APP_VERSION}")
    navigation = st.sidebar.radio(
        "Workspace",
        ["Overview", "Evaluate a brand", "Portfolio", "Comparative analysis", "Scoring framework", "Exports"],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    previous_weighting = bool(st.session_state.use_weighted)
    st.session_state.use_weighted = st.sidebar.toggle(
        "Weighted scoring",
        value=previous_weighting,
        help="Apply the criterion weights maintained in Scoring framework.",
    )
    if st.session_state.use_weighted != previous_weighting:
        _persist_configuration()

    if st.session_state.get("database_available"):
        info = database_info()
        st.sidebar.success(f"Database connected · {info['records']} brand(s)", icon="✅")
        if st.sidebar.button("Refresh database", use_container_width=True):
            _reload_database()
            st.rerun()
    else:
        st.sidebar.error("Database unavailable · session mode active")
        if st.session_state.get("database_error"):
            st.sidebar.caption(st.session_state.database_error)

    uploaded = st.sidebar.file_uploader("Import portfolio", type=["csv", "xlsx"])
    if uploaded is not None:
        fingerprint = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("last_upload") != fingerprint:
            imported, error = _load_upload(uploaded)
            if error:
                st.sidebar.error(error)
            else:
                if st.session_state.get("database_available"):
                    saved = upsert_assessments(imported.to_dict(orient="records"))
                    _reload_database()
                    st.sidebar.success(f"Imported and saved {saved} brand(s).")
                else:
                    st.session_state.portfolio_df = imported
                    st.sidebar.warning("Imported for this session only because the database is unavailable.")
                st.session_state.last_upload = fingerprint
    st.sidebar.caption("Source aligned with the shared BRAND ANALYSIS mind map.")
    return navigation


def _scored_portfolio() -> pd.DataFrame:
    return compute_scores(
        _portfolio_with_names(),
        st.session_state.weights,
        st.session_state.use_weighted,
        st.session_state.thresholds,
    )


def _style_figure(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": INK, "size": 12},
        margin={"l": 24, "r": 24, "t": 52, "b": 28},
        legend_title_text="",
        hoverlabel={"bgcolor": "#FFFFFF", "font_color": INK},
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor="#E7EBF2", zerolinecolor="#CBD3E1")
    fig.update_yaxes(gridcolor="#E7EBF2", zerolinecolor="#CBD3E1")
    return fig


def build_brand_profile_figure(data: pd.DataFrame) -> go.Figure:
    """Build one color-coded strategic radar trace for every supplied brand."""
    group_values = group_score_matrix(data)
    group_values.index = data["Brand name"].astype(str)
    categories = group_values.columns.tolist()
    fig = go.Figure()
    for index, (brand_name, scores) in enumerate(group_values.iterrows()):
        values = scores.fillna(0).tolist()
        color = PROFILE_COLORS[index % len(PROFILE_COLORS)]
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
        fig.add_trace(
            go.Scatterpolar(
                r=values + values[:1],
                theta=categories + categories[:1],
                fill="toself",
                mode="lines+markers",
                line={"color": color, "width": 3},
                marker={"color": color, "size": 6},
                fillcolor=f"rgba({red},{green},{blue},.10)",
                name=brand_name,
                hovertemplate="%{theta}: %{r:.2f}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [-2, 2], "gridcolor": "#DDE3ED"}},
        showlegend=True,
        title="Strategic profile comparison",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.03, "xanchor": "center", "x": 0.5},
    )
    return _style_figure(fig, 560)


def page_overview() -> None:
    render_hero(
        "Brand portfolio intelligence",
        "Assess brand attractiveness, strategic fit and execution readiness through one traceable scoring framework.",
        "Advent+ Africa",
    )
    scored = _scored_portfolio()
    if scored.empty:
        st.info("No brands have been evaluated yet. Open **Evaluate a brand** to create the first assessment.")
        cols = st.columns(4)
        cols[0].metric("Descriptive criteria", len(DESCRIPTIVE_CRITERIA))
        cols[1].metric("Strategic criteria", len(STRATEGIC_CRITERIA))
        cols[2].metric("Strategic pillars", len(STRATEGIC_GROUPS))
        cols[3].metric("Scoring scales", "2", help="Descriptive 1–4 and strategic −2 to +2")
        st.markdown(
            '<div class="section-note">The framework covers category and portfolio profile, market presence, '
            "export structure, operating capacity, relationships, solvability, complexity, energy and convergence.</div>",
            unsafe_allow_html=True,
        )
        return

    brand_names = scored["Brand name"].astype(str).tolist()
    selected_brands = st.multiselect(
        "Brands to display",
        brand_names,
        default=brand_names,
        help="Select one or more brands. Indicators, charts and recommendations update together.",
    )
    if not selected_brands:
        st.info("Select at least one brand to display its indicators.")
        return
    selected = scored[scored["Brand name"].astype(str).isin(selected_brands)].copy()

    st.subheader("Brand indicators")
    for brand_index, (_, brand) in enumerate(selected.iterrows()):
        with st.expander(str(brand["Brand name"]), expanded=brand_index == 0):
            details = []
            if not _is_blank(brand.get("Commercial owner")):
                details.append(f"Commercial owner: {brand['Commercial owner']}")
            if not _is_blank(brand.get("Strategic category")):
                details.append(f"Categories: {brand['Strategic category']}")
            if not _is_blank(brand.get("Brand family")):
                details.append(f"Families: {brand['Brand family']}")
            if details:
                st.caption(" · ".join(details))

            descriptive = brand["Descriptive score"]
            strategic = brand["Strategic score"]
            completeness = brand["Completeness (%)"]
            indicators = st.columns(3)
            indicators[0].metric(
                "Descriptive score",
                "Not assessed" if pd.isna(descriptive) else f"{descriptive:.2f} / 4",
            )
            indicators[1].metric(
                "Strategic score",
                "Not assessed" if pd.isna(strategic) else f"{strategic:+.2f}",
            )
            indicators[2].metric(
                "Completeness",
                "Not assessed" if pd.isna(completeness) else f"{completeness:.0f}%",
            )
            st.markdown("##### Score interpretation and recommendation")
            interpretation_indicators = st.columns(2)
            interpretation_indicators[0].metric(
                "Descriptive level",
                "Not assessed" if _is_blank(brand.get("Descriptive tier")) else str(brand["Descriptive tier"]),
            )
            interpretation_indicators[1].metric(
                "Strategic decision",
                "Not assessed" if _is_blank(brand.get("Decision")) else str(brand["Decision"]),
            )
            decision_indicators = st.columns(2)
            decision_indicators[0].metric(
                "Final recommendation",
                "Not assessed" if _is_blank(brand.get("Recommendation")) else str(brand["Recommendation"]),
            )
            decision_indicators[1].metric(
                "Assessment status",
                "Not assessed" if _is_blank(brand.get("Status")) else str(brand["Status"]),
            )

    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Decision matrix")
        matrix = selected.dropna(subset=["Descriptive score", "Strategic score"])
        fig = px.scatter(
            matrix,
            x="Descriptive score",
            y="Strategic score",
            color="Recommendation",
            text="Brand name",
            color_discrete_map={
                "Priority": GREEN,
                "Develop opportunity": MID_BLUE,
                "Validate risks": AMBER,
                "Do not prioritize": RED,
            },
        )
        fig.update_traces(marker={"size": 15, "line": {"width": 1.5, "color": "#FFFFFF"}}, textposition="top center")
        fig.add_hline(
            y=st.session_state.thresholds["strat_opportunity"],
            line_dash="dot",
            line_color=SILVER,
            annotation_text=f"Opportunity {st.session_state.thresholds['strat_opportunity']:+.2f}",
        )
        fig.add_vline(
            x=st.session_state.thresholds["desc_strong"],
            line_dash="dot",
            line_color=SILVER,
            annotation_text=f"Attractive {st.session_state.thresholds['desc_strong']:.2f}",
        )
        fig.update_xaxes(range=[0.8, 4.1], title="Descriptive score (1–4)")
        fig.update_yaxes(range=[-2.1, 2.1], title="Strategic score (−2 to +2)")
        st.plotly_chart(_style_figure(fig, 470), use_container_width=True)
    with right:
        st.subheader("Current recommendations")
        distribution = (
            selected["Recommendation"].value_counts().rename_axis("Recommendation").reset_index(name="Brands")
        )
        fig = px.bar(
            distribution,
            x="Brands",
            y="Recommendation",
            orientation="h",
            color="Recommendation",
            color_discrete_map={
                "Priority": GREEN,
                "Develop opportunity": MID_BLUE,
                "Validate risks": AMBER,
                "Do not prioritize": RED,
                "Not assessed": SILVER,
            },
            text="Brands",
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(_style_figure(fig, 310), use_container_width=True)
        top = selected.sort_values(["Strategic score", "Descriptive score"], ascending=False)
        recommendation_table = top[
            ["Brand name", "Descriptive score", "Descriptive tier", "Strategic score", "Decision", "Recommendation"]
        ].rename(columns={"Descriptive tier": "Descriptive level", "Decision": "Strategic decision"})
        st.dataframe(
            recommendation_table.style.format({"Descriptive score": "{:.2f}", "Strategic score": "{:+.2f}"}),
            use_container_width=True,
            hide_index=True,
        )


def _existing_value(row: pd.Series | None, column: str) -> Any:
    if row is None or column not in row or _is_blank(row[column]):
        return None
    return row[column]


def _option_index(criterion: str, current: Any) -> int:
    options = list((DESCRIPTIVE_SCALES.get(criterion) or STRATEGIC_SCALES[criterion]).keys())
    if current in options:
        return options.index(current) + 1
    current_score = score_value(criterion, current)
    if not pd.isna(current_score):
        for index, option in enumerate(options, start=1):
            if score_value(criterion, option) == current_score:
                return index
    return 0


def _criterion_select(criterion: str, row: pd.Series | None, prefix: str) -> str | None:
    scale = DESCRIPTIVE_SCALES.get(criterion) or STRATEGIC_SCALES[criterion]
    options: list[str | None] = [None, *scale.keys()]

    def format_option(value: str | None) -> str:
        if value is None:
            return "Not assessed"
        score = scale[value]
        return f"{score:+d}  ·  {value}" if criterion in STRATEGIC_SCALES else f"{score}  ·  {value}"

    return st.selectbox(
        criterion,
        options,
        index=_option_index(criterion, _existing_value(row, criterion)),
        format_func=format_option,
        key=f"{prefix}_{re.sub(r'[^a-z0-9]+', '_', criterion.lower()).strip('_')}",
        help=CRITERION_DESCRIPTIONS.get(criterion),
    )


def page_evaluate() -> None:
    render_hero(
        "Evaluate a brand",
        "Capture one consistent assessment across the full mind-map framework. Unassessed criteria remain blank and do not distort the average.",
        "Guided assessment",
    )
    delete_notice = st.session_state.get("delete_notice")
    if delete_notice:
        st.success(delete_notice)
        del st.session_state["delete_notice"]
    portfolio = _portfolio_with_names()
    brand_names = portfolio["Brand name"].astype(str).tolist()
    target = st.selectbox("Assessment", ["Create a new brand", *brand_names])
    row = None if target == "Create a new brand" else portfolio.loc[portfolio["Brand name"].astype(str).eq(target)].iloc[0]
    prefix = "new" if row is None else f"edit_{portfolio.index[portfolio['Brand name'].astype(str).eq(target)][0]}"

    category_options = strategic_category_options(
        st.session_state.get("custom_strategic_categories", []),
        portfolio,
    )
    default_categories = [
        category
        for category in parse_multi_value(_existing_value(row, "Strategic category"))
        if category in category_options
    ]
    category_widget_key = f"{prefix}_categories"
    pending_category_key = f"{prefix}_pending_category_selection"
    if pending_categories := st.session_state.pop(pending_category_key, None):
        st.session_state[category_widget_key] = pending_categories
    selected_category_values = st.multiselect(
        "Strategic categories",
        [*category_options, ADD_CATEGORY_OPTION],
        default=default_categories or (["Retail"] if row is None else []),
        key=category_widget_key,
        help=(
            "Select every strategic category in which the brand operates. "
            "Choose Other to create a category that will remain available in the database."
        ),
    )
    selected_categories = [
        category for category in selected_category_values if category != ADD_CATEGORY_OPTION
    ]

    if ADD_CATEGORY_OPTION in selected_category_values:
        add_category_left, add_category_right = st.columns([4, 1])
        new_category = add_category_left.text_input(
            "New strategic category",
            key=f"{prefix}_new_category",
            placeholder="Enter the category name",
        )
        add_category = add_category_right.button(
            "Add category",
            key=f"{prefix}_add_category",
            type="primary",
            use_container_width=True,
        )
        if add_category:
            cleaned_category = new_category.strip()
            existing_names = {category.casefold() for category in category_options}
            if not cleaned_category:
                st.error("Enter a category name before adding it.")
            elif cleaned_category.casefold() in existing_names:
                st.error("This strategic category already exists.")
            else:
                custom_categories = normalize_category_names(
                    [*st.session_state.get("custom_strategic_categories", []), cleaned_category]
                )
                st.session_state.custom_strategic_categories = custom_categories
                if st.session_state.get("database_available"):
                    save_setting("strategic_categories", custom_categories)
                    st.session_state.category_notice = (
                        f"{cleaned_category} was added permanently and is now selected."
                    )
                else:
                    st.session_state.category_notice = (
                        f"{cleaned_category} was added for this session. "
                        "Permanent saving requires the database connection."
                    )
                st.session_state[pending_category_key] = [
                    *selected_categories,
                    cleaned_category,
                ]
                st.rerun()

    category_notice = st.session_state.pop("category_notice", None)
    if category_notice:
        if st.session_state.get("database_available"):
            st.success(category_notice)
        else:
            st.warning(category_notice)

    custom_category_selected = any(
        category not in CATEGORIES_FAMILIES for category in selected_categories
    )
    valid_families = list(
        dict.fromkeys(
            family
            for category in selected_categories
            for family in CATEGORIES_FAMILIES.get(category, [])
        )
    )
    if custom_category_selected:
        valid_families = list(
            dict.fromkeys(
                [
                    *valid_families,
                    *(family for families in CATEGORIES_FAMILIES.values() for family in families),
                ]
            )
        )
    default_families = [
        family
        for family in parse_multi_value(_existing_value(row, "Brand family"))
        if family in valid_families
    ]

    with st.form(f"assessment_form_{prefix}", clear_on_submit=False):
        identity_left, identity_mid, identity_right = st.columns([1.35, 1, 0.8])
        brand_name = identity_left.text_input(
            "Brand name",
            value="" if row is None else str(_existing_value(row, "Brand name") or ""),
            placeholder="Enter the official brand name",
        )
        commercial_owner = identity_mid.text_input(
            "Commercial owner",
            value="" if row is None else str(_existing_value(row, "Commercial owner") or ""),
            placeholder="Commercial name",
            help="Identifies who owns or last reviewed the assessment.",
        )
        status_default = _existing_value(row, "Status")
        status_index = STATUS_VALUES.index(status_default) if status_default in STATUS_VALUES else 0
        status = identity_right.selectbox("Assessment status", STATUS_VALUES, index=status_index)
        brand_families = st.multiselect(
            "Brand families",
            valid_families,
            default=default_families,
            placeholder="Select one or more families",
            help=(
                "Available families are combined from every selected strategic category. "
                "For a custom category, all existing families are available."
            ),
        )

        tabs = st.tabs(["Brand profile", "Market fit", "Operations", "Relationships", "Solvability", "Execution fit"])
        values: dict[str, Any] = {}
        with tabs[0]:
            st.caption("Positioning, size, portfolio, recognition and export presence · descriptive scale 1–4")
            columns = st.columns(2)
            for index, criterion in enumerate(DESCRIPTIVE_CRITERIA):
                with columns[index % 2]:
                    values[criterion] = _criterion_select(criterion, row, prefix)
        with tabs[1]:
            st.caption("Brand attractiveness and compatibility · strategic scale −2 to +2")
            for criterion in STRATEGIC_GROUPS["Attractiveness and strategic fit"]:
                values[criterion] = _criterion_select(criterion, row, prefix)
        with tabs[2]:
            st.caption(CRITERION_DESCRIPTIONS["Operation Capacity"])
            columns = st.columns(2)
            for index, criterion in enumerate(STRATEGIC_GROUPS["Operation Capacity"]):
                with columns[index % 2]:
                    values[criterion] = _criterion_select(criterion, row, prefix)
        with tabs[3]:
            st.caption(CRITERION_DESCRIPTIONS["Partnerships / Relationships"])
            for criterion in STRATEGIC_GROUPS["Partnerships / Relationships"]:
                values[criterion] = _criterion_select(criterion, row, prefix)
        with tabs[4]:
            st.caption(CRITERION_DESCRIPTIONS["Solvability"])
            for criterion in STRATEGIC_GROUPS["Solvability"]:
                values[criterion] = _criterion_select(criterion, row, prefix)
        with tabs[5]:
            st.caption("Complexity, team energy and relationship convergence · strategic scale −2 to +2")
            for criterion in STRATEGIC_GROUPS["Execution fit"]:
                values[criterion] = _criterion_select(criterion, row, prefix)

        comments = st.text_area(
            "Comments and evidence",
            value="" if row is None else str(_existing_value(row, "Comments") or ""),
            placeholder="Capture assumptions, evidence, risks and next actions.",
        )
        submitted = st.form_submit_button(
            "Save assessment" if row is None else "Update assessment", type="primary", use_container_width=True
        )

    if row is not None:
        with st.expander("Delete this brand", icon="⚠️"):
            st.warning(
                f"This permanently removes {target} and its complete assessment from the database."
            )
            delete_confirmed = st.checkbox(
                f"I confirm that I want to delete {target}.",
                key=f"{prefix}_confirm_delete",
            )
            if st.button(
                "Delete brand permanently",
                disabled=not delete_confirmed,
                key=f"{prefix}_delete",
                use_container_width=True,
            ):
                try:
                    if st.session_state.get("database_available"):
                        deleted = delete_assessment(str(target))
                        _reload_database()
                    else:
                        current = migrate_portfolio(st.session_state.portfolio_df)
                        match = current["Brand name"].astype(str).str.casefold().eq(str(target).casefold())
                        deleted = bool(match.any())
                        st.session_state.portfolio_df = migrate_portfolio(
                            current.loc[~match].reset_index(drop=True)
                        )
                    st.session_state.delete_notice = (
                        f"{target} was permanently deleted."
                        if deleted
                        else f"{target} was already absent from the database."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"The brand could not be deleted from the database: {exc}")

    if submitted:
        cleaned_name = brand_name.strip()
        if not cleaned_name:
            st.error("Brand name is required.")
            return
        if not selected_categories:
            st.error("Select at least one strategic category.")
            return
        if not brand_families:
            st.error("Select at least one brand family.")
            return
        duplicate = portfolio["Brand name"].astype(str).str.casefold().eq(cleaned_name.casefold())
        if row is None and duplicate.any():
            st.error("A brand with this name already exists. Select it from the Assessment list to update it.")
            return
        record = {
            "Brand name": cleaned_name,
            "Commercial owner": commercial_owner.strip(),
            "Strategic category": serialize_multi_value(selected_categories),
            "Brand family": serialize_multi_value(brand_families),
            **values,
            "Comments": comments.strip(),
            "Status": status,
        }
        try:
            if st.session_state.get("database_available"):
                upsert_assessment(record, previous_name=None if row is None else str(target))
                _reload_database()
                st.success(f"Assessment saved to the database for {cleaned_name}.")
            else:
                current = migrate_portfolio(st.session_state.portfolio_df)
                if row is None:
                    current = pd.concat([current, pd.DataFrame([record])], ignore_index=True)
                else:
                    match = current["Brand name"].astype(str).eq(str(target))
                    current.loc[match, INPUT_COLUMNS] = pd.DataFrame(
                        [record], columns=INPUT_COLUMNS
                    ).iloc[0].values
                st.session_state.portfolio_df = migrate_portfolio(current)
                st.warning(f"Assessment saved for this session only: {cleaned_name}.")
        except Exception as exc:
            st.error(f"The assessment could not be saved to the database: {exc}")


def page_portfolio() -> None:
    render_hero(
        "Portfolio",
        "Review assessment completeness, decision status and the evidence captured for each brand.",
        "Portfolio register",
    )
    scored = _scored_portfolio()
    if scored.empty:
        st.info("No brands are available yet. Create an assessment first.")
        return
    filters = st.columns(5)
    categories = filters[0].multiselect("Category", _unique_multi_values(scored["Strategic category"]))
    families = filters[1].multiselect("Brand family", _unique_multi_values(scored["Brand family"]))
    owners = filters[2].multiselect("Commercial owner", sorted(scored["Commercial owner"].dropna().unique()))
    decisions = filters[3].multiselect("Recommendation", sorted(scored["Recommendation"].dropna().unique()))
    statuses = filters[4].multiselect("Status", sorted(scored["Status"].dropna().unique()))
    filtered = scored.copy()
    if categories:
        filtered = filtered[
            filtered["Strategic category"].map(lambda value: _contains_any_multi_value(value, categories))
        ]
    if families:
        filtered = filtered[
            filtered["Brand family"].map(lambda value: _contains_any_multi_value(value, families))
        ]
    if owners:
        filtered = filtered[filtered["Commercial owner"].isin(owners)]
    if decisions:
        filtered = filtered[filtered["Recommendation"].isin(decisions)]
    if statuses:
        filtered = filtered[filtered["Status"].isin(statuses)]
    view = filtered[
        [
            "Brand name",
            "Commercial owner",
            "Strategic category",
            "Brand family",
            "Descriptive score",
            "Strategic score",
            "Completeness (%)",
            "Recommendation",
            "Status",
            "Comments",
        ]
    ].sort_values(["Strategic score", "Descriptive score"], ascending=False).rename(
        columns={"Strategic category": "Strategic categories", "Brand family": "Brand families"}
    )
    st.dataframe(
        view.style.format(
            {"Descriptive score": "{:.2f}", "Strategic score": "{:+.2f}", "Completeness (%)": "{:.0f}%"},
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
        height=min(680, 92 + 36 * max(len(view), 1)),
    )
    st.caption("Use Evaluate a brand to edit an existing assessment. Imported legacy score labels remain supported.")


def page_analysis() -> None:
    render_hero(
        "Comparative analysis",
        "Compare brands at criterion and pillar level without losing the distinction between attractiveness and strategic fit.",
        "Portfolio analytics",
    )
    scored = _scored_portfolio()
    if scored.empty:
        st.info("No scored brands are available yet.")
        return
    selected = st.multiselect(
        "Brands to compare",
        scored["Brand name"].tolist(),
        default=scored["Brand name"].head(min(5, len(scored))).tolist(),
        max_selections=8,
    )
    if not selected:
        st.warning("Select at least one brand.")
        return
    subset = scored[scored["Brand name"].isin(selected)].copy()

    tabs = st.tabs(["Ranking", "Descriptive detail", "Strategic pillars", "Brand profile"])
    with tabs[0]:
        ranking = subset.sort_values("Strategic score")
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=ranking["Brand name"],
                x=ranking["Strategic score"],
                name="Strategic score",
                orientation="h",
                marker_color=[GREEN if value >= 0 else RED for value in ranking["Strategic score"].fillna(0)],
            )
        )
        fig.update_xaxes(range=[-2, 2], title="Strategic score")
        st.plotly_chart(_style_figure(fig, max(360, len(ranking) * 52)), use_container_width=True)
    with tabs[1]:
        heat = score_matrix(subset, DESCRIPTIVE_CRITERIA)
        heat.index = subset["Brand name"]
        fig = px.imshow(
            heat,
            zmin=1,
            zmax=4,
            color_continuous_scale=[[0, "#F5C2C2"], [0.5, "#FFF0B8"], [1, "#8FD5BF"]],
            text_auto=".0f",
            aspect="auto",
            labels={"color": "Score"},
        )
        st.plotly_chart(_style_figure(fig, max(380, len(heat) * 58)), use_container_width=True)
    with tabs[2]:
        groups = group_score_matrix(subset)
        groups.index = subset["Brand name"]
        fig = px.imshow(
            groups,
            zmin=-2,
            zmax=2,
            color_continuous_scale=[[0, "#D85B5B"], [0.5, "#F2F4F8"], [1, "#2BA67F"]],
            text_auto=".2f",
            aspect="auto",
            labels={"color": "Average"},
        )
        st.plotly_chart(_style_figure(fig, max(380, len(groups) * 58)), use_container_width=True)
    with tabs[3]:
        profile_brands = st.multiselect(
            "Brands in profile",
            selected,
            default=selected,
            key="profile_brands",
            help="Each selected brand is displayed on the same radar with a distinct color.",
        )
        if not profile_brands:
            st.info("Select at least one brand to display the strategic profile.")
        else:
            profile_subset = subset[subset["Brand name"].isin(profile_brands)]
            st.plotly_chart(build_brand_profile_figure(profile_subset), use_container_width=True)


def page_framework() -> None:
    render_hero(
        "Scoring framework",
        "Audit every criterion, definition and score used by the application. The framework includes all branches represented in the shared mind map.",
        "Methodology and settings",
    )
    st.markdown(
        '<div class="score-legend"><span>Descriptive: 1 low → 4 leading</span>'
        '<span>Strategic: −2 material risk → +2 strong fit</span>'
        f'<span>{len(ALL_CRITERIA)} criteria</span></div>',
        unsafe_allow_html=True,
    )
    st.link_button("Open the source mind map", MINDMAP_SOURCE)

    descriptive_tab, strategic_tab, settings_tab = st.tabs(["Descriptive criteria", "Strategic criteria", "Weights and thresholds"])
    with descriptive_tab:
        for criterion, scale in DESCRIPTIVE_SCALES.items():
            with st.expander(criterion):
                if criterion in CRITERION_DESCRIPTIONS:
                    st.caption(CRITERION_DESCRIPTIONS[criterion])
                st.dataframe(
                    pd.DataFrame([{"Definition": label, "Score": score} for label, score in scale.items()]),
                    use_container_width=True,
                    hide_index=True,
                )
    with strategic_tab:
        for group, criteria in STRATEGIC_GROUPS.items():
            st.subheader(group)
            if group in CRITERION_DESCRIPTIONS:
                st.caption(CRITERION_DESCRIPTIONS[group])
            for criterion in criteria:
                with st.expander(criterion):
                    if criterion in CRITERION_DESCRIPTIONS:
                        st.caption(CRITERION_DESCRIPTIONS[criterion])
                    st.dataframe(
                        pd.DataFrame(
                            [{"Definition": label, "Score": score} for label, score in STRATEGIC_SCALES[criterion].items()]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
    with settings_tab:
        st.caption("Weights apply only when Weighted scoring is enabled in the sidebar.")
        weight_frame = pd.DataFrame(
            {
                "Criterion": ALL_CRITERIA,
                "Pillar": [
                    "Descriptive" if criterion in DESCRIPTIVE_CRITERIA else next(
                        group for group, group_criteria in STRATEGIC_GROUPS.items() if criterion in group_criteria
                    )
                    for criterion in ALL_CRITERIA
                ],
                "Weight": [float(st.session_state.weights[criterion]) for criterion in ALL_CRITERIA],
            }
        )
        with st.form("framework_settings"):
            edited_weights = st.data_editor(
                weight_frame,
                column_config={
                    "Criterion": st.column_config.TextColumn(disabled=True),
                    "Pillar": st.column_config.TextColumn(disabled=True),
                    "Weight": st.column_config.NumberColumn(min_value=0.0, max_value=10.0, step=0.25),
                },
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
            )
            st.markdown("#### Descriptive level thresholds")
            updated_thresholds = st.session_state.thresholds.copy()
            descriptive_cols = st.columns(3)
            updated_thresholds["desc_low"] = descriptive_cols[0].number_input(
                "Developing from", 1.0, 4.0, float(updated_thresholds["desc_low"]), 0.1,
                help="A lower score is classified as Low.",
            )
            updated_thresholds["desc_strong"] = descriptive_cols[1].number_input(
                "Attractive from", 1.0, 4.0, float(updated_thresholds["desc_strong"]), 0.1,
                help="This boundary is also used by the final recommendation.",
            )
            updated_thresholds["desc_leading"] = descriptive_cols[2].number_input(
                "Leading from", 1.0, 4.0, float(updated_thresholds["desc_leading"]), 0.1
            )

            st.markdown("#### Strategic decision thresholds")
            strategic_cols = st.columns(4)
            updated_thresholds["strat_reject"] = strategic_cols[0].number_input(
                "Reject at or below", -2.0, 2.0, float(updated_thresholds["strat_reject"]), 0.05
            )
            updated_thresholds["strat_low"] = strategic_cols[1].number_input(
                "Investigate from", -2.0, 2.0, float(updated_thresholds["strat_low"]), 0.05
            )
            updated_thresholds["strat_opportunity"] = strategic_cols[2].number_input(
                "Opportunity from", -2.0, 2.0, float(updated_thresholds["strat_opportunity"]), 0.05,
                help="This boundary is also used by the final recommendation.",
            )
            updated_thresholds["strat_priority"] = strategic_cols[3].number_input(
                "Priority from", -2.0, 2.0, float(updated_thresholds["strat_priority"]), 0.05
            )
            save = st.form_submit_button("Save settings", type="primary")
        if save:
            if not (
                updated_thresholds["desc_low"]
                < updated_thresholds["desc_strong"]
                < updated_thresholds["desc_leading"]
            ):
                st.error("Descriptive thresholds must increase from Developing to Attractive to Leading.")
            elif not (
                updated_thresholds["strat_reject"]
                < updated_thresholds["strat_low"]
                < updated_thresholds["strat_opportunity"]
                < updated_thresholds["strat_priority"]
            ):
                st.error("Strategic thresholds must increase from reject to opportunity to priority.")
            else:
                st.session_state.weights = dict(zip(edited_weights["Criterion"], edited_weights["Weight"]))
                st.session_state.thresholds = updated_thresholds
                _persist_configuration()
                st.success("Scoring settings updated.")

        logic = st.session_state.thresholds
        st.markdown("#### Logic currently used")
        st.caption(
            "The final recommendation combines the editable Attractive and Opportunity boundaries shown above."
        )
        logic_left, logic_right = st.columns(2)
        with logic_left:
            st.markdown("**Descriptive level**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Result": "Leading", "Condition": f"Score ≥ {logic['desc_leading']:.2f}"},
                        {
                            "Result": "Attractive",
                            "Condition": f"{logic['desc_strong']:.2f} ≤ score < {logic['desc_leading']:.2f}",
                        },
                        {
                            "Result": "Developing",
                            "Condition": f"{logic['desc_low']:.2f} ≤ score < {logic['desc_strong']:.2f}",
                        },
                        {"Result": "Low", "Condition": f"Score < {logic['desc_low']:.2f}"},
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        with logic_right:
            st.markdown("**Strategic decision**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Result": "Priority", "Condition": f"Score ≥ {logic['strat_priority']:+.2f}"},
                        {
                            "Result": "Opportunity",
                            "Condition": (
                                f"{logic['strat_opportunity']:+.2f} ≤ score < {logic['strat_priority']:+.2f}"
                            ),
                        },
                        {
                            "Result": "Investigate",
                            "Condition": f"{logic['strat_low']:+.2f} ≤ score < {logic['strat_opportunity']:+.2f}",
                        },
                        {
                            "Result": "Low priority",
                            "Condition": f"{logic['strat_reject']:+.2f} < score < {logic['strat_low']:+.2f}",
                        },
                        {
                            "Result": "Do not prioritize",
                            "Condition": f"Score ≤ {logic['strat_reject']:+.2f}",
                        },
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("**Final recommendation**")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Descriptive result": "Attractive or Leading",
                        "Strategic result": "Opportunity or Priority",
                        "Final recommendation": "Priority",
                    },
                    {
                        "Descriptive result": "Attractive or Leading",
                        "Strategic result": "Below Opportunity",
                        "Final recommendation": "Validate risks",
                    },
                    {
                        "Descriptive result": "Low or Developing",
                        "Strategic result": "Opportunity or Priority",
                        "Final recommendation": "Develop opportunity",
                    },
                    {
                        "Descriptive result": "Low or Developing",
                        "Strategic result": "Below Opportunity",
                        "Final recommendation": "Do not prioritize",
                    },
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


def page_exports() -> None:
    render_hero(
        "Exports",
        "Share a clean portfolio extract or a complete Excel review pack with scores, rankings, methodology and settings.",
        "Reporting",
    )
    scored = _scored_portfolio()
    if scored.empty:
        st.info("No assessed brands are available to export.")
        return
    export_summary = scored[
        [
            "Brand name",
            "Descriptive score",
            "Descriptive tier",
            "Strategic score",
            "Decision",
            "Completeness (%)",
            "Recommendation",
        ]
    ].rename(columns={"Descriptive tier": "Descriptive level", "Decision": "Strategic decision"})
    st.dataframe(
        export_summary.style.format(
            {"Descriptive score": "{:.2f}", "Strategic score": "{:+.2f}", "Completeness (%)": "{:.0f}%"}
        ),
        use_container_width=True,
        hide_index=True,
    )
    csv_data = scored.to_csv(index=False).encode("utf-8-sig")
    excel_data = build_excel_export(
        _portfolio_with_names(), st.session_state.weights, st.session_state.thresholds, st.session_state.use_weighted
    )
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_col, xlsx_col = st.columns(2)
    csv_col.download_button(
        "Download CSV",
        csv_data,
        file_name=f"brand_scorecard_{stamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    xlsx_col.download_button(
        "Download Excel review pack",
        excel_data,
        file_name=f"brand_scorecard_{stamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )


def run_app() -> None:
    st.set_page_config(
        page_title="Brand Scorecard · Advent+ Africa",
        page_icon=str(LOGO_MARK_PATH),
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    init_state()
    navigation = render_sidebar()
    pages = {
        "Overview": page_overview,
        "Evaluate a brand": page_evaluate,
        "Portfolio": page_portfolio,
        "Comparative analysis": page_analysis,
        "Scoring framework": page_framework,
        "Exports": page_exports,
    }
    pages[navigation]()
    st.sidebar.divider()
    st.sidebar.caption(f"Advent+ Africa · Brand Scorecard v{APP_VERSION}")


if __name__ == "__main__":
    run_app()
