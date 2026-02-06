from scan.session_events import process_scan
from unittest.mock import Mock, patch
import pytest


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
    ):
        yield


# ---------------------------------------------------
# TEST 1: Online → Offline transition
# ---------------------------------------------------
def test_device_goes_offline_when_missing_next_scan(scan_db, minimal_patches):
    conn = scan_db
    cur = conn.cursor()

    # Device initially known
    cur.execute("""
        INSERT INTO Devices (devMac, devLastIP, devPresentLastScan, devAlertDown, devAlertEvents, devIsArchived)
        VALUES ('AA','1.1.1.1',1,1,1,0)
    """)
    conn.commit()

    # FIRST SCAN — device present
    cur.execute("INSERT INTO CurrentScan (scanMac, scanLastIP) VALUES ('AA','1.1.1.1')")
    conn.commit()

    process_scan(conn)

    # Device should be online
    row = cur.execute(
        "SELECT devPresentLastScan FROM Devices WHERE devMac='AA'"
    ).fetchone()
    assert row["devPresentLastScan"] == 1

    # SECOND SCAN — device missing
    process_scan(conn)

    row = cur.execute(
        "SELECT devPresentLastScan FROM Devices WHERE devMac='AA'"
    ).fetchone()
    assert row["devPresentLastScan"] == 0


# ---------------------------------------------------
# TEST 2: Device Down event created
# ---------------------------------------------------
def test_device_down_event_created_when_missing(scan_db, minimal_patches):
    conn = scan_db
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Devices (devMac, devLastIP, devPresentLastScan, devAlertDown, devAlertEvents, devIsArchived)
        VALUES ('BB','2.2.2.2',1,1,1,0)
    """)
    conn.commit()

    # No CurrentScan entry → offline
    process_scan(conn)

    event = cur.execute("""
        SELECT eve_EventType
        FROM Events
        WHERE eve_MAC='BB'
    """).fetchone()

    assert event is not None
    assert event["eve_EventType"] == "Device Down"


# ---------------------------------------------------
# TEST 3: Guards against the "forgot to clear CurrentScan" bug
# ---------------------------------------------------
def test_offline_detection_requires_currentscan_cleanup(scan_db, minimal_patches):
    conn = scan_db
    cur = conn.cursor()

    # Device exists
    cur.execute("""
        INSERT INTO Devices (devMac, devLastIP, devPresentLastScan, devAlertDown, devAlertEvents, devIsArchived)
        VALUES ('CC','3.3.3.3',1,1,1,0)
    """)
    conn.commit()

    # First scan — device present
    cur.execute("INSERT INTO CurrentScan (scanMac, scanLastIP) VALUES ('CC','3.3.3.3')")
    conn.commit()

    process_scan(conn)

    # Simulate bug: device not seen again BUT CurrentScan not cleared
    cur.execute("INSERT INTO CurrentScan (scanMac, scanLastIP) VALUES ('CC','3.3.3.3')")
    conn.commit()

    process_scan(conn)

    row = cur.execute("""
        SELECT devPresentLastScan
        FROM Devices WHERE devMac='CC'
    """).fetchone()

    assert row["devPresentLastScan"] == 0
