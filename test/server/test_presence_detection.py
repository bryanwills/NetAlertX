import sqlite3
from unittest.mock import Mock, patch

import pytest

from scan.session_events import process_scan

@pytest.fixture
def scan_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Devices
    cur.execute("""
    CREATE TABLE Devices (
      devMac TEXT PRIMARY KEY,
      devLastIP TEXT,
      devPresentLastScan INTEGER,
      devAlertDown INTEGER,
      devAlertEvents INTEGER,
      devIsArchived INTEGER DEFAULT 0
    )
    """)

    # Current scan
    cur.execute("""
    CREATE TABLE CurrentScan (
      scanMac TEXT,
      scanLastIP TEXT
    )
    """)

    # Events
    cur.execute("""
    CREATE TABLE Events (
      eve_MAC TEXT,
      eve_IP TEXT,
      eve_DateTime TEXT,
      eve_EventType TEXT,
      eve_AdditionalInfo TEXT,
      eve_PendingAlertEmail INTEGER
    )
    """)

    # LatestEventsPerMAC view
    cur.execute("""DROP VIEW IF EXISTS LatestEventsPerMAC;""")
    cur.execute("""
    CREATE VIEW LatestEventsPerMAC AS
    WITH RankedEvents AS (
        SELECT
            e.*,
            ROW_NUMBER() OVER (PARTITION BY e.eve_MAC ORDER BY e.eve_DateTime DESC) AS row_num
        FROM Events AS e
    )
    SELECT
        e.eve_MAC,
        e.eve_EventType,
        e.eve_DateTime,
        e.eve_PendingAlertEmail,
        d.devPresentLastScan,
        c.scanLastIP
    FROM RankedEvents AS e
    LEFT JOIN Devices AS d ON e.eve_MAC = d.devMac
    LEFT JOIN CurrentScan AS c ON e.eve_MAC = c.scanMac
    WHERE e.row_num = 1;
    """)

    conn.commit()

    db = Mock()
    db.sql_connection = conn
    db.sql = cur
    db.commitDB = conn.commit

    def read(query):
        return [dict(cur.execute(query).fetchone())]

    db.read = read

    yield db
    conn.close()


@pytest.fixture
def minimal_patches():
    with patch.multiple(
        "scan.session_events",
        exclude_ignored_devices=Mock(),
        save_scanned_devices=Mock(),
        print_scan_stats=Mock(),
        create_new_devices=Mock(),
        update_devices_data_from_scan=Mock(),
        update_devLastConnection_from_CurrentScan=Mock(),
        update_vendors_from_mac=Mock(),
        update_ipv4_ipv6=Mock(),
        update_icons_and_types=Mock(),
        pair_sessions_events=Mock(),
        create_sessions_snapshot=Mock(),
        insertOnlineHistory=Mock(),
        skip_repeated_notifications=Mock(),
        update_unread_notifications_count=Mock(),
        # insert_events optionally mocked depending on test
    ):
        yield


# ---------------------------------------------------
# TEST 1: Online → Offline transition
# ---------------------------------------------------


def test_device_goes_offline_when_missing_next_scan(scan_db, minimal_patches):
    db = scan_db
    cur = db.sql

    # Device initially known
    cur.execute(
        """
    INSERT INTO Devices VALUES
    ('AA','1.1.1.1',1,1,1,0)
  """
    )

    # FIRST SCAN — device present
    cur.execute("INSERT INTO CurrentScan VALUES ('AA','1.1.1.1')")
    db.commitDB()

    process_scan(db)

    # Device should be online
    row = cur.execute(
        "SELECT devPresentLastScan FROM Devices WHERE devMac='AA'"
    ).fetchone()
    assert row["devPresentLastScan"] == 1

    # SECOND SCAN — device missing
    # (CurrentScan was cleared by process_scan)
    process_scan(db)

    row = cur.execute(
        "SELECT devPresentLastScan FROM Devices WHERE devMac='AA'"
    ).fetchone()

    assert row["devPresentLastScan"] == 0


# ---------------------------------------------------
# TEST 2: Device Down event created
# ---------------------------------------------------


def test_device_down_event_created_when_missing(scan_db, minimal_patches):
    db = scan_db
    cur = db.sql

    cur.execute(
        """
    INSERT INTO Devices VALUES
    ('BB','2.2.2.2',1,1,1,0)
  """
    )

    # No CurrentScan entry → offline
    process_scan(db)

    event = cur.execute(
        """
            SELECT eve_EventType
            FROM Events
            WHERE eve_MAC='BB'
        """
    ).fetchone()

    assert event is not None
    assert event["eve_EventType"] == "Device Down"


# ---------------------------------------------------
# TEST 3: Guards against the "forgot to clear CurrentScan" bug
# ---------------------------------------------------


def test_offline_detection_requires_currentscan_cleanup(scan_db, minimal_patches):
    """
    This test FAILS if CurrentScan is not cleared.
    """
    db = scan_db
    cur = db.sql

    # Device exists
    cur.execute(
        """
    INSERT INTO Devices VALUES
    ('CC','3.3.3.3',1,1,1,0)
  """
    )

    # First scan — device present
    cur.execute("INSERT INTO CurrentScan VALUES ('CC','3.3.3.3')")
    db.commitDB()

    process_scan(db)

    # Simulate bug: device not seen again BUT CurrentScan not cleared
    # (reinsert old entry like stale data)
    cur.execute("INSERT INTO CurrentScan VALUES ('CC','3.3.3.3')")
    db.commitDB()

    process_scan(db)

    row = cur.execute(
        """
    SELECT devPresentLastScan
    FROM Devices WHERE devMac='CC'
  """
    ).fetchone()

    # If CurrentScan works correctly, device should be offline
    assert row["devPresentLastScan"] == 0
