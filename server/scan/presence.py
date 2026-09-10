import re

_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def current_scan_presence_condition(mac_column: str) -> str:
    """SQL fragment: TRUE if any CurrentScan row for mac_column asserts presence.
    The one and only definition of 'is this MAC present this cycle' - every
    caller uses this, nobody writes their own CurrentScan presence predicate.

    mac_column MUST be a trusted, hardcoded SQL column/table.column reference
    written by NetAlertX code (e.g. "devMac", "CurrentScan.scanMac") - this
    function does raw string interpolation, not parameterized SQL. Never pass
    plugin data, user input, or any runtime string value here.

    Not usable everywhere a presence check appears: the "New Connections"
    query in session_events.py and the raw Sessions insert in
    create_new_devices() (device_handling.py) both need the actual
    scanLastIP/scanVendor *values* off the presence-asserting row via a
    MIN()/GROUP BY aggregate, not just a boolean - see
    scan-pipeline-hardening.md Design §1's correction for why those two
    (plus "IP Changed", an eighth non-canonical site) keep their own
    hand-written aggregation instead of calling this helper.
    """
    if not _SQL_IDENTIFIER_RE.match(mac_column):
        raise ValueError(f"mac_column must be a plain identifier, got: {mac_column!r}")
    return f"""EXISTS (
        SELECT 1 FROM CurrentScan
        WHERE scanMac = {mac_column} AND scanPresence = 1
    )"""
