# Advent+ Africa Brand Scorecard

A Streamlit decision workspace that turns the shared **BRAND ANALYSIS** mind map into a structured brand-assessment workflow.

## Run locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run home.py
```

The app supports:

- a live home dashboard with portfolio counts, a three-step workflow and a recent-brand snapshot;
- guided assessments across all descriptive and strategic criteria;
- multi-select strategic categories, permanent custom category creation, and category-dependent brand families;
- protected brand and custom-category deletion with explicit confirmation;
- persistent PostgreSQL/Supabase storage in production, with SQLite as the local fallback;
- a commercial-owner field for accountability and portfolio filtering;
- an Overview brand filter with collapsible indicators for every selected brand;
- simple or weighted scoring;
- decision matrices, rankings, heatmaps and pillar profiles;
- a color-coded multi-brand radar for strategic profile comparison;
- CSV and Excel portfolio imports;
- formatted Excel review-pack exports;
- legacy columns and score labels from the previous implementation.

## Database, import and export

The application uses Supabase PostgreSQL whenever the `DATABASE_URL` secret is configured. Without that secret, it falls back to `data/brand_scorecard.db` and creates the local SQLite database automatically.

- Saving or updating an assessment writes the complete record to the database.
- Deleting an existing brand requires explicit confirmation and removes its complete assessment.
- CSV/XLSX imports are merged into the database by brand name.
- Exports remain available for portfolio reviews, sharing and backups.
- Open **Data tools** in the sidebar and use **Refresh database** to load changes saved by another active session.

To make the local application use the same Supabase database as the deployed application, create an untracked `.streamlit/secrets.toml` file:

```toml
DATABASE_URL = "postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:5432/postgres"
```

Use the **Session pooler** URI copied from the Supabase **Connect** dialog. Never commit this file or connection string. To keep using SQLite but store it elsewhere, set `BRAND_SCORECARD_DB_PATH` before starting Streamlit:

```powershell
$env:BRAND_SCORECARD_DB_PATH = "D:\Data\brand_scorecard.db"
python -m streamlit run home.py
```

The PostgreSQL tables are created automatically on first connection. To migrate the existing local SQLite records and settings, install the requirements and run:

```powershell
python migrate_to_supabase.py
```

Paste the untouched Session pooler URI containing `[YOUR-PASSWORD]`, then enter the database password separately when prompted. The password input is hidden, URL-encoded automatically and is not written to the project.

## Scoring model

- **Descriptive score:** 1 (low) to 4 (leading).
- **Strategic score:** -2 (material risk) to +2 (strong fit).
- Missing criteria remain blank and are excluded from averages.
- Completeness reports the share of all 27 criteria that have been assessed.

The shared MindManager map remains the source reference. Any extra operational definitions are shown in the in-app **Scoring framework** page so the model stays auditable.

## Structure

- `home.py` — landing page.
- `assets/app.css` — shared visual design for the home page and scorecard interfaces.
- `pages/Scorecard.py` — Streamlit multipage entry point.
- `Scorecard.py` — standalone entry point.
- `brand_scorecard.py` — shared data model, scoring engine, UI and exports.
- `database.py` — persistent assessment and configuration storage.
- `migrate_to_supabase.py` — one-time SQLite-to-Supabase migration utility.
- `tests/test_scorecard.py` — scoring and export regression tests.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```
