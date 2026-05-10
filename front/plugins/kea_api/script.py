#!/usr/bin/env python3
import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../server'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../plugins'))

from plugin_helper import Plugin_Objects, mylog, handleEmpty, is_mac
from helper import get_setting_value
from const import logPath

pluginName = "KEALSS"
LOG_PATH = logPath + "/plugins"
LOG_FILE = os.path.join(LOG_PATH, f'script.{pluginName}.log')
RESULT_FILE = os.path.join(LOG_PATH, f'last_result.{pluginName}.log')

plugin_objects = Plugin_Objects(RESULT_FILE)


def main():
    try:
        url = get_setting_value(f'{pluginName}_URL')
        user = get_setting_value(f'{pluginName}_USER')
        password = get_setting_value(f'{pluginName}_PASS')

        mylog('verbose', [f'[{pluginName}] Querying Kea API at {url}'])

        payload = {'command': 'lease4-get-all', 'service': ['dhcp4']}

        response = requests.post(url, json=payload, auth=(user, password), timeout=10)
        response.raise_for_status()
        data = response.json()

        count = 0
        for entry in data:
            # Result: 0 (success), 1 (error), or 3 (empty).
            if entry.get("result") == 0:
                leases = entry["arguments"].get("leases", [])
                for l in leases:
                    mac = l['hw-address']                    
                    state = l['state']
                    if is_mac(mac):
                        plugin_objects.add_object(
                            primaryId   = mac,
                            secondaryId = l['ip-address'],
                            # Active or not, similar to watched 1 of DHCPLSS plugin
                            watched1    = state == 0, 
                            watched2    = l['hostname'],
                            watched3    = None,
                            # Default (or assigned) (0), declined (1), expired-reclaimed (2), released (3), and registered (4)).
                            watched4    = state,
                            extra       = None,
                            foreignKey  = mac
                        )
                        count += 1
            elif entry.get("result") == 1:
                mylog('none', [f'[{pluginName}] ⚠ ERROR: Kea API indicated error'])

        plugin_objects.write_result_file()

        mylog('verbose', [f'[{pluginName}] Successfully imported {count} devices reported by Kea API'])

    except Exception as e:
        mylog('none', [f'[{pluginName}] ⚠ ERROR: {str(e)}'])



if __name__ == '__main__':
    main()
