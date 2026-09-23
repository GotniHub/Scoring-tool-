# Advent+ Africa Brand Scorecard

A Streamlit decision workspace that turns the shared **BRAND ANALYSIS** mind map into a structured brand-assessment workflow.

## Run locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run home.py
```

The app supports:

- guided assessments across all descriptive and strategic criteria;
- multi-select strategic categories, permanent custom category creation, and category-dependent brand families;
- persistent SQLite storage for every assessment and scoring configuration;
- a commercial-owner field for accountability and portfolio filtering;
- an Overview brand filter with collapsible indicators for every selected brand;
- simple or weighted scoring;
- decision matrices, rankings, heatmaps and pillar profiles;
- a color-coded multi-brand radar for strategic profile comparison;
- CSV and Excel portfolio imports;
- formatted Excel review-pack exports;
- legacy columns and score labels from the previous implementation.

## Database, import and export

The application uses `data/brand_scorecard.db` by default. It creates the database automatically on first launch.

- Saving or updating an assessment writes the complete record to the database.
- Deleting an existing brand requires explicit confirmation and removes its complete assessment.
- CSV/XLSX imports are merged into the database by brand name.
- Exports remain available for portfolio reviews, sharing and backups.
- Use **Refresh database** in the sidebar to load changes saved by another active session.

To store the database elsewhere, set `BRAND_SCORECARD_DB_PATH` before starting Streamlit:

```powershell
$env:BRAND_SCORECARD_DB_PATH = "D:\Data\brand_scorecard.db"
python -m streamlit run home.py
```

SQLite is appropriate for a local installation or a small team sharing one persistent server. For a stateless cloud deployment or heavier concurrent usage, migrate the storage layer to PostgreSQL.

## Scoring model

- **Descriptive score:** 1 (low) to 4 (leading).
- **Strategic score:** -2 (material risk) to +2 (strong fit).
- Missing criteria remain blank and are excluded from averages.
- Completeness reports the share of all 27 criteria that have been assessed.

The shared MindManager map remains the source reference. Any extra operational definitions are shown in the in-app **Scoring framework** page so the model stays auditable.

## Structure

- `home.py` — landing page.
- `pages/Scorecard.py` — Streamlit multipage entry point.
- `Scorecard.py` — standalone entry point.
- `brand_scorecard.py` — shared data model, scoring engine, UI and exports.
- `database.py` — persistent assessment and configuration storage.
- `tests/test_scorecard.py` — scoring and export regression tests.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```
