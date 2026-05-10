## Overview

A plugin allowing for importing devices from the Kea DHCP API.  
https://www.isc.org/kea/

And specifically:
https://kea.readthedocs.io/en/kea-2.6.3/api.html#lease4-get-all


### Usage

To enable the API, first you want to add something like this to your main kea configuration (this is for debian 13):

```json
    "control-socket": {
        "socket-type": "unix",
        "socket-name": "/run/kea/kea4-ctrl-socket"
    },
    
    "hooks-libraries": [
        {
            "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_lease_cmds.so"
        }
    ],
```

    
And you need to install kea-ctrl-agent, with a config that looks something like this:
    
```json
{
"Control-agent": {
    "http-host": "127.0.0.1",
    "http-port": 8000,

    "authentication": {
        "type": "basic",
        "realm": "Kea Control Agent",
        "directory": "/etc/kea",
        "clients": [
            {
                "user": "kea-api",
                "password-file": "kea-api-password"
            }
        ]
    },
    "control-sockets": {
        "dhcp4": {
            "socket-type": "unix",
            "socket-name": "/run/kea/kea4-ctrl-socket"
        }
    },
    "loggers": [
    {
        "name": "kea-ctrl-agent",
        "output-options": [
            {
                "output": "stdout",
                "pattern": "%-5p %m\n"
            }
        ],
        "severity": "INFO",
        "debuglevel": 0
    }
  ]
}
}
```

You will need to configure the plugin with the URL to the API, and the username and password configured above (from kea-api-password file in the example)
