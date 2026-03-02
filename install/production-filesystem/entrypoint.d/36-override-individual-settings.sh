#!/bin/bash
# 36-override-individual-settings.sh - Applies environment variable overrides to app.conf

set -eu

# Ensure config exists
if [ ! -f "${NETALERTX_CONFIG}/app.conf" ]; then
    echo "[ENV] No config file found at ${NETALERTX_CONFIG}/app.conf — skipping overrides"
    exit 0
fi

if [ -n "${LOADED_PLUGINS:-}" ]; then
    echo "[ENV] Applying LOADED_PLUGINS override"
    value=$(printf '%s' "$LOADED_PLUGINS" | tr -d '\n\r')
    escaped=$(printf '%s\n' "$value" | sed 's/[\/&]/\\&/g')

    if grep -q '^LOADED_PLUGINS=' "${NETALERTX_CONFIG}/app.conf"; then
        sed -i "s|^LOADED_PLUGINS=.*|LOADED_PLUGINS=${escaped}|" "${NETALERTX_CONFIG}/app.conf"
    else
        echo "LOADED_PLUGINS=${value}" >> "${NETALERTX_CONFIG}/app.conf"
    fi
fi
