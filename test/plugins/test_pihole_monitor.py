"""Tests for the pihole_monitor (PIHOLEMON) plugin.

pihole_monitor.py is loaded with its NetAlertX-internal dependencies
(plugin_helper, logger, helper, const, conf, pytz, utils.*) stubbed out,
the same approach test_mikrotik_scan.py uses - it keeps these tests
runnable without the full devcontainer environment and without any live
Pi-hole. `requests` itself is left real; individual HTTP calls are mocked
per test.

Layout:
  - PiholeSource.auth() / fetch_top_blocked_clients(): unit tests against
    a mocked `requests`, covering the auth success/failure paths and the
    None-sentinel-on-failure contract (vs. a genuine empty {}).
  - build_ip_to_mac(): pure-function unit tests for the multi-IP-per-MAC
    fix (a device must not lose its other IPs to the by-MAC merge).
  - main(): integration tests with PiholeSource's network-touching
    methods stubbed at the object level, covering source aggregation,
    the stats_complete gate (a failed fetch must not corrupt a device's
    history with a false zero), and the history_length boundary clamp.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests


def _is_mac(value):
    """Same shape as plugin_helper.is_mac, without pytz as a dependency."""
    import re
    s = str(value).lower().strip()
    return bool(re.match(r"^[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\1[0-9a-f]{2}){4}$", s))


def _load_pihole_monitor_module():
    missing_module = object()
    previous_modules = {}

    def stub(name, **attributes):
        previous_modules[name] = sys.modules.get(name, missing_module)
        module = types.ModuleType(name)
        for attribute, value in attributes.items():
            setattr(module, attribute, value)
        sys.modules[name] = module

    stub("plugin_helper", Plugin_Objects=MagicMock, is_mac=_is_mac)
    stub("logger", mylog=MagicMock(), Logger=MagicMock())
    stub("helper", get_setting_value=MagicMock(return_value="UTC"))
    stub("const", logPath="/tmp")
    stub("conf", tz=None)
    stub("pytz", timezone=MagicMock(return_value="UTC"))
    stub("utils")
    stub("utils.datetime_utils", timeNowUTC=MagicMock())
    stub("utils.crypto_utils", string_to_fake_mac=lambda s: "fa:ce:00:00:00:01")

    module_path = Path(__file__).resolve().parents[2] / "server" / "plugins" / "pihole_monitor" / "pihole_monitor.py"
    spec = importlib.util.spec_from_file_location("pihole_monitor", module_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        for name, previous_module in previous_modules.items():
            if previous_module is missing_module:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous_module

    return module


pihole_monitor = _load_pihole_monitor_module()


def _resp(json_data):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data)
    return resp


# ---------------------------------------------------------------------------
# PiholeSource.auth()
# ---------------------------------------------------------------------------


def test_auth_success_stores_sid_and_csrf():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    with patch("requests.post", return_value=_resp({"session": {"valid": True, "sid": "abc", "csrf": "xyz"}})):
        assert source.auth() is True
    assert source.sid == "abc"
    assert source.csrf == "xyz"


def test_auth_invalid_session_returns_false():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "wrongpw", True, 5)
    with patch("requests.post", return_value=_resp({"session": {"valid": False}})):
        assert source.auth() is False
    assert source.sid is None


def test_auth_connection_error_returns_false_without_raising():
    import requests as real_requests
    source = pihole_monitor.PiholeSource("primary", "http://unreachable/", "pw", True, 5)
    with patch("requests.post", side_effect=real_requests.exceptions.ConnectionError("no route")):
        assert source.auth() is False
    assert source.sid is None


def test_auth_unconfigured_source_short_circuits():
    source = pihole_monitor.PiholeSource("secondary", "", "", True, 5)
    with patch("requests.post") as mock_post:
        assert source.auth() is False
    mock_post.assert_not_called()


def test_auth_timeout_returns_false():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    with patch("requests.post", side_effect=requests.exceptions.Timeout("slow")):
        assert source.auth() is False
    assert source.sid is None


def test_auth_unexpected_error_returns_false():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    with patch("requests.post", side_effect=ValueError("boom")):
        assert source.auth() is False


def test_auth_unparseable_json_returns_false():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(side_effect=ValueError("not json"))
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    with patch("requests.post", return_value=resp):
        assert source.auth() is False


def test_auth_disables_insecure_warning_when_verify_ssl_off():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", False, 5)
    session_resp = _resp({"session": {"valid": True, "sid": "s", "csrf": "c"}})
    with patch("requests.post", return_value=session_resp), \
         patch("requests.packages.urllib3.disable_warnings") as mock_disable:
        assert source.auth() is True
    mock_disable.assert_called_once()


# ---------------------------------------------------------------------------
# PiholeSource.deauth()
# ---------------------------------------------------------------------------


def test_deauth_clears_session_on_success():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    source.sid = "sid"
    source.csrf = "csrf"
    with patch("requests.delete", return_value=_resp({})) as mock_delete:
        source.deauth()
    mock_delete.assert_called_once()
    assert source.sid is None
    assert source.csrf is None


def test_deauth_swallows_request_errors():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    source.sid = "sid"
    with patch("requests.delete", side_effect=requests.exceptions.ConnectionError("gone")):
        source.deauth()  # must not raise
    assert source.sid is None


def test_deauth_noop_without_an_active_session():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    with patch("requests.delete") as mock_delete:
        source.deauth()
    mock_delete.assert_not_called()


# ---------------------------------------------------------------------------
# PiholeSource.fetch_devices()
# ---------------------------------------------------------------------------


def test_fetch_devices_success_returns_device_list():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    source.sid = "sid"
    source.csrf = "csrf"  # also exercises _headers() including X-FTL-CSRF
    payload = {"devices": [{"hwaddr": "aa:bb:cc:dd:ee:01"}]}
    with patch("requests.get", return_value=_resp(payload)) as mock_get:
        result = source.fetch_devices(max_clients=500)
    assert result == [{"hwaddr": "aa:bb:cc:dd:ee:01"}]
    assert mock_get.call_args.kwargs["params"] == {"max_devices": "500", "max_addresses": "2"}


def test_fetch_devices_failure_returns_empty_list():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    source.sid = "sid"
    with patch("requests.get", side_effect=requests.exceptions.Timeout("slow")):
        assert source.fetch_devices(max_clients=500) == []


def test_fetch_devices_without_session_returns_empty_list():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    with patch("requests.get") as mock_get:
        assert source.fetch_devices(max_clients=500) == []
    mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# netalertx_device_owner()
# ---------------------------------------------------------------------------


def test_netalertx_device_owner_returns_empty_without_url():
    assert pihole_monitor.netalertx_device_owner(None, "token", "aa:bb:cc:dd:ee:01", 5) == ''


def test_netalertx_device_owner_returns_owner_on_success():
    payload = {"data": {"devices": {"devices": [{"devMac": "aa:bb:cc:dd:ee:01", "devOwner": "Mauricio"}]}}}
    with patch("requests.post", return_value=_resp(payload)) as mock_post:
        owner = pihole_monitor.netalertx_device_owner("http://nax/graphql", "tok", "aa:bb:cc:dd:ee:01", 5)
    assert owner == "Mauricio"
    assert mock_post.call_args.kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_netalertx_device_owner_returns_empty_when_device_unknown():
    payload = {"data": {"devices": {"devices": []}}}
    with patch("requests.post", return_value=_resp(payload)):
        owner = pihole_monitor.netalertx_device_owner("http://nax/graphql", "", "aa:bb:cc:dd:ee:01", 5)
    assert owner == ''


def test_netalertx_device_owner_returns_empty_on_request_error():
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("down")):
        owner = pihole_monitor.netalertx_device_owner("http://nax/graphql", "tok", "aa:bb:cc:dd:ee:01", 5)
    assert owner == ''


# ---------------------------------------------------------------------------
# gather_device_entries() - skip branches and the fake-MAC fallback
# ---------------------------------------------------------------------------


def test_gather_device_entries_skips_invalid_hwaddr_empty_ips_and_placeholder_ip():
    devices = [
        {"hwaddr": "00:00:00:00:00:00", "ips": [{"ip": "10.0.0.1"}]},  # excluded hwaddr
        {"hwaddr": "", "ips": [{"ip": "10.0.0.2"}]},                    # missing hwaddr
        {"hwaddr": "aa:bb:cc:dd:ee:01", "ips": []},                     # no ips at all
        {"hwaddr": "aa:bb:cc:dd:ee:02", "ips": [{"ip": "0.0.0.0"}]},    # only a placeholder ip
        {"hwaddr": "aa:bb:cc:dd:ee:03", "ips": [{"ip": "10.0.0.3", "lastSeen": 1000}]},  # the one real entry
    ]
    source = MagicMock()
    source.fetch_devices.return_value = devices
    entries = pihole_monitor.gather_device_entries(source, consider_online=300, fake_mac=False, max_clients=500)
    assert [e["mac"] for e in entries] == ["aa:bb:cc:dd:ee:03"]


def test_gather_device_entries_fake_mac_fallback_for_invalid_hwaddr():
    devices = [{"hwaddr": "not-a-real-mac", "ips": [{"ip": "10.0.0.9", "lastSeen": 1000}]}]
    source = MagicMock()
    source.fetch_devices.return_value = devices
    entries = pihole_monitor.gather_device_entries(source, consider_online=300, fake_mac=True, max_clients=500)
    assert entries[0]["mac"] == "fa:ce:00:00:00:01"  # from the stubbed string_to_fake_mac


# ---------------------------------------------------------------------------
# PiholeSource.fetch_top_blocked_clients() - None sentinel vs. genuine {}
# ---------------------------------------------------------------------------


def test_fetch_top_blocked_clients_success_returns_dict():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    source.sid = "sid"
    payload = {"clients": [{"ip": "10.0.0.5", "count": 12}, {"ip": "10.0.0.6", "count": 0}]}
    with patch("requests.get", return_value=_resp(payload)) as mock_get:
        result = source.fetch_top_blocked_clients(count=123)
    assert result == {"10.0.0.5": 12, "10.0.0.6": 0}
    assert mock_get.call_args.kwargs["params"] == {"blocked": "true", "count": 123}


def test_fetch_top_blocked_clients_genuine_empty_is_not_none():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    source.sid = "sid"
    with patch("requests.get", return_value=_resp({"clients": []})):
        result = source.fetch_top_blocked_clients(count=500)
    assert result == {}


def test_fetch_top_blocked_clients_failure_returns_none_not_empty_dict():
    import requests as real_requests
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    source.sid = "sid"
    with patch("requests.get", side_effect=real_requests.exceptions.Timeout("slow")):
        result = source.fetch_top_blocked_clients(count=500)
    assert result is None


def test_fetch_top_blocked_clients_without_session_returns_none():
    source = pihole_monitor.PiholeSource("primary", "http://ph1/", "pw", True, 5)
    assert source.fetch_top_blocked_clients(count=500) is None


# ---------------------------------------------------------------------------
# build_ip_to_mac() - a multi-IP device must not lose its other IPs
# ---------------------------------------------------------------------------


def _entry(mac, ip, last_seen):
    return {"mac": mac, "ip": ip, "name": "", "macVendor": "", "lastSeen": last_seen, "is_online": True}


def test_build_ip_to_mac_keeps_every_ip_of_a_multi_ip_device():
    entries = [
        _entry("aa:bb:cc:dd:ee:01", "10.0.0.5", 100),
        _entry("aa:bb:cc:dd:ee:01", "10.0.0.6", 90),  # same device, second IP, older lastSeen
    ]
    ip_to_mac = pihole_monitor.build_ip_to_mac(entries)
    assert ip_to_mac == {"10.0.0.5": "aa:bb:cc:dd:ee:01", "10.0.0.6": "aa:bb:cc:dd:ee:01"}


def test_build_ip_to_mac_freshest_mac_wins_on_ip_reassignment():
    entries = [
        _entry("aa:bb:cc:dd:ee:01", "10.0.0.5", 100),  # older MAC on this IP
        _entry("aa:bb:cc:dd:ee:02", "10.0.0.5", 200),  # DHCP reassigned, newer
    ]
    ip_to_mac = pihole_monitor.build_ip_to_mac(entries)
    assert ip_to_mac == {"10.0.0.5": "aa:bb:cc:dd:ee:02"}


def test_build_ip_to_mac_differs_from_naive_merged_result():
    """Regression guard for the original bug: deriving the IP map from
    merge_device_entries()'s output (one entry per MAC) drops a device's
    other IPs. build_ip_to_mac() must not do that."""
    entries = [
        _entry("aa:bb:cc:dd:ee:01", "10.0.0.5", 100),
        _entry("aa:bb:cc:dd:ee:01", "10.0.0.6", 90),
    ]
    merged = pihole_monitor.merge_device_entries(entries)
    naive_ip_to_mac = {e["ip"]: mac for mac, e in merged.items()}
    assert naive_ip_to_mac == {"10.0.0.5": "aa:bb:cc:dd:ee:01"}  # the bug: 10.0.0.6 missing

    fixed_ip_to_mac = pihole_monitor.build_ip_to_mac(entries)
    assert "10.0.0.6" in fixed_ip_to_mac


# ---------------------------------------------------------------------------
# main() - orchestration, with PiholeSource's network methods stubbed
# ---------------------------------------------------------------------------


def _device_payload(mac, ip, name="dev", vendor="Acme", last_seen=1000):
    return {"hwaddr": mac, "macVendor": vendor, "ips": [{"ip": ip, "name": name, "lastSeen": last_seen}]}


class _Settings(dict):
    """get_setting_value side_effect backed by a dict, with the plugin's
    own defaults for anything a test doesn't override."""

    _DEFAULTS = {
        "PIHOLEMON_VERIFY_SSL": True,
        "PIHOLEMON_RUN_TIMEOUT": 5,
        "PIHOLEMON_GET_OFFLINE": False,
        "PIHOLEMON_FAKE_MAC": False,
        "PIHOLEMON_API_MAXCLIENTS": 500,
        "PIHOLEMON_CONSIDER_ONLINE": 300,
        "PIHOLEMON_GRAPHQL_URL": None,
        "PIHOLEMON_GRAPHQL_TOKEN": None,
        "PIHOLEMON_MULTIPLIER": 4,
        "PIHOLEMON_MIN_BLOCKED": 1,
        "PIHOLEMON_HISTORY_LENGTH": 28,
        "PIHOLEMON_PRIMARY_URL": "http://ph1/",
        "PIHOLEMON_PRIMARY_PASSWORD": "pw1",
        "PIHOLEMON_SECONDARY_URL": "",
        "PIHOLEMON_SECONDARY_PASSWORD": "",
    }

    def __call__(self, key):
        if key in self:
            return self[key]
        return self._DEFAULTS[key]


@pytest.fixture
def settings():
    return _Settings()


@pytest.fixture
def isolated_state(tmp_path, settings):
    """Points STATE_FILE/RESULT_FILE at a scratch dir and wires up
    get_setting_value, for every main()-level test."""
    with patch.object(pihole_monitor, "STATE_FILE", str(tmp_path / "state.json")), \
         patch.object(pihole_monitor, "RESULT_FILE", str(tmp_path / "last_result.log")), \
         patch.object(pihole_monitor, "get_setting_value", side_effect=settings), \
         patch.object(pihole_monitor.PiholeSource, "auth", return_value=True), \
         patch.object(pihole_monitor.PiholeSource, "deauth", return_value=None):
        yield tmp_path


def test_main_aggregates_blocked_counts_from_both_sources(isolated_state, settings):
    settings["PIHOLEMON_SECONDARY_URL"] = "http://ph2/"
    settings["PIHOLEMON_SECONDARY_PASSWORD"] = "pw2"

    devices_by_label = {
        "primary": [_device_payload("aa:bb:cc:dd:ee:01", "10.0.0.5")],
        "secondary": [_device_payload("aa:bb:cc:dd:ee:01", "10.0.0.5")],
    }
    blocked_by_label = {"primary": {"10.0.0.5": 30}, "secondary": {"10.0.0.5": 15}}

    def _fetch_devices(self, max_clients):
        return devices_by_label[self.label]

    def _fetch_top_blocked(self, count):
        return blocked_by_label[self.label]

    with patch.object(pihole_monitor.PiholeSource, "fetch_devices", _fetch_devices), \
         patch.object(pihole_monitor.PiholeSource, "fetch_top_blocked_clients", _fetch_top_blocked), \
         patch.object(pihole_monitor, "Plugin_Objects") as mock_plugin_objects:
        assert pihole_monitor.main() == 0

    instance = mock_plugin_objects.return_value
    (call,) = instance.add_object.call_args_list
    # Not imported twice (one device-import row) and its blocked counts
    # from both instances are summed, not compared/overwritten.
    assert call.kwargs["primaryId"] == "aa:bb:cc:dd:ee:01"
    assert call.kwargs["watched3"] == "45"


def test_main_stats_complete_false_when_a_source_fetch_fails(isolated_state, settings):
    """A failed top_clients fetch must not write a false zero into a
    device's history, and must not evaluate an anomaly this run."""
    device = [_device_payload("aa:bb:cc:dd:ee:01", "10.0.0.5")]

    with patch.object(pihole_monitor.PiholeSource, "fetch_devices", return_value=device), \
         patch.object(pihole_monitor.PiholeSource, "fetch_top_blocked_clients", return_value=None), \
         patch.object(pihole_monitor, "Plugin_Objects") as mock_plugin_objects:
        # Seed a history so a baseline exists and would trip the multiplier
        # if (incorrectly) evaluated against a written-in zero.
        pihole_monitor.save_state({"aa:bb:cc:dd:ee:01": [40, 42, 38]})
        assert pihole_monitor.main() == 0

    instance = mock_plugin_objects.return_value
    (call,) = instance.add_object.call_args_list
    assert call.kwargs["watched4"] == "normal"  # not "anomaly" - stats were incomplete

    state_after = pihole_monitor.load_state()
    assert state_after["aa:bb:cc:dd:ee:01"] == [40, 42, 38]  # untouched, no false 0 appended


def test_main_records_anomaly_when_stats_are_complete(isolated_state, settings):
    settings["PIHOLEMON_MULTIPLIER"] = 2
    settings["PIHOLEMON_MIN_BLOCKED"] = 5
    device = [_device_payload("aa:bb:cc:dd:ee:01", "10.0.0.5")]

    with patch.object(pihole_monitor.PiholeSource, "fetch_devices", return_value=device), \
         patch.object(pihole_monitor.PiholeSource, "fetch_top_blocked_clients", return_value={"10.0.0.5": 50}), \
         patch.object(pihole_monitor, "Plugin_Objects") as mock_plugin_objects:
        pihole_monitor.save_state({"aa:bb:cc:dd:ee:01": [10, 10, 10]})  # baseline avg 10, 50 >> 2x
        assert pihole_monitor.main() == 0

    instance = mock_plugin_objects.return_value
    (call,) = instance.add_object.call_args_list
    assert call.kwargs["watched4"] == "anomaly"

    state_after = pihole_monitor.load_state()
    assert state_after["aa:bb:cc:dd:ee:01"] == [10, 10, 10, 50]


@pytest.mark.parametrize(
    ("configured_length", "expected_history"),
    [
        (-5, [40]),              # negative - must clamp to 1, keeping only the newest sample
        (0, [10, 20, 30, 40]),   # falsy - already falls back to 28 via `or`, nothing trimmed
        (1, [40]),               # explicit 1 - only the newest sample survives
        (28, [10, 20, 30, 40]),  # the documented default - well under the cap, nothing trimmed
    ],
)
def test_main_history_length_clamps_and_trims_exactly(isolated_state, settings, configured_length, expected_history):
    """Distinct, ordered seed values (not len() alone) so a wrong slice
    window - e.g. a length-1 clamp that actually kept 4 items, which a
    bare `len(history) >= 1` check would miss - shows up as a mismatch."""
    settings["PIHOLEMON_HISTORY_LENGTH"] = configured_length
    device = [_device_payload("aa:bb:cc:dd:ee:01", "10.0.0.5")]

    with patch.object(pihole_monitor.PiholeSource, "fetch_devices", return_value=device), \
         patch.object(pihole_monitor.PiholeSource, "fetch_top_blocked_clients", return_value={"10.0.0.5": 40}), \
         patch.object(pihole_monitor, "Plugin_Objects"):
        pihole_monitor.save_state({"aa:bb:cc:dd:ee:01": [10, 20, 30]})
        assert pihole_monitor.main() == 0

    history = pihole_monitor.load_state()["aa:bb:cc:dd:ee:01"]
    assert history == expected_history


def test_main_returns_1_when_no_source_is_configured(isolated_state, settings):
    settings["PIHOLEMON_PRIMARY_URL"] = ""
    settings["PIHOLEMON_PRIMARY_PASSWORD"] = ""
    assert pihole_monitor.main() == 1


def test_main_marks_stats_incomplete_when_a_source_fails_to_authenticate(tmp_path, settings):
    """Also exercises the CONSIDER_ONLINE fallback (a non-int setting falls
    back to 300) alongside the per-source auth-failure branch, which needs
    per-label auth behavior rather than the isolated_state fixture's
    blanket auth=True."""
    settings["PIHOLEMON_SECONDARY_URL"] = "http://ph2/"
    settings["PIHOLEMON_SECONDARY_PASSWORD"] = "badpw"
    settings["PIHOLEMON_CONSIDER_ONLINE"] = "not-a-number"

    def _auth(self):
        return self.label == "primary"  # secondary fails to authenticate

    device = [_device_payload("aa:bb:cc:dd:ee:01", "10.0.0.5")]

    with patch.object(pihole_monitor, "STATE_FILE", str(tmp_path / "state.json")), \
         patch.object(pihole_monitor, "RESULT_FILE", str(tmp_path / "last_result.log")), \
         patch.object(pihole_monitor, "get_setting_value", side_effect=settings), \
         patch.object(pihole_monitor.PiholeSource, "auth", _auth), \
         patch.object(pihole_monitor.PiholeSource, "deauth", return_value=None), \
         patch.object(pihole_monitor.PiholeSource, "fetch_devices", return_value=device), \
         patch.object(pihole_monitor.PiholeSource, "fetch_top_blocked_clients", return_value={"10.0.0.5": 999}), \
         patch.object(pihole_monitor, "Plugin_Objects") as mock_plugin_objects:
        pihole_monitor.save_state({"aa:bb:cc:dd:ee:01": [1, 1, 1]})
        assert pihole_monitor.main() == 0

        instance = mock_plugin_objects.return_value
        (call,) = instance.add_object.call_args_list
        assert call.kwargs["watched4"] == "normal"  # secondary's auth failure marks stats incomplete
        assert pihole_monitor.load_state()["aa:bb:cc:dd:ee:01"] == [1, 1, 1]  # history untouched


def test_main_links_offline_device_resolves_owner_skips_invalid_mac_and_tracks_unknown_ip(isolated_state, settings):
    """One run covering four branches at once: an offline device still
    gets its blocked traffic linked to its real MAC (not a bare IP), an
    online device gets its devOwner resolved via GraphQL, a device with an
    invalid hardware address is skipped entirely, and blocked traffic on
    an IP no device was ever seen on falls back to being tracked under
    that bare IP."""
    settings["PIHOLEMON_GRAPHQL_URL"] = "http://nax/graphql"
    settings["PIHOLEMON_GRAPHQL_TOKEN"] = "tok"

    now = MagicMock()
    now.timestamp.return_value = 2_000_000

    devices = [
        {"hwaddr": "aa:bb:cc:dd:ee:01", "macVendor": "Acme",
         "ips": [{"ip": "10.0.0.1", "name": "online-dev", "lastSeen": 2_000_000 - 10}]},        # online
        {"hwaddr": "aa:bb:cc:dd:ee:02", "macVendor": "Acme",
         "ips": [{"ip": "10.0.0.2", "name": "offline-dev", "lastSeen": 2_000_000 - 10_000}]},   # offline
        {"hwaddr": "not-a-real-mac", "macVendor": "Acme",
         "ips": [{"ip": "10.0.0.3", "name": "bad-mac-dev", "lastSeen": 2_000_000 - 10}]},        # invalid MAC
    ]
    blocked = {"10.0.0.1": 5, "10.0.0.2": 5, "10.0.0.99": 5}  # .99: never any device's IP
    owner_resp = _resp({"data": {"devices": {"devices": [{"devOwner": "Mauricio"}]}}})

    with patch.object(pihole_monitor, "timeNowUTC", return_value=now), \
         patch.object(pihole_monitor.PiholeSource, "fetch_devices", return_value=devices), \
         patch.object(pihole_monitor.PiholeSource, "fetch_top_blocked_clients", return_value=blocked), \
         patch("requests.post", return_value=owner_resp), \
         patch.object(pihole_monitor, "Plugin_Objects") as mock_plugin_objects:
        assert pihole_monitor.main() == 0

    instance = mock_plugin_objects.return_value
    calls_by_primary_id = {c.kwargs["primaryId"]: c for c in instance.add_object.call_args_list}

    assert "owner: Mauricio" in calls_by_primary_id["aa:bb:cc:dd:ee:01"].kwargs["extra"]
    assert calls_by_primary_id["aa:bb:cc:dd:ee:02"].kwargs["foreignKey"] == "aa:bb:cc:dd:ee:02"
    assert "not-a-real-mac" not in calls_by_primary_id
    assert calls_by_primary_id["10.0.0.99"].kwargs["foreignKey"] == "null"
