"""Tests for update_devPresentLastScan_based_on_nics.

Regression coverage for the bug where a parent device with a 'nic' child
relationship had its own directly-detected presence overwritten by the NIC
child's absence, producing an endless one-directional Connected event stream.
"""

import sqlite3

import pytest

from server.scan import device_handling


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(rows):
    """Return a DummyDB-compatible object populated with the given Devices rows."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE Devices (
            devMac TEXT PRIMARY KEY,
            devPresentLastScan INTEGER DEFAULT 0,
            devParentMAC TEXT,
            devParentRelType TEXT DEFAULT '',
            devReqNicsOnline INTEGER DEFAULT 0
        )
        """
    )
    cur.executemany(
        """
        INSERT INTO Devices (devMac, devPresentLastScan, devParentMAC,
                             devParentRelType, devReqNicsOnline)
        VALUES (:mac, :present, :parent_mac, :rel_type, :req_all)
        """,
        rows,
    )
    conn.commit()

    class DummyDB:
        def __init__(self, connection):
            self.sql = connection.cursor()
            self._conn = connection

        def commitDB(self):
            self._conn.commit()

    db = DummyDB(conn)
    # Re-use conn cursor for later reads
    db._raw_conn = conn
    return db


def _present(db, mac):
    row = db._raw_conn.execute(
        "SELECT devPresentLastScan FROM Devices WHERE devMac = ?", (mac,)
    ).fetchone()
    return row[0]


# ---------------------------------------------------------------------------
# Core bug regression: parent directly detected (present=1) + absent NIC child
# ---------------------------------------------------------------------------

class TestNicChildDoesNotForcePresentParentDown:
    """Parent was directly detected this scan; absent NIC must NOT override that."""

    def test_any_mode_absent_nic_does_not_clear_present_parent(self):
        """Bug: req_all=0, parent present=1, nic present=0 → parent must stay 1."""
        db = _make_db([
            {"mac": "AA:AA:AA:AA:AA:01", "present": 1,
             "parent_mac": "",     "rel_type": "",    "req_all": 0},
            {"mac": "BB:BB:BB:BB:BB:01", "present": 0,
             "parent_mac": "AA:AA:AA:AA:AA:01", "rel_type": "nic", "req_all": 0},
        ])
        device_handling.update_devPresentLastScan_based_on_nics(db)
        assert _present(db, "AA:AA:AA:AA:AA:01") == 1, (
            "Parent directly detected as present must not be forced offline "
            "by an absent NIC child."
        )

    def test_req_all_mode_absent_nic_does_not_clear_present_parent(self):
        """Bug: req_all=1, parent present=1, nic present=0 → parent must stay 1."""
        db = _make_db([
            {"mac": "AA:AA:AA:AA:AA:02", "present": 1,
             "parent_mac": "",     "rel_type": "",    "req_all": 1},
            {"mac": "BB:BB:BB:BB:BB:02", "present": 0,
             "parent_mac": "AA:AA:AA:AA:AA:02", "rel_type": "nic", "req_all": 0},
        ])
        device_handling.update_devPresentLastScan_based_on_nics(db)
        assert _present(db, "AA:AA:AA:AA:AA:02") == 1


# ---------------------------------------------------------------------------
# NIC can still raise an undetected parent (original=0)
# ---------------------------------------------------------------------------

class TestNicRaisesAbsentParent:
    """NIC children should be able to mark a parent present when it wasn't seen directly."""

    def test_any_mode_online_nic_raises_absent_parent(self):
        db = _make_db([
            {"mac": "AA:AA:AA:AA:AA:03", "present": 0,
             "parent_mac": "",     "rel_type": "",    "req_all": 0},
            {"mac": "BB:BB:BB:BB:BB:03", "present": 1,
             "parent_mac": "AA:AA:AA:AA:AA:03", "rel_type": "nic", "req_all": 0},
        ])
        device_handling.update_devPresentLastScan_based_on_nics(db)
        assert _present(db, "AA:AA:AA:AA:AA:03") == 1

    def test_req_all_mode_all_nics_online_raises_absent_parent(self):
        db = _make_db([
            {"mac": "AA:AA:AA:AA:AA:04", "present": 0,
             "parent_mac": "",     "rel_type": "",    "req_all": 1},
            {"mac": "BB:BB:BB:BB:BB:04a", "present": 1,
             "parent_mac": "AA:AA:AA:AA:AA:04", "rel_type": "nic", "req_all": 0},
            {"mac": "BB:BB:BB:BB:BB:04b", "present": 1,
             "parent_mac": "AA:AA:AA:AA:AA:04", "rel_type": "nic", "req_all": 0},
        ])
        device_handling.update_devPresentLastScan_based_on_nics(db)
        assert _present(db, "AA:AA:AA:AA:AA:04") == 1

    def test_req_all_mode_partial_nics_does_not_raise_absent_parent(self):
        """In req_all mode, if not all NICs are online, an absent parent stays absent."""
        db = _make_db([
            {"mac": "AA:AA:AA:AA:AA:05", "present": 0,
             "parent_mac": "",     "rel_type": "",    "req_all": 1},
            {"mac": "BB:BB:BB:BB:BB:05a", "present": 1,
             "parent_mac": "AA:AA:AA:AA:AA:05", "rel_type": "nic", "req_all": 0},
            {"mac": "BB:BB:BB:BB:BB:05b", "present": 0,
             "parent_mac": "AA:AA:AA:AA:AA:05", "rel_type": "nic", "req_all": 0},
        ])
        device_handling.update_devPresentLastScan_based_on_nics(db)
        assert _present(db, "AA:AA:AA:AA:AA:05") == 0

    def test_any_mode_all_nics_absent_leaves_parent_absent(self):
        db = _make_db([
            {"mac": "AA:AA:AA:AA:AA:06", "present": 0,
             "parent_mac": "",     "rel_type": "",    "req_all": 0},
            {"mac": "BB:BB:BB:BB:BB:06", "present": 0,
             "parent_mac": "AA:AA:AA:AA:AA:06", "rel_type": "nic", "req_all": 0},
        ])
        device_handling.update_devPresentLastScan_based_on_nics(db)
        assert _present(db, "AA:AA:AA:AA:AA:06") == 0


# ---------------------------------------------------------------------------
# No NIC children → no change regardless of presence
# ---------------------------------------------------------------------------

class TestNoNicChildren:
    def test_parent_with_no_nics_unchanged(self):
        db = _make_db([
            {"mac": "AA:AA:AA:AA:AA:07", "present": 1,
             "parent_mac": "",     "rel_type": "",    "req_all": 0},
            {"mac": "AA:AA:AA:AA:AA:08", "present": 0,
             "parent_mac": "",     "rel_type": "",    "req_all": 0},
        ])
        updated = device_handling.update_devPresentLastScan_based_on_nics(db)
        assert updated == 0
        assert _present(db, "AA:AA:AA:AA:AA:07") == 1
        assert _present(db, "AA:AA:AA:AA:AA:08") == 0
