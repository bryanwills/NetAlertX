#!/usr/bin/env python

import os
import sys
import json
from pytz import timezone
from unifi_sm_api.api import SiteManagerAPI

# Define the installation path and extend the system path for plugin imports
INSTALL_PATH = os.getenv('NETALERTX_APP', '/app')
sys.path.extend([f"{INSTALL_PATH}/server/plugins", f"{INSTALL_PATH}/server"])

from plugin_helper import Plugin_Objects, decode_settings_base64  # noqa: E402 [flake8 lint suppression]
from logger import mylog, Logger  # noqa: E402 [flake8 lint suppression]
from const import logPath  # noqa: E402 [flake8 lint suppression]
from helper import get_setting_value  # noqa: E402 [flake8 lint suppression]
import conf  # noqa: E402 [flake8 lint suppression]

# Make sure the TIMEZONE for logging is correct
conf.tz = timezone(get_setting_value('TIMEZONE'))

# Make sure log level is initialized correctly
Logger(get_setting_value('LOG_LEVEL'))

pluginName = 'UNIFIAPI'

# Define the current path and log file paths
LOG_PATH = logPath + '/plugins'
LOG_FILE = os.path.join(LOG_PATH, f'script.{pluginName}.log')
RESULT_FILE = os.path.join(LOG_PATH, f'last_result.{pluginName}.log')

# Initialize the Plugin obj output file
plugin_objects = Plugin_Objects(RESULT_FILE)


def main():
    mylog('verbose', [f'[{pluginName}] In script'])

    # Retrieve configuration settings
    unifi_sites_configs = get_setting_value('UNIFIAPI_sites')

    mylog('verbose', [f'[{pluginName}] number of unifi_sites_configs: {len(unifi_sites_configs)}'])

    for site_config in unifi_sites_configs:

        siteDict = decode_settings_base64(site_config)

        mylog('verbose', [f'[{pluginName}] siteDict: {json.dumps(siteDict)}'])
        mylog('none', [f'[{pluginName}] Connecting to: {siteDict["UNIFIAPI_site_name"]}'])

        api = SiteManagerAPI(
            api_key=siteDict["UNIFIAPI_api_key"],
            version=siteDict["UNIFIAPI_api_version"],
            base_url=siteDict["UNIFIAPI_base_url"],
            verify_ssl=siteDict["UNIFIAPI_verify_ssl"]
        )

        sites_resp = api.get_sites()
        sites = sites_resp.get("data", [])

        for site in sites:

            # retrieve data
            device_data = get_device_data(site, api)

            #  Process the data into native application tables
            if len(device_data) > 0:

                # insert devices into the lats_result.log
                for device in device_data:
                    plugin_objects.add_object(
                        primaryId   = device['dev_mac'],                    # mac
                        secondaryId = device['dev_ip'],                     # IP
                        watched1    = device['dev_name'],                   # name
                        watched2    = device['dev_type'],                   # device_type (AP/Switch etc)
                        watched3    = device['dev_connected'],              # connectedAt or empty
                        watched4    = device['dev_parent_mac'],             # parent_mac or "internet"
                        extra       = '',
                        foreignKey  = device['dev_mac'],
                        helpVal1    = siteDict["UNIFIAPI_site_name"],       # devSite
                        helpVal2    = device.get('dev_vlan_id', 'null'),
                        helpVal3    = device.get('dev_vlan_name', 'null'),  # devVlan
                        helpVal4    = device.get('dev_wan_name', 'null')
                    )

                mylog('verbose', [f'[{pluginName}] New entries: "{len(device_data)}"'])

        # log result
        plugin_objects.write_result_file()

    return 0


#  retrieve data
def get_device_data(site, api):
    device_data = []

    mylog('verbose', [f'[{pluginName}] Site: {site} '])
    site_id = site["id"]
    site_name = site.get("name", "Unnamed Site")

    mylog('verbose', [f'[{pluginName}] Site: {site_name} ({site_id})'])

    # --- Networks ---
    networks_resp = api.get_networks(site_id)
    networks = networks_resp.get("data", [])

    mylog(
        'trace',
        [f'[{pluginName}] Site: {site_name} networks: '
         f'{json.dumps(networks_resp, indent=2)}']
    )

    # Network/VLAN lookup by UniFi network ID
    network_lookup = {
        network.get("id"): network
        for network in networks
        if network.get("id")
    }

    # VLAN lookup by VLAN ID
    vlan_lookup = {
        str(network.get("vlanId")): network
        for network in networks
        if network.get("vlanId") is not None
    }

    # --- WiFi broadcasts ---
    wifi_broadcasts_resp = api.get_wifi_broadcasts(site_id)

    # --- WANs ---
    wans_resp = api.get_wans(site_id)
    wans = wans_resp.get("data", [])

    mylog(
        'trace',
        [f'[{pluginName}] Site: {site_name} WANs: '
         f'{json.dumps(wans_resp, indent=2)}']
    )

    # WAN lookup by UniFi WAN ID
    wan_lookup = {
        wan.get("id"): wan
        for wan in wans
        if wan.get("id")
    }

    # --- Devices ---
    unifi_devices_resp = api.get_unifi_devices(site_id)
    unifi_devices = unifi_devices_resp.get("data", [])
    mylog('trace', [f'[{pluginName}] Site: {site_name} unifi devices: {json.dumps(unifi_devices_resp, indent=2)}'])

    # --- Clients ---
    clients_resp = api.get_clients(site_id)
    clients = clients_resp.get("data", [])
    mylog('trace', [f'[{pluginName}] Site: {site_name} clients: {json.dumps(clients_resp, indent=2)}'])

    # Build a lookup for devices by their 'id' to find parent MAC easily
    device_id_to_mac = {}
    for dev in unifi_devices:
        if "id" not in dev:
            mylog("verbose", [f"[{pluginName}] Skipping device without 'id': {json.dumps(dev)}"])
            continue
        device_id_to_mac[dev["id"]] = dev.get("macAddress", "")

    # Helper to resolve uplinkDeviceId to parent MAC, or "internet" if no uplink
    def resolve_parent_mac(uplink_id):
        if not uplink_id:
            return "internet"
        return device_id_to_mac.get(uplink_id, "Unknown")

    # Process Unifi devices
    for device in unifi_devices:
        dev_mac  = device.get('macAddress', '')
        dev_ip   = device.get('ipAddress', '')
        dev_name = device.get('name', '')
        
        features = device.get('features', [])
        if 'accessPoint' in features:
            device_type = 'AP'
        elif 'switching' in features:
            device_type = 'Switch'
        else:
            device_type = 'Unknown'

        dev_type = device_type
        dev_connected = ''

        uplinkDeviceId = device.get('uplinkDeviceId', '')
        dev_parent_mac = resolve_parent_mac(uplinkDeviceId)

        # Resolve VLAN/network for devices if available
        vlan_id = device.get('vlanId')
        vlan_name = ''
        if not vlan_id and 'networkId' in device:
            network = network_lookup.get(device.get('networkId'), {})
            vlan_id = network.get("vlanId")
            vlan_name = network.get("name", "")

        # Default management network fallback for gateway/devices
        if not vlan_id and network_lookup:
            # Fallback to the first network (e.g., LAN) if none specified
            default_net = list(network_lookup.values())[0]
            vlan_id = default_net.get("vlanId")
            vlan_name = default_net.get("name", "")

        wan_name = wans[0].get("name", "") if wans else ""

        device_data.append({
            "dev_mac": dev_mac,
            "dev_ip": dev_ip,
            "dev_name": dev_name,
            "dev_type": dev_type,
            "dev_connected": dev_connected,
            "dev_parent_mac": dev_parent_mac,
            "dev_vlan_id": str(vlan_id) if vlan_id is not None else "null",
            "dev_vlan_name": vlan_name or "null",
            "dev_wan_name": wan_name or "null"
        })

    # Process Clients (child devices connected to APs or switches)
    for client in clients:
        dev_mac = client.get('macAddress', '')
        dev_ip = client.get('ipAddress', '')
        dev_name = client.get('name', '')
        dev_type = ''
        dev_connected = client.get('connectedAt', '')

        uplinkDeviceId = client.get('uplinkDeviceId', '')
        dev_parent_mac = resolve_parent_mac(uplinkDeviceId)

        # Defaults
        vlan_id = None
        vlan_name = ''
        wan_name = ''

        # Retrieve client details
        client_id = client.get("id")
        client_details = {}
        if client_id:
            client_details = api.get_client_details(site_id, client_id)

        # Resolve VLAN/network from client details or base client payload
        client_network = client_details.get("network", {})
        network_id = client_network.get("id") or client.get("network_id")

        if network_id:
            network = network_lookup.get(network_id, {})
            vlan_id = network.get("vlanId")
            vlan_name = network.get("name", "")
        
        # Fallback if network name is directly in client payload
        if not vlan_name:
            vlan_name = client.get("last_connection_network_name", "")

        # Map WAN name
        wan_id = client_details.get("wan_id") or client.get("wan_id")
        if wan_id and wan_id in wan_lookup:
            wan_name = wan_lookup[wan_id].get("name", "")
        else:
            wan_name = wans[0].get("name", "") if wans else ""

        device_data.append({
            "dev_mac": dev_mac,
            "dev_ip": dev_ip,
            "dev_name": dev_name,
            "dev_type": dev_type,
            "dev_connected": dev_connected,
            "dev_parent_mac": dev_parent_mac,
            "dev_vlan_id": str(vlan_id) if vlan_id is not None else "1",  # Fallback to 1 if default LAN
            "dev_vlan_name": vlan_name or "LAN",
            "dev_wan_name": wan_name or "null"
        })

    return device_data

if __name__ == '__main__':
    main()
