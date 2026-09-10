"""
Tests for the Events/Sessions/AppEvents/Notifications schema drift guard
(server/db/schema_columns.py, server/db/db_upgrade.py's ensure_table_columns())
- see scan-pipeline-hardening.md Design §3.

Three things are tested:
1. No drift today between TABLE_COLUMNS and the real server/db/schema/app.sql.
2. The drift-detection logic can actually detect a real mismatch (not just a
   check that always passes trivially) - per the prd-writing skill's rule
   that a guard needs its own test, separate from "no drift found today".
3. AppEvents/Notifications specifically have a *second* schema-definition
   surface beyond app.sql (their own inline CREATE TABLE IF NOT EXISTS in
   application code) - keep that in sync too, using the real classes rather
   than re-parsing their SQL as text.
4. ensure_table_columns() backfill: a table missing one column gets it added
   with the right type.
"""

import os
import sqlite3
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.schema_columns import TABLE_COLUMNS  # noqa: E402
from db.db_upgrade import ensure_table_columns  # noqa: E402
from db_test_helpers import make_db, DummyDB  # noqa: E402

_APP_SQL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "server", "db", "schema", "app.sql"
)


def _columns_from_ddl(ddl_sql, table):
    """Execute a CREATE TABLE (or full multi-statement schema) into a fresh
    in-memory connection and return the resulting column name set - uses
    SQLite's own DDL parser rather than a hand-rolled regex, so it can't be
    fooled by formatting differences that a text-based diff would trip on."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(ddl_sql)
        return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
    finally:
        conn.close()


def _drift(ddl_sql, table):
    """Column names present in one source but not the other. Empty = no drift."""
    expected = set(TABLE_COLUMNS[table].keys())
    actual = _columns_from_ddl(ddl_sql, table)
    return expected.symmetric_difference(actual)


class TestNoDriftAgainstRealAppSql:
    @pytest.mark.parametrize("table", list(TABLE_COLUMNS.keys()))
    def test_table_matches_app_sql(self, table):
        app_sql = open(_APP_SQL_PATH).read()
        drift = _drift(app_sql, table)
        assert not drift, (
            f"{table}: TABLE_COLUMNS (server/db/schema_columns.py) and "
            f"app.sql disagree on {drift} - update whichever one is stale"
        )


class TestGuardActuallyDetectsDrift:
    """Proves the comparison logic can fail, not just a check that always
    reports success - without this, it's possible to ship a guard that
    passes regardless of what it's given."""

    def test_missing_columns_detected(self):
        broken_sql = "CREATE TABLE Events (eveMac TEXT, eveIp TEXT);"
        drift = _drift(broken_sql, "Events")
        assert drift == {
            "eveDateTime", "eveEventType", "eveAdditionalInfo",
            "evePendingAlertEmail", "evePairEventRowid",
        }

    def test_extra_column_detected(self):
        broken_sql = "CREATE TABLE Sessions (sesMac TEXT, sesUnexpectedNewColumn TEXT);"
        drift = _drift(broken_sql, "Sessions")
        assert "sesUnexpectedNewColumn" in drift


class TestInlineDDLMatchesConstant:
    """AppEvents/Notifications each have a second schema-definition surface
    beyond app.sql - the inline CREATE TABLE IF NOT EXISTS in their own
    Python classes (found during Design §3 implementation - see
    scan-pipeline-hardening.md's correction). Exercised via the real classes,
    not by re-parsing their embedded SQL as text."""

    def test_app_events_inline_ddl_matches_constant(self):
        from workflows.app_events import AppEvent_obj

        conn = make_db()
        db = DummyDB(conn)
        AppEvent_obj(db)  # drops + recreates AppEvents with the real inline DDL

        cols = {row[1] for row in conn.execute('PRAGMA table_info("AppEvents")').fetchall()}
        assert cols == set(TABLE_COLUMNS["AppEvents"].keys())
        conn.close()

    def test_notifications_inline_ddl_matches_constant(self):
        from models.notification_instance import NotificationInstance

        conn = make_db()
        db = DummyDB(conn)
        with patch("models.notification_instance.get_setting_value", return_value=""), \
             patch("models.notification_instance.Logger"):
            NotificationInstance(db)

        cols = {row[1] for row in conn.execute('PRAGMA table_info("Notifications")').fetchall()}
        assert cols == set(TABLE_COLUMNS["Notifications"].keys())
        conn.close()


class TestEnsureTableColumnsBackfill:
    """ensure_table_columns() must repair a table that's missing a column -
    mirroring however Devices' existing 18 ensure_column() calls are (or
    aren't currently) tested, generalized to the four registered tables."""

    @pytest.mark.parametrize("table", list(TABLE_COLUMNS.keys()))
    def test_missing_column_is_backfilled(self, table):
        columns = TABLE_COLUMNS[table]
        first_col, first_type = next(iter(columns.items()))
        remaining = {c: t for c, t in columns.items() if c != first_col}

        conn = sqlite3.connect(":memory:")
        col_defs = ", ".join(f'"{c}" {t}' for c, t in remaining.items())
        conn.execute(f"CREATE TABLE {table} ({col_defs})")
        cur = conn.cursor()

        ok = ensure_table_columns(cur, table)
        assert ok, f"ensure_table_columns({table}) reported failure"

        cols = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
        assert cols == set(columns.keys()), f"{table}: backfill did not restore {first_col}"
        conn.close()

    def test_missing_table_skips_without_error(self):
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        ok = ensure_table_columns(cur, "Notifications")
        assert ok, "a not-yet-created table must not be treated as a failure"
        conn.close()
