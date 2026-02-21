#!/bin/bash
# 36-override-loaded-plugins.sh - Applies environment variable overrides to app.conf

set -eu

# Ensure config exists
if [ ! -f "${NETALERTX_CONFIG}/app.conf" ]; then
    echo "[ENV] No config file found at ${NETALERTX_CONFIG}/app.conf — skipping overrides"
    exit 0
fi

# Helper: set or append config key safely
set_config_value() {
    _key="$1"
    _value="$2"

    # Remove newlines just in case
    _value=$(printf '%s' "$_value" | tr -d '\n\r')

    # Escape sed-sensitive chars
    _escaped=$(printf '%s\n' "$_value" | sed 's/[\/&]/\\&/g')

    if grep -q "^${_key}=" "${NETALERTX_CONFIG}/app.conf"; then
        sed -i "s|^${_key}=.*|${_key}=${_escaped}|" "${NETALERTX_CONFIG}/app.conf"
    else
        echo "${_key}=${_value}" >> "${NETALERTX_CONFIG}/app.conf"
    fi
}

# ------------------------------------------------------------
# LOADED_PLUGINS override
# ------------------------------------------------------------
if [ -n "${LOADED_PLUGINS:-}" ]; then
    echo "[ENV] Applying LOADED_PLUGINS override"
    set_config_value "LOADED_PLUGINS" "$LOADED_PLUGINS"
fi
