"""
Tests for _publisher_ntfy/ntfy.py custom header parsing.

Run from inside the NetAlertX container (where the full environment is available),
or locally — in that case the NetAlertX-specific modules are stubbed out
automatically before the script is imported.

    pytest test/plugins/test_ntfy_custom_headers.py -v
"""

import os
import sys
import tempfile
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub NetAlertX-specific modules so tests can run outside the container.
# sys.modules.setdefault() is a no-op when the real module is already loaded,
# so this is safe to run inside the container too.
# ---------------------------------------------------------------------------
_tmp_log = tempfile.mkdtemp()


def _stub(name: str, **attrs):
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod


_stub("pytz", timezone=lambda tz: tz)
_stub("conf", tz=None)
_stub("const", confFileName="app.conf", logPath=_tmp_log)
_stub("plugin_helper", Plugin_Objects=MagicMock, handleEmpty=lambda v: v)
_stub("utils")
_stub("utils.datetime_utils", timeNowUTC=lambda: "2026-01-01 00:00:00")
_stub("logger", mylog=lambda *a: None, Logger=MagicMock)
_stub("helper", get_setting_value=lambda k, default="": "")
_stub("models")
_stub("models.notification_instance", NotificationInstance=MagicMock)
_stub("database", DB=MagicMock)

if "requests" not in sys.modules:
    _req = types.ModuleType("requests")
    _req.post = MagicMock
    _req_exc = types.ModuleType("requests.exceptions")
    _req_exc.InvalidHeader = type("InvalidHeader", (Exception,), {})
    _req_exc.RequestException = type("RequestException", (Exception,), {})
    _req.exceptions = _req_exc
    sys.modules["requests"] = _req
    sys.modules["requests.exceptions"] = _req_exc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server", "plugins", "_publisher_ntfy"))

from ntfy import build_custom_headers  # noqa: E402

BUILT_IN = {"Title": "NetAlertX Notification", "Authorization": "Bearer secret"}


def test_parses_a_single_header():
    assert build_custom_headers(["X-Token: abc123"], {}) == {"X-Token": "abc123"}


def test_parses_multiple_headers():
    entries = ["P-Access-Token-Id: id123", "P-Access-Token: token456"]

    assert build_custom_headers(entries, {}) == {
        "P-Access-Token-Id": "id123",
        "P-Access-Token": "token456",
    }


def test_trims_surrounding_whitespace():
    assert build_custom_headers(["  X-Token :  abc123  "], {}) == {"X-Token": "abc123"}


def test_keeps_colons_inside_the_value():
    assert build_custom_headers(["X-Token: id:secret"], {}) == {"X-Token": "id:secret"}


def test_skips_entries_without_a_separator():
    assert build_custom_headers(["X-Token abc123"], {}) == {}


def test_skips_entries_missing_a_name_or_value():
    assert build_custom_headers([": abc123", "X-Token:", "", "   "], {}) == {}


def test_skips_names_that_collide_with_a_built_in_header():
    assert build_custom_headers(["Authorization: Bearer mine"], BUILT_IN) == {}


def test_collision_check_ignores_case():
    assert build_custom_headers(["authorization: Bearer mine"], BUILT_IN) == {}


def test_keeps_the_first_of_a_repeated_name():
    assert build_custom_headers(["X-Token: first", "X-Token: second"], {}) == {"X-Token": "first"}


def test_a_bad_entry_does_not_discard_the_good_ones():
    entries = ["Authorization: Bearer mine", "malformed", "P-Access-Token: token456"]

    assert build_custom_headers(entries, BUILT_IN) == {"P-Access-Token": "token456"}


def test_no_entries_produces_no_headers():
    assert build_custom_headers([], BUILT_IN) == {}
