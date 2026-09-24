import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import brand_scorecard as app
import database
import migrate_to_supabase


class ScorecardTests(unittest.TestCase):
    def test_database_backend_uses_postgres_url_but_explicit_paths_remain_sqlite(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            sqlite_path = Path(temp_directory) / "scorecard.db"
            with patch.dict(
                os.environ,
                {"DATABASE_URL": "postgresql://example.invalid/postgres"},
            ):
                self.assertEqual(database.database_backend(), "PostgreSQL")
                self.assertEqual(database.database_backend(sqlite_path), "SQLite")

    def test_database_json_payload_converts_missing_values_to_null(self):
        payload = database._json_payload(
            {"pandas_missing": pd.NA, "float_nan": float("nan"), "value": 2}
        )
        self.assertEqual(
            json.loads(payload),
            {"pandas_missing": None, "float_nan": None, "value": 2},
        )

    def test_supabase_migration_builds_safe_session_pooler_url(self):
        template = (
            "postgresql://postgres.project-ref:[YOUR-PASSWORD]"
            "@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
        )
        database_url = migrate_to_supabase.build_database_url(
            template,
            "Strong@Password#1!",
        )
        self.assertIn("Strong%40Password%231%21", database_url)
        self.assertNotIn("[YOUR-PASSWORD]", database_url)

    def test_framework_contains_every_mindmap_branch(self):
        self.assertIn("Confectionery", app.CATEGORIES_FAMILIES["Retail"])
        self.assertIn("Adjacent", app.CATEGORIES_FAMILIES["Food service"])
        for criterion in [
            "Performance",
            "Product Acceptance",
            "DNA Convergence",
            "Strategy Compatibility",
            "Complexity",
            "Energy",
            "Convergence",
        ]:
            self.assertIn(criterion, app.STRATEGIC_SCALES)

    def test_performance_scale_matches_mindmap(self):
        scale = app.STRATEGIC_SCALES["Performance"]
        self.assertEqual(list(scale.values()), [-2, -1, 1, 2])

    def test_scoring_accepts_raw_numeric_and_legacy_decorated_values(self):
        raw = next(label for label, score in app.DESCRIPTIVE_SCALES["Positioning"].items() if score == 4)
        self.assertEqual(app.score_value("Positioning", raw), 4)
        self.assertEqual(app.score_value("Positioning", "Legacy label → Score : 3"), 3)
        self.assertEqual(app.score_value("Performance", "Legacy label → Score : +2"), 2)
        self.assertEqual(app.score_value("Performance", -2), -2)

    def test_compute_scores_uses_all_assessed_values_and_tracks_completeness(self):
        record = {column: pd.NA for column in app.INPUT_COLUMNS}
        record.update(
            {
                "Brand name": "Test Brand",
                "Strategic category": "Retail",
                "Brand family": "Chocolate",
                "Positioning": next(iter(app.DESCRIPTIVE_SCALES["Positioning"])),
                "Performance": next(
                    label for label, score in app.STRATEGIC_SCALES["Performance"].items() if score == 2
                ),
                "Status": "In progress",
            }
        )
        scored = app.compute_scores(pd.DataFrame([record]))
        self.assertEqual(scored.loc[0, "Descriptive score"], 1)
        self.assertEqual(scored.loc[0, "Strategic score"], 2)
        self.assertEqual(scored.loc[0, "Completeness (%)"], round(2 / len(app.ALL_CRITERIA) * 100))

    def test_score_interpretations_and_recommendation_follow_editable_thresholds(self):
        thresholds = app.DEFAULT_THRESHOLDS
        self.assertEqual(app.descriptive_tier(1.99, thresholds), "Low")
        self.assertEqual(app.descriptive_tier(2.00, thresholds), "Developing")
        self.assertEqual(app.descriptive_tier(3.00, thresholds), "Attractive")
        self.assertEqual(app.descriptive_tier(3.50, thresholds), "Leading")

        self.assertEqual(app.strategic_decision(0.10, thresholds), "Investigate")
        self.assertEqual(app.strategic_decision(0.25, thresholds), "Opportunity")
        self.assertEqual(app.strategic_decision(1.00, thresholds), "Priority")

        self.assertEqual(app.matrix_recommendation(2.14, 0.10, thresholds), "Do not prioritize")
        self.assertEqual(app.matrix_recommendation(2.14, 0.25, thresholds), "Develop opportunity")
        self.assertEqual(app.matrix_recommendation(3.43, 0.90, thresholds), "Priority")

        custom_thresholds = {**thresholds, "desc_strong": 3.5, "strat_opportunity": 0.5}
        self.assertEqual(app.matrix_recommendation(3.43, 0.90, custom_thresholds), "Develop opportunity")
        self.assertEqual(app.matrix_recommendation(3.60, 0.40, custom_thresholds), "Validate risks")

    def test_zero_weight_group_does_not_divide_by_zero(self):
        record = {column: pd.NA for column in app.INPUT_COLUMNS}
        record.update({"Brand name": "Test", "Positioning": 4, "Performance": 2})
        weights = {criterion: 0 for criterion in app.ALL_CRITERIA}
        scored = app.compute_scores(pd.DataFrame([record]), weights=weights, use_weighted=True)
        self.assertTrue(pd.isna(scored.loc[0, "Descriptive score"]))
        self.assertTrue(pd.isna(scored.loc[0, "Strategic score"]))

    def test_brand_profile_figure_has_one_distinct_trace_per_brand(self):
        records = []
        for brand_name, score in [("Alpha", 2), ("Beta", -1), ("Gamma", 1)]:
            record = {column: pd.NA for column in app.INPUT_COLUMNS}
            record.update({"Brand name": brand_name, **{criterion: score for criterion in app.STRATEGIC_CRITERIA}})
            records.append(record)
        figure = app.build_brand_profile_figure(pd.DataFrame(records))
        self.assertEqual([trace.name for trace in figure.data], ["Alpha", "Beta", "Gamma"])
        self.assertEqual(len({trace.line.color for trace in figure.data}), 3)
        self.assertTrue(figure.layout.showlegend)

    def test_legacy_columns_are_migrated(self):
        migrated = app.migrate_portfolio(
            pd.DataFrame(
                [
                    {
                        "Brand name": "Legacy",
                        "Country Location": "0 - 10 pays",
                        "Export Turnover %": "0% - 5%",
                        "Status": "Review required",
                    }
                ]
            )
        )
        self.assertIn("Country Presence", migrated.columns)
        self.assertIn("Export Turnover (%)", migrated.columns)
        self.assertEqual(migrated.loc[0, "Status"], "Ready for review")

    def test_categories_and_families_support_multiple_values(self):
        migrated = app.migrate_portfolio(
            pd.DataFrame(
                [
                    {
                        "Brand name": "Multi",
                        "Strategic category": ["Retail", "Food service", "Retail"],
                        "Brand family": "Chocolate; Biscuits | Adjacent",
                    }
                ]
            )
        )
        self.assertEqual(migrated.loc[0, "Strategic category"], "Retail | Food service")
        self.assertEqual(migrated.loc[0, "Brand family"], "Chocolate | Biscuits | Adjacent")
        self.assertEqual(
            app.parse_multi_value(migrated.loc[0, "Strategic category"]),
            ["Retail", "Food service"],
        )

    def test_custom_strategic_categories_extend_default_options(self):
        portfolio = pd.DataFrame(
            {
                "Strategic category": ["Retail | Hospitality", "Specialty"],
            }
        )
        options = app.strategic_category_options(
            ["Hospitality", "retail", "Healthcare"],
            portfolio,
        )
        self.assertEqual(
            options,
            ["Retail", "Beverage", "Food service", "Hospitality", "Healthcare", "Specialty"],
        )
        self.assertNotIn(app.ADD_CATEGORY_OPTION, options)

    def test_excel_export_contains_review_pack_sheets(self):
        record = {column: pd.NA for column in app.INPUT_COLUMNS}
        record.update({"Brand name": "Export Test", "Positioning": 4, "Performance": 2})
        payload = app.build_excel_export(
            pd.DataFrame([record]), app.DEFAULT_WEIGHTS, app.DEFAULT_THRESHOLDS, False
        )
        self.assertTrue(payload.startswith(b"PK"))
        workbook = pd.ExcelFile(io.BytesIO(payload))
        self.assertEqual(
            workbook.sheet_names,
            ["Portfolio", "Ranking", "Scoring framework", "Settings", "Methodology"],
        )

    def test_database_persists_updates_and_configuration(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / "scorecard.db"
            database.initialize_database(path)
            database.upsert_assessment(
                {
                    "Brand name": "Database Brand",
                    "Commercial owner": "Commercial A",
                    "Strategic category": "Retail | Beverage",
                    "Brand family": "Chocolate | Syrups",
                    "Status": "In progress",
                },
                path=path,
            )
            saved = database.load_assessments(path)
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["Commercial owner"], "Commercial A")

            saved[0]["Status"] = "Review required"
            database.upsert_assessment(saved[0], path=path)
            self.assertEqual(
                database.rename_assessment_status("Review required", "Ready for review", path),
                1,
            )
            self.assertEqual(database.load_assessments(path)[0]["Status"], "Ready for review")

            updated = dict(saved[0])
            updated["Brand name"] = "Renamed Brand"
            updated["Status"] = "Validated"
            database.upsert_assessment(updated, previous_name="Database Brand", path=path)
            reloaded = database.load_assessments(path)
            self.assertEqual([record["Brand name"] for record in reloaded], ["Renamed Brand"])
            self.assertEqual(reloaded[0]["Status"], "Validated")

            database.save_setting("test", {"weighted": True}, path)
            self.assertEqual(database.load_setting("test", path=path), {"weighted": True})
            self.assertFalse(database.delete_assessment("Missing Brand", path))
            self.assertTrue(database.delete_assessment("RENAMED BRAND", path))
            self.assertEqual(database.load_assessments(path), [])
            self.assertEqual(database.database_info(path)["records"], 0)


if __name__ == "__main__":
    unittest.main()
