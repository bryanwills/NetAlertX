"""Tests for the dockerdisc (DOCKERDISC) plugin.

script.py is loaded with its NetAlertX-internal dependencies
(plugin_helper, logger, helper, const, conf, pytz, database) stubbed out,
the same approach test_pihole_monitor.py uses - it keeps these tests
runnable without the full devcontainer environment and without a live
Docker Socket Proxy. `requests` itself is left real; individual HTTP calls
are mocked per test. `handleEmpty`/`normalize_mac`/`decode_settings_base64`
are reimplemented locally (same shape as plugin_helper's) rather than
imported, to avoid pulling in plugin_helper's own dependency chain.

Layout:
  - pick_lan_network() / first_network_driver(): pure-function unit tests
    for the macvlan/ipvlan network-selection logic (spec §6), given a
    {NetworkID: Driver} lookup - Driver isn't inline on a container's own
    NetworkSettings.Networks entry (confirmed 2026-09-08 against a real
    Socket Proxy - see script.py's module docstring), so these always take
    that lookup as a separate argument. A container with no LAN-visible
    network must still get a driver name, just no MAC/IP. A container with
    *more than one* macvlan/ipvlan network at once deterministically picks
    the alphabetically-first network name (spec §9's decided tie-break).
  - DockerHost.get_network_drivers(): unit tests for the batched
    GET /networks?filters=... call - one request for every unique
    NetworkID, not one per network, and a safe {} (not a crash) when the
    Socket Proxy denies it (missing NETWORKS=1).
  - resolve_host_mac(): unit tests for the manual-MAC-short-circuits-
    without-any-request-first, else /info -> devName match chain (spec
    §3.2) - a configured DOCKERDISC_HOST_MAC wins immediately with zero
    Socket Proxy calls (deliberate: no auto-re-verification once you've
    told us the answer), so auto-detection only ever runs when it's
    empty, and only then can hostname-unmatched or /info-unreachable
    resolve to None.
  - lookup_device_mac(): unit test for the "host must already exist, this
    plugin never creates it" gate - explicit COLLATE NOCASE, not just
    relied on from the Devices.devMac column definition.
  - process_host(): integration tests with DockerHost's network-touching
    methods stubbed at the object level - covers a mixed macvlan+bridge
    container list (only the macvlan one gets a MAC/IP), an unconfigured
    entry (no proxy URL) short-circuiting before any request, and a host
    MAC that doesn't resolve to a known device short-circuiting before
    /containers/json is ever called.

All of the above was additionally run live, end to end, against a real
Docker Engine + a real tecnativa/docker-socket-proxy on 2026-09-08 (ad-hoc
harness, not part of this repo) - that run is what caught the Driver-not-
inline bug these tests now guard against.
"""

import base64
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests


def _handle_empty(value):
    """Same shape as plugin_helper.handleEmpty, without its import chain."""
    return value if value else 'null'


def _normalize_mac(mac):
    """Same shape as plugin_helper.normalize_mac, without its import chain."""
    s = str(mac).strip().lower()
    if s == "internet":
        return "internet"
    if ':' in s:
        parts = s.split(':')
    elif '-' in s:
        parts = s.split('-')
    else:
        parts = [s[i:i + 2] for i in range(0, len(s), 2)]
    return ':'.join(p if p == '*' else p.zfill(2) for p in (part.strip() for part in parts))


def _decode_settings_base64(encoded_str):
    """Same shape as plugin_helper.decode_settings_base64 (convert_types=True)."""
    settings_list = json.loads(base64.b64decode(encoded_str).decode("utf-8"))
    out = {}
    for _, key, _type, value in settings_list:
        t = _type.lower()
        if t == "boolean":
            out[key] = value.lower() == "true"
        elif t == "integer":
            out[key] = int(value)
        elif t == "float":
            out[key] = float(value)
        else:
            out[key] = value
    return out


def _encode_host_entry(proxy_url, host_mac):
    """Builds a base64-encoded popUpForm entry matching what NetAlertX
    would send for one `DOCKERDISC_hosts` row."""
    settings_list = [
        ["DOCKERDISC_hosts", "DOCKERDISC_SOCKET_PROXY_URL", "string", proxy_url],
        ["DOCKERDISC_hosts", "DOCKERDISC_HOST_MAC", "string", host_mac or ""],
    ]
    return base64.b64encode(json.dumps(settings_list).encode("utf-8")).decode("ascii")


def _load_dockerdisc_module():
    missing_module = object()
    previous_modules = {}

    def stub(name, **attributes):
        previous_modules[name] = sys.modules.get(name, missing_module)
        module = types.ModuleType(name)
        for attribute, value in attributes.items():
            setattr(module, attribute, value)
        sys.modules[name] = module

    stub(
        "plugin_helper",
        Plugin_Objects=MagicMock,
        handleEmpty=_handle_empty,
        normalize_mac=_normalize_mac,
        decode_settings_base64=_decode_settings_base64,
    )
    stub("logger", mylog=MagicMock(), Logger=MagicMock())
    stub("helper", get_setting_value=MagicMock(return_value="UTC"))
    stub("const", logPath="/tmp")
    stub("database", get_temp_db_connection=MagicMock())
    stub("conf", tz=None)
    stub("pytz", timezone=MagicMock(return_value="UTC"))

    module_path = Path(__file__).resolve().parents[2] / "server" / "plugins" / "dockerdisc" / "script.py"
    spec = importlib.util.spec_from_file_location("dockerdisc_script", module_path)
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


dockerdisc = _load_dockerdisc_module()


def _resp(json_data):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data)
    return resp


def _db_returning(rows):
    """A get_temp_db_connection() replacement whose cursor().fetchone()
    yields successive `rows` entries (one per execute() call), then None."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.fetchone.side_effect = list(rows) + [None] * 10
    return conn


# ---------------------------------------------------------------------------
# pick_lan_network() / first_network_driver()
# ---------------------------------------------------------------------------


def test_pick_lan_network_prefers_macvlan():
    networks = {
        "bridge": {"NetworkID": "net-bridge", "MacAddress": "02:aa:aa:aa:aa:aa", "IPAddress": "172.17.0.2"},
        "lan": {"NetworkID": "net-lan", "MacAddress": "aa:bb:cc:dd:ee:ff", "IPAddress": "192.168.1.50"},
    }
    driver_by_id = {"net-bridge": "bridge", "net-lan": "macvlan"}
    name, driver, network = dockerdisc.pick_lan_network(networks, driver_by_id)
    assert driver == "macvlan"
    assert network["MacAddress"] == "aa:bb:cc:dd:ee:ff"


def test_pick_lan_network_none_for_bridge_only():
    networks = {"bridge": {"NetworkID": "net-bridge", "MacAddress": "02:aa:aa:aa:aa:aa"}}
    assert dockerdisc.pick_lan_network(networks, {"net-bridge": "bridge"}) is None


def test_pick_lan_network_empty_networks():
    assert dockerdisc.pick_lan_network({}, {}) is None
    assert dockerdisc.pick_lan_network(None, {}) is None


def test_pick_lan_network_multiple_lan_networks_ties_broken_alphabetically_by_name():
    """A container with two simultaneous macvlan/ipvlan networks must
    deterministically pick the alphabetically-first network *name* (spec
    §9's decided tie-break) - not whatever order the dict happens to
    iterate in."""
    networks = {
        "zzz-lan": {"NetworkID": "net-z", "MacAddress": "aa:aa:aa:aa:aa:zz"},
        "aaa-lan": {"NetworkID": "net-a", "MacAddress": "aa:aa:aa:aa:aa:aa"},
    }
    driver_by_id = {"net-z": "macvlan", "net-a": "ipvlan"}

    name, driver, network = dockerdisc.pick_lan_network(networks, driver_by_id)

    assert name == "aaa-lan"
    assert driver == "ipvlan"
    assert network["MacAddress"] == "aa:aa:aa:aa:aa:aa"


def test_pick_lan_network_missing_from_driver_lookup_is_treated_as_no_match():
    """If get_network_drivers() failed (Socket Proxy denied NETWORKS=1) the
    lookup is {} - every network must be treated as unknown/non-LAN, not
    crash on a missing key."""
    networks = {"lan": {"NetworkID": "net-lan", "MacAddress": "aa:bb:cc:dd:ee:ff"}}
    assert dockerdisc.pick_lan_network(networks, {}) is None


def test_first_network_driver_bridge_only():
    networks = {"bridge": {"NetworkID": "net-bridge"}}
    assert dockerdisc.first_network_driver(networks, {"net-bridge": "bridge"}) == "bridge"


def test_first_network_driver_empty():
    assert dockerdisc.first_network_driver({}, {}) is None


def test_first_network_driver_missing_from_driver_lookup():
    networks = {"lan": {"NetworkID": "net-lan"}}
    assert dockerdisc.first_network_driver(networks, {}) is None


# ---------------------------------------------------------------------------
# DockerHost.get_network_drivers()
# ---------------------------------------------------------------------------


def test_get_network_drivers_batches_into_one_request():
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    networks_resp = _resp([
        {"Id": "net-a", "Driver": "macvlan"},
        {"Id": "net-b", "Driver": "bridge"},
    ])
    with patch("requests.get", return_value=networks_resp) as mock_get:
        result = host.get_network_drivers(["net-a", "net-b", "net-a"])  # duplicate on purpose

    assert result == {"net-a": "macvlan", "net-b": "bridge"}
    assert mock_get.call_count == 1  # one batched call, not one per network


def test_get_network_drivers_empty_input_makes_no_request():
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch("requests.get") as mock_get:
        assert host.get_network_drivers([]) == {}
    mock_get.assert_not_called()


def test_get_network_drivers_denied_permission_returns_empty_dict():
    """Socket Proxy without NETWORKS=1 - request fails, callers must fall
    back to an empty lookup rather than crash."""
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("denied")):
        assert host.get_network_drivers(["net-a"]) == {}


# ---------------------------------------------------------------------------
# resolve_host_mac()
# ---------------------------------------------------------------------------


def test_resolve_host_mac_manual_mac_short_circuits_without_any_request():
    """A configured DOCKERDISC_HOST_MAC is used immediately, with zero
    Socket Proxy calls - it's a stable value, there's nothing to gain by
    spending an /info request "confirming" it every scheduled run. This
    is a deliberate design choice (not an oversight): auto-detection only
    ever runs when the field is left blank - filling it in trades away
    the self-healing "auto-detect keeps re-verifying it" behavior for the
    saved request, on purpose."""
    host = dockerdisc.DockerHost("http://proxy:2375", "11:22:33:44:55:66", 5)
    with patch.object(host, "get_info") as mock_get_info:
        assert dockerdisc.resolve_host_mac(host) == "11:22:33:44:55:66"
    mock_get_info.assert_not_called()


def test_resolve_host_mac_auto_detect_success():
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch.object(host, "get_info", return_value={"Name": "docker-host-1"}):
        with patch.object(dockerdisc, "get_temp_db_connection", return_value=_db_returning([("AA:BB:CC:DD:EE:FF",)])):
            assert dockerdisc.resolve_host_mac(host) == "aa:bb:cc:dd:ee:ff"


def test_resolve_host_mac_none_when_hostname_unmatched_and_no_manual_mac():
    """No manual fallback configured, so an unmatched hostname resolves to
    nothing - the "fall back to manual" path only exists when manual is
    actually set, and when it is, it short-circuits before this branch is
    ever reached (see the short-circuit test above)."""
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch.object(host, "get_info", return_value={"Name": "unknown-host"}):
        with patch.object(dockerdisc, "get_temp_db_connection", return_value=_db_returning([])):
            assert dockerdisc.resolve_host_mac(host) is None


def test_resolve_host_mac_none_when_info_unreachable_and_no_manual_mac():
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch.object(host, "get_info", return_value=None):
        assert dockerdisc.resolve_host_mac(host) is None


# ---------------------------------------------------------------------------
# lookup_device_mac()
# ---------------------------------------------------------------------------


def test_lookup_device_mac_found():
    with patch.object(dockerdisc, "get_temp_db_connection", return_value=_db_returning([(1,)])):
        assert dockerdisc.lookup_device_mac("aa:bb:cc:dd:ee:ff") is True


def test_lookup_device_mac_not_found():
    with patch.object(dockerdisc, "get_temp_db_connection", return_value=_db_returning([])):
        assert dockerdisc.lookup_device_mac("aa:bb:cc:dd:ee:ff") is False


# ---------------------------------------------------------------------------
# DockerHost._get() error handling (never raises)
# ---------------------------------------------------------------------------


def test_dockerhost_get_timeout_returns_none():
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch("requests.get", side_effect=requests.exceptions.Timeout("slow")):
        assert host.get_info() is None


def test_dockerhost_get_connection_error_returns_none():
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("no route")):
        assert host.get_containers() == []


def test_dockerhost_get_containers_success():
    host = dockerdisc.DockerHost("http://proxy:2375", "", 5)
    with patch("requests.get", return_value=_resp([{"Id": "abc123"}])):
        assert host.get_containers() == [{"Id": "abc123"}]


# ---------------------------------------------------------------------------
# process_host()
# ---------------------------------------------------------------------------


def _container(name, image, driver, mac=None, ip=None, project=None, service=None, extra_bridge=False):
    # NetworkID only - Driver is deliberately NOT set here, matching what a
    # real Socket Proxy actually returns (see module docstring); tests
    # supply Driver separately via a {NetworkID: Driver} lookup, same as
    # process_host() gets it from DockerHost.get_network_drivers().
    networks = {}
    if extra_bridge:
        networks["bridge"] = {"NetworkID": "net-bridge"}
    if driver:
        networks["lan"] = {"NetworkID": "net-lan", "MacAddress": mac, "IPAddress": ip}
    labels = {}
    if project:
        labels["com.docker.compose.project"] = project
    if service:
        labels["com.docker.compose.service"] = service
    return {
        "Id": "deadbeef0000",
        "Names": [f"/{name}"],
        "Image": image,
        "Labels": labels,
        "NetworkSettings": {"Networks": networks},
    }


def test_process_host_mixed_macvlan_and_bridge_containers():
    host_entry = {
        "DOCKERDISC_SOCKET_PROXY_URL": "http://proxy:2375",
        "DOCKERDISC_HOST_MAC": "aa:bb:cc:dd:ee:ff",
    }
    containers = [
        _container("pihole", "pihole/pihole:latest", "macvlan", mac="aa:aa:aa:aa:aa:01", ip="192.168.1.50", project="dns", service="pihole"),
        _container("redis", "redis:7", None, extra_bridge=True),
    ]
    plugin_objects = MagicMock()
    plugin_objects.add_object = MagicMock()

    host = dockerdisc.DockerHost(host_entry["DOCKERDISC_SOCKET_PROXY_URL"], host_entry["DOCKERDISC_HOST_MAC"], 5)
    with patch.object(dockerdisc, "DockerHost", return_value=host):
        with patch.object(host, "get_info", return_value=None):  # unused - manual_mac short-circuits before this would ever be called
            with patch.object(host, "get_containers", return_value=containers):
                with patch.object(host, "get_network_drivers", return_value={"net-lan": "macvlan", "net-bridge": "bridge"}) as mock_drivers:
                    with patch.object(dockerdisc, "get_temp_db_connection", return_value=_db_returning([(1,)])):
                        added = dockerdisc.process_host(host_entry, 5, plugin_objects)

    # one batched call for both containers' networks, not two
    mock_drivers.assert_called_once()
    assert sorted(mock_drivers.call_args.args[0]) == ["net-bridge", "net-lan"]

    assert added == 2
    assert plugin_objects.add_object.call_count == 2

    pihole_call = plugin_objects.add_object.call_args_list[0].kwargs
    assert pihole_call["primaryId"] == "aa:bb:cc:dd:ee:ff"  # host MAC, not the container's
    assert pihole_call["foreignKey"] == "aa:bb:cc:dd:ee:ff"
    assert pihole_call["secondaryId"] == "pihole"
    assert pihole_call["watched2"] == "dns / pihole"
    assert pihole_call["watched3"] == "macvlan"
    assert pihole_call["watched4"] == "aa:aa:aa:aa:aa:01"
    assert pihole_call["extra"] == "192.168.1.50"

    redis_call = plugin_objects.add_object.call_args_list[1].kwargs
    assert redis_call["primaryId"] == "aa:bb:cc:dd:ee:ff"  # same host, not skipped for lacking a LAN MAC
    assert redis_call["watched3"] == "bridge"
    assert redis_call["watched4"] == "null"  # no LAN-visible MAC for a bridge-only container
    assert redis_call["extra"] == "null"


def test_process_host_skips_unconfigured_entry_without_any_request():
    plugin_objects = MagicMock()
    with patch("requests.get") as mock_get:
        added = dockerdisc.process_host({"DOCKERDISC_SOCKET_PROXY_URL": "", "DOCKERDISC_HOST_MAC": ""}, 5, plugin_objects)
    assert added == 0
    mock_get.assert_not_called()
    plugin_objects.add_object.assert_not_called()


def test_process_host_skips_when_host_mac_unresolved():
    host_entry = {"DOCKERDISC_SOCKET_PROXY_URL": "http://proxy:2375", "DOCKERDISC_HOST_MAC": ""}
    plugin_objects = MagicMock()
    with patch.object(dockerdisc.DockerHost, "get_info", return_value=None):
        added = dockerdisc.process_host(host_entry, 5, plugin_objects)
    assert added == 0
    plugin_objects.add_object.assert_not_called()


def test_process_host_skips_when_host_not_a_known_device_without_listing_containers():
    host_entry = {"DOCKERDISC_SOCKET_PROXY_URL": "http://proxy:2375", "DOCKERDISC_HOST_MAC": "aa:bb:cc:dd:ee:ff"}
    plugin_objects = MagicMock()
    with patch.object(dockerdisc.DockerHost, "get_info", return_value=None):
        with patch.object(dockerdisc, "get_temp_db_connection", return_value=_db_returning([])):  # not found
            with patch.object(dockerdisc.DockerHost, "get_containers") as mock_get_containers:
                added = dockerdisc.process_host(host_entry, 5, plugin_objects)
    assert added == 0
    mock_get_containers.assert_not_called()
    plugin_objects.add_object.assert_not_called()


# ---------------------------------------------------------------------------
# _encode_host_entry() / decode_settings_base64 round trip (sanity check
# that the test helper matches what NetAlertX actually sends)
# ---------------------------------------------------------------------------


def test_encode_decode_host_entry_round_trip():
    encoded = _encode_host_entry("http://proxy:2375", "aa:bb:cc:dd:ee:ff")
    decoded = _decode_settings_base64(encoded)
    assert decoded == {
        "DOCKERDISC_SOCKET_PROXY_URL": "http://proxy:2375",
        "DOCKERDISC_HOST_MAC": "aa:bb:cc:dd:ee:ff",
    }
