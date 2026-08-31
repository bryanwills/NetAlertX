"""
Tests for the __template plugin scaffold (server/plugins/__template/rename_me.py).

This is the copy-paste starting point for every new plugin, so keeping it
covered by a passing test (and demonstrating the expected test shape) gives
new plugin authors something to copy alongside the script itself.

Run from inside the NetAlertX container, or locally - NetAlertX-specific
modules are stubbed out automatically before the script is imported.

    pytest "test/plugins/test___template.py" -v
"""

import os
import sys
import tempfile
import types
from unittest.mock import MagicMock

_tmp_log = tempfile.mkdtemp()
_tmp_db = tempfile.mkdtemp()


def _stub(name: str, **attrs):
    # Additive: several plugin test files stub the same generic module names
    # (helper, plugin_helper, const, ...) with different attribute subsets.
    # If another test already registered this name, add whatever attributes
    # it doesn't have yet instead of skipping outright - a plain skip-if-
    # present guard makes collection order decide which test's dependencies
    # win, breaking whichever test runs later in the same pytest session.
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        if not hasattr(mod, k):
            setattr(mod, k, v)


_stub("pytz", timezone=lambda tz: tz)
_stub("conf")
_stub("const", dataPath=_tmp_db, dbFolderPath=_tmp_db, configPath=_tmp_db, logPath=_tmp_log)
_stub("plugin_helper", Plugin_Objects=MagicMock)
_stub("logger", mylog=lambda *a: None, Logger=MagicMock)
_stub("helper", get_setting_value=lambda k: "")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server", "plugins", "__template"))

import rename_me  # noqa: E402


class TestGetDeviceData:
    def test_returns_the_sample_devices(self):
        data = rename_me.get_device_data(some_setting="anything")
        assert len(data) == 2
        assert {d["mac_address"] for d in data} == {"00:11:22:33:44:55", "00:11:22:33:44:66"}
        for device in data:
            for key in ("mac_address", "ip_address", "hostname", "vendor", "device_type", "last_seen"):
                assert key in device


class TestMain:
    def test_writes_one_object_per_device_and_result_file_once(self):
        rename_me.plugin_objects = MagicMock()
        rename_me.plugin_objects.__len__ = lambda self: 2

        rename_me.main()

        assert rename_me.plugin_objects.add_object.call_count == 2
        rename_me.plugin_objects.write_result_file.assert_called_once()
