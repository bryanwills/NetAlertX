# -------------------------------------------------------------------------------
# notification_sections.py — Single source of truth for notification section
# metadata: titles, SQL templates, datetime fields, and section ordering.
#
# Both reporting.py and notification_instance.py import from here.
# -------------------------------------------------------------------------------

# Canonical processing order
SECTION_ORDER = [
    "new_devices",
    "down_devices",
    "down_reconnected",
    "events",
    "plugins",
]

# Section display titles (used in text + HTML notifications)
SECTION_TITLES = {
    "new_devices": "🆕 New devices",
    "down_devices": "🔴 Down devices",
    "down_reconnected": "🔁 Reconnected down devices",
    "events": "⚡ Events",
    "plugins": "🔌 Plugins",
}

# Which column(s) contain datetime values per section (for timezone conversion)
DATETIME_FIELDS = {
    "new_devices": ["eve_DateTime"],
    "down_devices": ["eve_DateTime"],
    "down_reconnected": ["eve_DateTime"],
    "events": ["eve_DateTime"],
    "plugins": ["DateTimeChanged"],
}

# ---------------------------------------------------------------------------
# SQL templates
#
# All device sections use unified DB column names so the JSON output
# has consistent field names across new_devices, down_devices,
# down_reconnected, and events.
#
# Placeholders:
#   {condition}          — optional WHERE clause appended by condition builder
#   {alert_down_minutes} — runtime value, only used by down_devices
# ---------------------------------------------------------------------------
SQL_TEMPLATES = {
    "new_devices": """
        SELECT
            devName,
            eve_MAC,
            devVendor,
            devLastIP as eve_IP,
            eve_DateTime,
            eve_EventType,
            devComments
        FROM Events_Devices
        WHERE eve_PendingAlertEmail = 1
          AND eve_EventType = 'New Device' {condition}
        ORDER BY eve_DateTime
    """,
    "down_devices": """
        SELECT
            devName,
            eve_MAC,
            devVendor,
            eve_IP,
            eve_DateTime,
            eve_EventType,
            devComments
        FROM Events_Devices AS down_events
        WHERE eve_PendingAlertEmail = 1
          AND down_events.eve_EventType = 'Device Down'
          AND eve_DateTime < datetime('now', '-{alert_down_minutes} minutes')
          AND NOT EXISTS (
              SELECT 1
              FROM Events AS connected_events
              WHERE connected_events.eve_MAC = down_events.eve_MAC
                AND connected_events.eve_EventType = 'Connected'
                AND connected_events.eve_DateTime > down_events.eve_DateTime
          )
        ORDER BY down_events.eve_DateTime
    """,
    "down_reconnected": """
        SELECT
            devName,
            eve_MAC,
            devVendor,
            eve_IP,
            eve_DateTime,
            eve_EventType,
            devComments
        FROM Events_Devices AS reconnected_devices
        WHERE reconnected_devices.eve_EventType = 'Down Reconnected'
          AND reconnected_devices.eve_PendingAlertEmail = 1
        ORDER BY reconnected_devices.eve_DateTime
    """,
    "events": """
        SELECT
            devName,
            eve_MAC,
            devVendor,
            devLastIP as eve_IP,
            eve_DateTime,
            eve_EventType,
            devComments
        FROM Events_Devices
        WHERE eve_PendingAlertEmail = 1
          AND eve_EventType IN ('Connected', 'Down Reconnected', 'Disconnected','IP Changed') {condition}
        ORDER BY eve_DateTime
    """,
    "plugins": """
        SELECT
            Plugin,
            Object_PrimaryId,
            Object_SecondaryId,
            DateTimeChanged,
            Watched_Value1,
            Watched_Value2,
            Watched_Value3,
            Watched_Value4,
            Status
        FROM Plugins_Events
    """,
}

# Sections that support user-defined condition filters
SECTIONS_WITH_CONDITIONS = {"new_devices", "events"}

# Legacy setting key mapping for condition filters
SECTION_CONDITION_MAP = {
    "new_devices": "NTFPRCS_new_dev_condition",
    "events": "NTFPRCS_event_condition",
}
