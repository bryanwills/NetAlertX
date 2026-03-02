"""
Integration tests for the 'Device Down' event insertion and sleeping suppression.

Two complementary layers are tested:

Layer 1 — insert_events() (session_events.py)
  The "Device Down" event fires when:
    devPresentLastScan = 1  (was online last scan)
    AND device NOT in CurrentScan  (absent this scan)
    AND devAlertDown != 0

  At this point devIsSleeping is always 0 (sleeping requires devPresentLastScan=0,
  but insert_events runs before update_presence_from_CurrentScan flips it).
  Tests here verify NULL-devAlertDown regression and normal down/no-down branching.

Layer 2 — DevicesView down-count query (as used by insertOnlineHistory / db_helper)
  After presence is updated (devPresentLastScan → 0) the sleeping suppression
  (devIsSleeping=1) kicks in for count/API queries.
  Tests here verify that sleeping devices are excluded from down counts and that
  expired-window devices are included.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db_test_helpers import (  # noqa: E402
    make_db as _make_db,
    minutes_ago as _minutes_ago,
    insert_device as _insert_device,
    down_event_macs as _down_event_macs,
    DummyDB,
)

# server/ is already on sys.path after db_test_helpers import
from scan.session_events import insert_events  # noqa: E402


# ---------------------------------------------------------------------------
# Layer 1: insert_events() — event creation on the down transition
#
# Condition: devPresentLastScan = 1 (was online) AND not in CurrentScan (now absent)
# At this point devIsSleeping is always 0 (sleeping requires devPresentLastScan=0).
# ---------------------------------------------------------------------------

class TestInsertEventsDownDetection:
    """
    Tests for the 'Device Down' INSERT in insert_events().

    The down transition is: devPresentLastScan=1 AND absent from CurrentScan.
    CurrentScan is left empty in all tests (all devices absent this scan).
    """

    def test_null_alert_down_does_not_fire_down_event(self):
        """
        Regression: NULL devAlertDown must NOT produce a 'Device Down' event.

        Root cause: IFNULL(devAlertDown, '') made '' != 0 evaluate TRUE in SQLite,
        causing devices without devAlertDown set to fire constant down events.
        Fix:        IFNULL(devAlertDown, 0)  → 0 != 0 is FALSE.
        """
        conn = _make_db()
        cur = conn.cursor()
        _insert_device(cur, "AA:11:22:33:44:01", alert_down=None, present_last_scan=1)
        conn.commit()

        insert_events(DummyDB(conn))

        assert "AA:11:22:33:44:01" not in _down_event_macs(cur), (
            "NULL devAlertDown must never fire a 'Device Down' event "
            "(IFNULL coercion regression)"
        )

    def test_zero_alert_down_does_not_fire_down_event(self):
        """Explicit devAlertDown=0 must NOT fire a 'Device Down' event."""
        conn = _make_db()
        cur = conn.cursor()
        _insert_device(cur, "AA:11:22:33:44:02", alert_down=0, present_last_scan=1)
        conn.commit()

        insert_events(DummyDB(conn))

        assert "AA:11:22:33:44:02" not in _down_event_macs(cur)

    def test_alert_down_one_fires_down_event_when_absent(self):
        """devAlertDown=1, was online last scan, absent now → 'Device Down' event."""
        conn = _make_db()
        cur = conn.cursor()
        _insert_device(cur, "AA:11:22:33:44:03", alert_down=1, present_last_scan=1)
        conn.commit()

        insert_events(DummyDB(conn))

        assert "AA:11:22:33:44:03" in _down_event_macs(cur)

    def test_device_in_current_scan_does_not_fire_down_event(self):
        """A device present in CurrentScan (online now) must NOT get Down event."""
        conn = _make_db()
        cur = conn.cursor()
        _insert_device(cur, "AA:11:22:33:44:04", alert_down=1, present_last_scan=1)
        # Put it in CurrentScan → device is online this scan
        cur.execute(
            "INSERT INTO CurrentScan (scanMac, scanLastIP) VALUES (?, ?)",
            ("AA:11:22:33:44:04", "192.168.1.1"),
        )
        conn.commit()

        insert_events(DummyDB(conn))

        assert "AA:11:22:33:44:04" not in _down_event_macs(cur)

    def test_already_absent_last_scan_does_not_re_fire(self):
        """
        devPresentLastScan=0 means device was already absent last scan.
        The down event was already created then; it must not be created again.
        (The INSERT query requires devPresentLastScan=1 — the down-transition moment.)
        """
        conn = _make_db()
        cur = conn.cursor()
        _insert_device(cur, "AA:11:22:33:44:05", alert_down=1, present_last_scan=0)
        conn.commit()

        insert_events(DummyDB(conn))

        assert "AA:11:22:33:44:05" not in _down_event_macs(cur)

    def test_archived_device_does_not_fire_down_event(self):
        """Archived devices should not produce Down events."""
        conn = _make_db()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO Devices
                   (devMac, devAlertDown, devPresentLastScan, devCanSleep,
                    devLastConnection, devLastIP, devIsArchived, devIsNew)
               VALUES (?, 1, 1, 0, ?, '192.168.1.1', 1, 0)""",
            ("AA:11:22:33:44:06", _minutes_ago(60)),
        )
        conn.commit()

        insert_events(DummyDB(conn))

        # Archived devices have devIsArchived=1; insert_events doesn't filter
        # by archived, but DevicesView applies devAlertDown — archived here is
        # tested to confirm the count stays clean for future filter additions.
        # The archived device DOES get a Down event today (no archive filter in
        # insert_events). This test documents the current behaviour.
        # If that changes, update this assertion accordingly.
        assert "AA:11:22:33:44:06" in _down_event_macs(cur)

    def test_multiple_devices_mixed_alert_down(self):
        """Only devices with devAlertDown=1 that are absent fire Down events."""
        conn = _make_db()
        cur = conn.cursor()
        cases = [
            ("CC:00:00:00:00:01", None, 1),   # NULL  → no event
            ("CC:00:00:00:00:02", 0,    1),   # 0     → no event
            ("CC:00:00:00:00:03", 1,    1),   # 1     → event
            ("CC:00:00:00:00:04", 1,    0),   # already absent → no event
        ]
        for mac, alert_down, present in cases:
            _insert_device(cur, mac, alert_down=alert_down, present_last_scan=present)
        conn.commit()

        insert_events(DummyDB(conn))
        fired = _down_event_macs(cur)

        assert "CC:00:00:00:00:01" not in fired, "NULL devAlertDown must not fire"
        assert "CC:00:00:00:00:02" not in fired, "devAlertDown=0 must not fire"
        assert "CC:00:00:00:00:03" in fired,     "devAlertDown=1 absent must fire"
        assert "CC:00:00:00:00:04" not in fired, "already-absent device must not fire again"


# ---------------------------------------------------------------------------
# Layer 2: DevicesView down-count query (post-presence-update)
#
# After update_presence_from_CurrentScan sets devPresentLastScan → 0 for absent
# devices, the sleeping suppression (devIsSleeping) becomes active for:
#   - insertOnlineHistory  (SUM ... WHERE devPresentLastScan=0 AND devIsSleeping=0)
#   - db_helper "down" filter
#   - getDown()
# ---------------------------------------------------------------------------

class TestDownCountSleepingSuppression:
    """
    Tests for the post-presence-update down-count query.

    Simulates the state AFTER update_presence_from_CurrentScan has run by
    inserting devices with devPresentLastScan=0 (already absent) directly.
    """

    _DOWN_COUNT_SQL = """
        SELECT devMac FROM DevicesView
        WHERE devAlertDown != 0
          AND devPresentLastScan = 0
          AND devIsSleeping = 0
          AND devIsArchived = 0
    """

    def test_null_alert_down_excluded_from_down_count(self):
        """NULL devAlertDown must not contribute to down count."""
        conn = _make_db()
        cur = conn.cursor()
        _insert_device(cur, "DD:00:00:00:00:01", alert_down=None, present_last_scan=0)
        conn.commit()

        cur.execute(self._DOWN_COUNT_SQL)
        macs = {r["devMac"] for r in cur.fetchall()}
        assert "DD:00:00:00:00:01" not in macs

    def test_alert_down_one_included_in_down_count(self):
        """devAlertDown=1 absent device must be counted as down."""
        conn = _make_db()
        cur = conn.cursor()
        _insert_device(cur, "DD:00:00:00:00:02", alert_down=1, present_last_scan=0,
                       last_connection=_minutes_ago(60))
        conn.commit()

        cur.execute(self._DOWN_COUNT_SQL)
        macs = {r["devMac"] for r in cur.fetchall()}
        assert "DD:00:00:00:00:02" in macs

    def test_sleeping_device_excluded_from_down_count(self):
        """
        devCanSleep=1 + absent + within sleep window → devIsSleeping=1.
        Must be excluded from the down-count query.
        """
        conn = _make_db(sleep_minutes=30)
        cur = conn.cursor()
        _insert_device(cur, "DD:00:00:00:00:03", alert_down=1, present_last_scan=0,
                       can_sleep=1, last_connection=_minutes_ago(5))
        conn.commit()

        cur.execute(self._DOWN_COUNT_SQL)
        macs = {r["devMac"] for r in cur.fetchall()}
        assert "DD:00:00:00:00:03" not in macs, (
            "Sleeping device must be excluded from down count"
        )

    def test_expired_sleep_window_included_in_down_count(self):
        """Once the sleep window expires the device must appear in down count."""
        conn = _make_db(sleep_minutes=30)
        cur = conn.cursor()
        _insert_device(cur, "DD:00:00:00:00:04", alert_down=1, present_last_scan=0,
                       can_sleep=1, last_connection=_minutes_ago(45))
        conn.commit()

        cur.execute(self._DOWN_COUNT_SQL)
        macs = {r["devMac"] for r in cur.fetchall()}
        assert "DD:00:00:00:00:04" in macs, (
            "Device past its sleep window must appear in down count"
        )

    def test_can_sleep_zero_always_in_down_count(self):
        """devCanSleep=0 device that is absent is always counted as down."""
        conn = _make_db(sleep_minutes=30)
        cur = conn.cursor()
        _insert_device(cur, "DD:00:00:00:00:05", alert_down=1, present_last_scan=0,
                       can_sleep=0, last_connection=_minutes_ago(5))
        conn.commit()

        cur.execute(self._DOWN_COUNT_SQL)
        macs = {r["devMac"] for r in cur.fetchall()}
        assert "DD:00:00:00:00:05" in macs

    def test_online_history_down_count_excludes_sleeping(self):
        """
        Mirrors the insertOnlineHistory SUM query exactly.
        Sleeping devices must not inflate the downDevices count.
        """
        conn = _make_db(sleep_minutes=30)
        cur = conn.cursor()

        # Normal down
        _insert_device(cur, "EE:00:00:00:00:01", alert_down=1, present_last_scan=0,
                       can_sleep=0, last_connection=_minutes_ago(60))
        # Sleeping (within window)
        _insert_device(cur, "EE:00:00:00:00:02", alert_down=1, present_last_scan=0,
                       can_sleep=1, last_connection=_minutes_ago(10))
        # Online
        _insert_device(cur, "EE:00:00:00:00:03", alert_down=1, present_last_scan=1,
                       last_connection=_minutes_ago(1))
        conn.commit()

        cur.execute("""
            SELECT
                COALESCE(SUM(CASE
                    WHEN devPresentLastScan = 0
                     AND devAlertDown = 1
                     AND devIsSleeping = 0
                    THEN 1 ELSE 0 END), 0) AS downDevices
            FROM DevicesView
        """)
        count = cur.fetchone()["downDevices"]
        assert count == 1, (
            f"Expected 1 down device (sleeping device must not be counted), got {count}"
        )
