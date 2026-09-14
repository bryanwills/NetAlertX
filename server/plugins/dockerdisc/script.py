#!/usr/bin/env python
"""NetAlertX plugin: DOCKERDISC - Docker discovery (enrichment, not import)

Does NOT discover devices. NetAlertX's own ARP/Nmap scanners remain the
sole source of device presence. Instead, for each configured Docker host
this plugin lists that host's containers under the *host's own* Device
Details -> Plugins -> DOCKERDISC tab.

Design ("Device = Docker host -> List of containers", per maintainer
jokob-sk, see ../../../PLUGIN_DOCKERDISC_SPEC.md for the full history):

  - objectPrimaryId / foreignKey is always the Docker HOST's MAC - never a
    container's own MAC. Every plugin object (one per container) attaches
    to the host device, which must already exist in NetAlertX (found the
    normal way, via ARP/Nmap). This plugin never creates a device row, for
    either a host or a container.
  - Because matching targets the host (persistent LAN identity), not the
    container, EVERY container is listed - bridge/overlay ones included -
    not only macvlan/ipvlan ones. A container only gets its own MAC/IP
    shown (watched4/extra) when it has a macvlan/ipvlan network; otherwise
    those fields are "null".
  - One `hosts` entry = one Docker host: a read-only Docker Socket Proxy
    URL, plus a manual MAC fallback for when auto-detection (via the
    proxy's own /info endpoint) doesn't resolve to a known device. Never
    connects to /var/run/docker.sock directly.

Verified 2026-09-08 against a real Docker Engine + docker-socket-proxy
(see PLUGIN_DOCKERDISC_SPEC.md §9 for the open questions this closed):
`GET /containers/json`'s `NetworkSettings.Networks.<name>` does NOT carry
a `Driver` field inline (only NetworkID/Gateway/IPAddress/MacAddress/...) -
the driver has to come from a separate `GET /networks` call, filtered by
the unique NetworkIDs seen across a host's containers in one batched
request (cacheable per run, as originally anticipated). This needs the
Socket Proxy's NETWORKS=1 permission in addition to CONTAINERS=1/INFO=1.

Structural references: server/plugins/internet_speedtest/config.json
(plugin_type "other", no mapped_to_column - this never writes into
Devices/CurrentScan) and server/plugins/vendor_update/script.py
("resolve for a device that must already exist, skip - never create -
otherwise" logic, applied here to the host instead of the container).
"""

import json
import os
import sys
from urllib.parse import urlencode

import requests

INSTALL_PATH = os.getenv('NETALERTX_APP', '/app')
sys.path.extend([f"{INSTALL_PATH}/server/plugins", f"{INSTALL_PATH}/server"])

from plugin_helper import (  # noqa: E402
    Plugin_Objects,
    handleEmpty,
    normalize_mac,
    decode_settings_base64,
)
from logger import mylog, Logger  # noqa: E402
from helper import get_setting_value  # noqa: E402
from const import logPath  # noqa: E402
from database import get_temp_db_connection  # noqa: E402
import conf  # noqa: E402
from pytz import timezone  # noqa: E402

conf.tz = timezone(get_setting_value('TIMEZONE'))
Logger(get_setting_value('LOG_LEVEL'))

pluginName = 'DOCKERDISC'

LOG_PATH = logPath + '/plugins'
RESULT_FILE = os.path.join(LOG_PATH, f'last_result.{pluginName}.log')

REQUEST_TIMEOUT_DEFAULT = 30

# Docker network drivers with their own real LAN-visible MAC/IP - the only
# ones that can populate watched4/extra (container_mac/container_ip). Every
# other driver (bridge, overlay, host, none, ...) still gets its container
# listed, just without those two fields.
LAN_VISIBLE_DRIVERS = ('macvlan', 'ipvlan')


class DockerHost:
    """One configured `hosts` entry: a Docker Socket Proxy endpoint plus
    the manual host-MAC fallback for it. Does not connect on construction -
    call get_info()/get_containers() to actually talk to the proxy. Never
    raises - a failed host is logged and skipped, not fatal to the run."""

    def __init__(self, proxy_url, manual_mac, run_timeout):
        self.proxy_url = (proxy_url or '').rstrip('/')
        self.manual_mac = normalize_mac(manual_mac) if manual_mac else None
        self.run_timeout = run_timeout

    @property
    def configured(self):
        return bool(self.proxy_url)

    def _get(self, path):
        """GET against this host's Socket Proxy. Returns the parsed JSON
        body, or None (logging why) on any failure."""
        try:
            resp = requests.get(
                self.proxy_url + path,
                timeout=self.run_timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            mylog('none', [f'[{pluginName}] {self.proxy_url}: request to {path} timed out. Try increasing the run timeout.'])
            return None
        except requests.exceptions.ConnectionError:
            mylog('none', [f'[{pluginName}] {self.proxy_url}: connection error on {path}. Check the Socket Proxy URL and that it is reachable.'])
            return None
        except Exception as e:
            mylog('none', [f'[{pluginName}] {self.proxy_url}: unexpected error on {path}: {e}'])
            return None

    def get_info(self):
        """Docker Engine API /info - used only for host-MAC auto-detection
        (the daemon's `Name`, i.e. hostname). Requires the Socket Proxy's
        INFO=1 permission; returns None if that's not granted or /info
        otherwise fails, in which case callers fall back to manual_mac."""
        return self._get('/info')

    def get_containers(self):
        """Docker Engine API /containers/json (running containers only,
        matching the default `all=false`) - includes NetworkSettings and
        Labels, which is all this plugin needs. Requires CONTAINERS=1."""
        return self._get('/containers/json') or []

    def get_network_drivers(self, network_ids):
        """{NetworkID: Driver} for the given network IDs, in one batched
        `GET /networks?filters=...` call - NetworkSettings.Networks on a
        container does NOT carry Driver inline (confirmed against a real
        Socket Proxy 2026-09-08), so this is the only way to get it.
        Requires NETWORKS=1. Returns {} (not per-container failure) if the
        call fails - callers fall back to an empty/unknown driver rather
        than aborting the whole host."""
        network_ids = sorted(set(network_ids))
        if not network_ids:
            return {}

        query = urlencode({'filters': json.dumps({'id': network_ids})})
        networks = self._get(f'/networks?{query}')
        if networks is None:
            mylog('verbose', [f'[{pluginName}] {self.proxy_url}: could not read /networks (needs the Socket Proxy NETWORKS=1 permission) - network driver will show as empty.'])
            return {}

        return {n['Id']: n.get('Driver') for n in networks if 'Id' in n}


def resolve_host_mac(host):
    """Manually configured DOCKERDISC_HOST_MAC wins immediately, with no
    Socket Proxy call at all - a MAC address is stable and doesn't need
    runtime "confirmation" via hostname matching, so there's nothing to
    gain from spending an /info request on it every single scheduled run.
    Otherwise auto-detects via Socket Proxy /info -> Devices.devName
    match. Returns a normalized MAC string, or None if neither resolves
    to anything."""

    if host.manual_mac:
        return host.manual_mac

    info = host.get_info()
    hostname = (info or {}).get('Name')

    if hostname:
        conn = get_temp_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT devMac FROM Devices WHERE devName = ? COLLATE NOCASE LIMIT 1",
            (hostname.lstrip('/'),),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            mylog('verbose', [f'[{pluginName}] {host.proxy_url}: auto-detected host MAC via hostname "{hostname}".'])
            return normalize_mac(row[0])

        mylog(
            'verbose',
            [f'[{pluginName}] {host.proxy_url}: /info hostname "{hostname}" has no matching Devices.devName - '
             'falling back to the manually configured host MAC, if any.'],
        )
    else:
        mylog(
            'verbose',
            [f'[{pluginName}] {host.proxy_url}: could not read hostname via /info (needs the Socket Proxy '
             'INFO=1 permission) - falling back to the manually configured host MAC, if any.'],
        )

    return host.manual_mac


def lookup_device_mac(mac):
    """True if `mac` already exists as a Devices row - this plugin never
    creates the host device, same rule vendor_update applies to the
    devices it enriches. COLLATE NOCASE is explicit here (not just relied
    on from the Devices.devMac column definition) so this still matches
    correctly even if that ever changes - normalize_mac() lowercases what
    we search for, but what's actually stored can come from other
    discovery methods and isn't guaranteed to be lowercase."""
    conn = get_temp_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Devices WHERE devMac = ? COLLATE NOCASE LIMIT 1", (mac,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def pick_lan_network(networks, driver_by_id):
    """Given a container's NetworkSettings.Networks dict and a
    {NetworkID: Driver} lookup (from DockerHost.get_network_drivers - the
    per-network Driver isn't inline on `networks`, see module docstring),
    return the (name, driver, network) for its macvlan/ipvlan network if it
    has one, else None.

    If a container somehow has more than one macvlan/ipvlan network at
    once, the one with the alphabetically first network *name* wins - a
    deliberate, deterministic tie-break (spec §9), not "whatever order the
    Socket Proxy's JSON happened to list them in" (dict iteration order,
    which isn't a documented/guaranteed ordering from the Docker API and
    could in principle vary between runs)."""
    lan_networks = sorted(
        ((name, network) for name, network in (networks or {}).items()
         if driver_by_id.get(network.get('NetworkID')) in LAN_VISIBLE_DRIVERS),
        key=lambda item: item[0],
    )
    if not lan_networks:
        return None
    name, network = lan_networks[0]
    return name, driver_by_id[network['NetworkID']], network


def first_network_driver(networks, driver_by_id):
    """Best-effort driver name to show when the container has no
    macvlan/ipvlan network - whatever its first network reports."""
    for network in (networks or {}).values():
        driver = driver_by_id.get(network.get('NetworkID'))
        if driver:
            return driver
    return None


def process_host(host_entry, run_timeout, plugin_objects):
    host = DockerHost(
        proxy_url=host_entry.get('DOCKERDISC_SOCKET_PROXY_URL'),
        manual_mac=host_entry.get('DOCKERDISC_HOST_MAC'),
        run_timeout=run_timeout,
    )

    if not host.configured:
        mylog('none', [f'[{pluginName}] Skipping a configured host entry with no Socket Proxy URL.'])
        return 0

    host_mac = resolve_host_mac(host)
    if not host_mac:
        mylog('none', [f'[{pluginName}] {host.proxy_url}: no host MAC (auto-detect failed and no manual fallback set) - skipping.'])
        return 0

    if not lookup_device_mac(host_mac):
        mylog('none', [f'[{pluginName}] {host.proxy_url}: host MAC {host_mac} is not a known device (never created by this plugin) - skipping.'])
        return 0

    containers = host.get_containers()
    mylog('verbose', [f'[{pluginName}] {host.proxy_url} ({host_mac}): {len(containers)} container(s) found.'])

    # One batched /networks call for every unique NetworkID referenced by
    # this host's containers, instead of one call per container/network.
    network_ids = (
        network.get('NetworkID')
        for container in containers
        for network in ((container.get('NetworkSettings') or {}).get('Networks') or {}).values()
    )
    driver_by_id = host.get_network_drivers(n for n in network_ids if n)

    added = 0
    for container in containers:
        networks = (container.get('NetworkSettings') or {}).get('Networks') or {}
        lan_net = pick_lan_network(networks, driver_by_id)

        if lan_net:
            _, network_driver, network = lan_net
            container_mac = network.get('MacAddress') or ''
            container_ip = network.get('IPAddress') or ''
        else:
            network_driver = first_network_driver(networks, driver_by_id) or ''
            container_mac = ''
            container_ip = ''

        labels = container.get('Labels') or {}
        compose_project = labels.get('com.docker.compose.project')
        compose_service = labels.get('com.docker.compose.service')
        compose = ' / '.join(p for p in (compose_project, compose_service) if p) or None

        names = container.get('Names') or []
        container_name = names[0].lstrip('/') if names else container.get('Id', '')[:12]

        plugin_objects.add_object(
            primaryId=host_mac,
            secondaryId=handleEmpty(container_name),
            watched1=handleEmpty(container.get('Image')),
            watched2=handleEmpty(compose),
            watched3=handleEmpty(network_driver),
            watched4=handleEmpty(container_mac),
            extra=handleEmpty(container_ip),
            foreignKey=host_mac,
        )
        added += 1

    return added


def main():
    mylog('verbose', [f'[{pluginName}] In script'])

    host_configs = get_setting_value('DOCKERDISC_hosts') or []
    run_timeout = get_setting_value('DOCKERDISC_RUN_TIMEOUT') or REQUEST_TIMEOUT_DEFAULT

    mylog('verbose', [f'[{pluginName}] number of configured hosts: {len(host_configs)}'])

    plugin_objects = Plugin_Objects(RESULT_FILE)

    total_added = 0
    for host_config in host_configs:
        host_entry = decode_settings_base64(host_config)
        total_added += process_host(host_entry, run_timeout, plugin_objects)

    plugin_objects.write_result_file()

    mylog('verbose', [f'[{pluginName}] Update complete - {total_added} container(s) reported across {len(host_configs)} host(s).'])

    return 0


if __name__ == '__main__':
    main()
