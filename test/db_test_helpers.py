"""
Shared in-memory database factories and helpers for NetAlertX unit tests.

Import from any test subdirectory with:

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from db_test_helpers import make_db, insert_device, minutes_ago, DummyDB, down_event_macs
"""

import sqlite3
import sys
import os
from datetime import datetime, timezone, timedelta

# Make the 'server' package importable when this module is loaded directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
from db.db_upgrade import ensure_views  # noqa: E402


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

CREATE_DEVICES = """
    CREATE TABLE IF NOT EXISTS Devices (
        devMac                 TEXT PRIMARY KEY,
        devName                TEXT,
        devOwner               TEXT,
        devType                TEXT,
        devVendor              TEXT,
        devFavorite            INTEGER DEFAULT 0,
        devGroup               TEXT,
        devComments            TEXT,
        devFirstConnection     TEXT,
        devLastConnection      TEXT,
        devLastIP              TEXT,
        devPrimaryIPv4         TEXT,
        devPrimaryIPv6         TEXT,
        devVlan                TEXT,
        devForceStatus         TEXT,
        devStaticIP            TEXT,
        devScan                INTEGER DEFAULT 1,
        devLogEvents           INTEGER DEFAULT 1,
        devAlertEvents         INTEGER DEFAULT 1,
        devAlertDown           INTEGER,             -- intentionally nullable
        devCanSleep            INTEGER DEFAULT 0,
        devSkipRepeated        INTEGER DEFAULT 0,
        devLastNotification    TEXT,
        devPresentLastScan     INTEGER DEFAULT 0,
        devIsNew               INTEGER DEFAULT 0,
        devLocation            TEXT,
        devIsArchived          INTEGER DEFAULT 0,
        devParentMAC           TEXT,
        devParentPort          TEXT,
        devIcon                TEXT,
        devGUID                TEXT,
        devSite                TEXT,
        devSSID                TEXT,
        devSyncHubNode         TEXT,
        devSourcePlugin        TEXT,
        devCustomProps         TEXT,
        devFQDN                TEXT,
        devParentRelType       TEXT,
        devReqNicsOnline       INTEGER DEFAULT 0,
        devMacSource           TEXT,
        devNameSource          TEXT,
        devFQDNSource          TEXT,
        devLastIPSource        TEXT,
        devVendorSource        TEXT,
        devSSIDSource          TEXT,
        devParentMACSource     TEXT,
        devParentPortSource    TEXT,
        devParentRelTypeSource TEXT,
        devVlanSource          TEXT
    )
"""

# Includes eve_PairEventRowid — required by insert_events().
CREATE_EVENTS = """
    CREATE TABLE IF NOT EXISTS Events (
        eve_MAC               TEXT,
        eve_IP                TEXT,
        eve_DateTime          TEXT,
        eve_EventType         TEXT,
        eve_AdditionalInfo    TEXT,
        eve_PendingAlertEmail INTEGER,
        eve_PairEventRowid    INTEGER
    )
"""

CREATE_CURRENT_SCAN = """
    CREATE TABLE IF NOT EXISTS CurrentScan (
        scanMac            TEXT,
        scanLastIP         TEXT,
        scanVendor         TEXT,
        scanSourcePlugin   TEXT,
        scanName           TEXT,
        scanLastQuery      TEXT,
        scanLastConnection TEXT,
        scanSyncHubNode    TEXT,
        scanSite           TEXT,
        scanSSID           TEXT,
        scanParentMAC      TEXT,
        scanParentPort     TEXT,
        scanType           TEXT
    )
"""

CREATE_SETTINGS = """
    CREATE TABLE IF NOT EXISTS Settings (
        setKey   TEXT PRIMARY KEY,
        setValue TEXT
    )
"""


# ---------------------------------------------------------------------------
# DB factory
# ---------------------------------------------------------------------------

def make_db(sleep_minutes: int = 30) -> sqlite3.Connection:
    """
    Return a fully seeded in-memory SQLite connection with DevicesView built.

    Builds all required tables (Devices, Events, CurrentScan, Settings) and
    calls ensure_views() so DevicesView is immediately queryable.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(CREATE_DEVICES)
    cur.execute(CREATE_EVENTS)
    cur.execute(CREATE_CURRENT_SCAN)
    cur.execute(CREATE_SETTINGS)
    cur.execute(
        "INSERT OR REPLACE INTO Settings (setKey, setValue) VALUES (?, ?)",
        ("NTFPRCS_sleep_time", str(sleep_minutes)),
    )
    conn.commit()
    ensure_views(cur)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def minutes_ago(n: int) -> str:
    """Return a UTC timestamp string for *n* minutes ago."""
    dt = datetime.now(timezone.utc) - timedelta(minutes=n)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def now_utc() -> str:
    """Return the current UTC timestamp as a string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Device row factory
# ---------------------------------------------------------------------------

def insert_device(
    cur,
    mac: str,
    *,
    alert_down,
    present_last_scan: int = 0,
    can_sleep: int = 0,
    last_connection: str | None = None,
    last_ip: str = "192.168.1.1",
) -> None:
    """
    Insert a minimal Devices row.

    Parameters
    ----------
    alert_down:
        Value for devAlertDown. Pass ``None`` to store SQL NULL (tests the
        IFNULL coercion regression), ``0`` for disabled, ``1`` for enabled.
    present_last_scan:
        ``1`` = device was seen last scan (about to go down transition).
        ``0`` = device was already absent last scan.
    can_sleep:
        ``1`` enables the sleeping window for this device.
    last_connection:
        ISO-8601 UTC string; defaults to 60 minutes ago when omitted.
    last_ip:
        Value stored in devLastIP.
    """
    cur.execute(
        """
        INSERT INTO Devices
            (devMac, devAlertDown, devPresentLastScan, devCanSleep,
             devLastConnection, devLastIP, devIsArchived, devIsNew)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (mac, alert_down, present_last_scan, can_sleep,
         last_connection or minutes_ago(60), last_ip),
    )


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

def down_event_macs(cur) -> set:
    """Return the set of MACs that have a 'Device Down' event row."""
    cur.execute("SELECT eve_MAC FROM Events WHERE eve_EventType = 'Device Down'")
    return {r["eve_MAC"] for r in cur.fetchall()}


# ---------------------------------------------------------------------------
# DummyDB — minimal wrapper used by scan.session_events helpers
# ---------------------------------------------------------------------------

class DummyDB:
    """
    Minimal DB wrapper that satisfies the interface expected by
    ``session_events.insert_events()`` and related helpers.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.sql = conn.cursor()
        self._conn = conn

    def commitDB(self) -> None:
        self._conn.commit()
