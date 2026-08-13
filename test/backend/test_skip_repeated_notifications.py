"""
Tests for skip_repeated_notifications() UTC/localtime correctness.

Verifies that the cooldown comparison uses UTC on both sides, so that
devSkipRepeated works correctly regardless of the server's local timezone.

License: GNU GPLv3
"""

import sqlite3
import sys
import os
import time
import unittest

INSTALL_PATH = os.getenv("NETALERTX_APP", "/app")
sys.path.extend([f"{INSTALL_PATH}/server"])


def _make_db():
    """Create an in-memory SQLite DB with the minimal schema needed."""
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE Devices (
            devMac TEXT PRIMARY KEY,
            devName TEXT,
            devLastNotification TEXT,
            devSkipRepeated INTEGER DEFAULT 0
        );
        CREATE TABLE Events (
            eveRowid INTEGER PRIMARY KEY AUTOINCREMENT,
            eveMac TEXT,
            evePendingAlertEmail INTEGER DEFAULT 0
        );
    """)
    return con


class FakeDB:
    """Minimal stub accepted by skip_repeated_notifications."""

    def __init__(self, con):
        self.sql = con
        self._committed = False

    def commitDB(self):
        self._committed = True
        self.sql.commit()


class TestSkipRepeatedNotifications(unittest.TestCase):

    def _get_flag(self, con, mac):
        row = con.execute(
            "SELECT evePendingAlertEmail FROM Events WHERE eveMac=?", (mac,)
        ).fetchone()
        return row[0] if row else None

    def test_recent_notification_suppresses_event(self):
        """
        A notification that occurred seconds ago should suppress the pending
        alert when devSkipRepeated is set to 1 hour.
        """
        from messaging.reporting import skip_repeated_notifications

        con = _make_db()

        # last notification = now (UTC ISO format)
        now_utc = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        con.execute(
            "INSERT INTO Devices VALUES (?,?,?,?)",
            ("AA:BB:CC:DD:EE:01", "TestDev", now_utc, 1),
        )
        con.execute(
            "INSERT INTO Events (eveMac, evePendingAlertEmail) VALUES (?,?)",
            ("AA:BB:CC:DD:EE:01", 1),
        )
        con.commit()

        db = FakeDB(con)
        skip_repeated_notifications(db)

        self.assertEqual(
            self._get_flag(con, "AA:BB:CC:DD:EE:01"),
            0,
            "Event should have been suppressed because last notification is recent",
        )

    def test_old_notification_does_not_suppress(self):
        """
        A notification older than devSkipRepeated should NOT suppress the event.
        """
        from messaging.reporting import skip_repeated_notifications

        con = _make_db()

        # last notification = 2 hours ago (UTC)
        two_hours_ago = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 7200)
        )
        con.execute(
            "INSERT INTO Devices VALUES (?,?,?,?)",
            ("AA:BB:CC:DD:EE:02", "TestDev2", two_hours_ago, 1),
        )
        con.execute(
            "INSERT INTO Events (eveMac, evePendingAlertEmail) VALUES (?,?)",
            ("AA:BB:CC:DD:EE:02", 1),
        )
        con.commit()

        db = FakeDB(con)
        skip_repeated_notifications(db)

        self.assertEqual(
            self._get_flag(con, "AA:BB:CC:DD:EE:02"),
            1,
            "Event should NOT be suppressed because last notification was 2 h ago "
            "and cooldown is only 1 h",
        )

    def test_utc_stored_timestamp_not_inflated_by_localtime(self):
        """
        Regression test: if the RHS still used 'localtime', a UTC-stored
        devLastNotification in a positive-offset timezone would appear as if
        the cooldown has already expired, producing no suppression.

        We simulate this by using a timestamp that is 20 minutes in the past
        (well within a 2-hour cooldown).  With the bug the comparison would
        evaluate incorrectly in timezones with a positive UTC offset.
        """
        from messaging.reporting import skip_repeated_notifications

        con = _make_db()

        twenty_min_ago_utc = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 1200)
        )
        con.execute(
            "INSERT INTO Devices VALUES (?,?,?,?)",
            ("AA:BB:CC:DD:EE:03", "TestDev3", twenty_min_ago_utc, 2),
        )
        con.execute(
            "INSERT INTO Events (eveMac, evePendingAlertEmail) VALUES (?,?)",
            ("AA:BB:CC:DD:EE:03", 1),
        )
        con.commit()

        db = FakeDB(con)
        skip_repeated_notifications(db)

        self.assertEqual(
            self._get_flag(con, "AA:BB:CC:DD:EE:03"),
            0,
            "Event should be suppressed: only 20 min elapsed, cooldown is 2 h. "
            "Failure here means the localtime bug is still present.",
        )

    def test_zero_skip_repeated_never_suppresses(self):
        """devSkipRepeated=0 should never suppress notifications."""
        from messaging.reporting import skip_repeated_notifications

        con = _make_db()

        now_utc = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        con.execute(
            "INSERT INTO Devices VALUES (?,?,?,?)",
            ("AA:BB:CC:DD:EE:04", "TestDev4", now_utc, 0),
        )
        con.execute(
            "INSERT INTO Events (eveMac, evePendingAlertEmail) VALUES (?,?)",
            ("AA:BB:CC:DD:EE:04", 1),
        )
        con.commit()

        db = FakeDB(con)
        skip_repeated_notifications(db)

        self.assertEqual(
            self._get_flag(con, "AA:BB:CC:DD:EE:04"),
            1,
            "Event should NOT be suppressed when devSkipRepeated=0",
        )


if __name__ == "__main__":
    unittest.main()
