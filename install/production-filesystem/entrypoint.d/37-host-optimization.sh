#!/bin/sh

# 37-host-optimization.sh: Apply and validate network optimizations (ARP flux fix)
#
# This script improves detection accuracy by ensuring proper ARP behavior.
# It attempts to apply sysctl settings and warns if not possible.

# --- Color Codes ---
RED=$(printf '\033[1;31m')
YELLOW=$(printf '\033[1;33m')
RESET=$(printf '\033[0m')

# --- Skip flag ---
if [ -n "${SKIP_OPTIMIZATIONS:-}" ]; then
    exit 0
fi

# --- Helpers ---

get_sysctl() {
    sysctl -n "$1" 2>/dev/null || echo "unknown"
}

set_sysctl_if_needed() {
    key="$1"
    expected="$2"

    current="$(get_sysctl "$key")"

    # Already correct
    if [ "$current" = "$expected" ]; then
        return 0
    fi

    # Try to apply
    if sysctl -w "$key=$expected" >/dev/null 2>&1; then
        return 0
    fi

    # Failed
    return 1
}

# --- Apply Settings (best effort) ---

failed=0

set_sysctl_if_needed net.ipv4.conf.all.arp_ignore 1 || failed=1
set_sysctl_if_needed net.ipv4.conf.all.arp_announce 2 || failed=1
set_sysctl_if_needed net.ipv4.conf.default.arp_ignore 1 || failed=1
set_sysctl_if_needed net.ipv4.conf.default.arp_announce 2 || failed=1

# --- Validate final state ---

all_ignore="$(get_sysctl net.ipv4.conf.all.arp_ignore)"
all_announce="$(get_sysctl net.ipv4.conf.all.arp_announce)"

# --- Warning Output ---

if [ "$all_ignore" != "1" ] || [ "$all_announce" != "2" ]; then
    >&2 printf "%s" "${YELLOW}"
    >&2 cat <<EOF
══════════════════════════════════════════════════════════════════════════════
⚠️  ATTENTION: ARP flux protection not enabled.

    NetAlertX relies on ARP for device detection. Your system currently allows
    ARP replies from incorrect interfaces (ARP flux), which may result in:

      • False devices being detected
      • IP/MAC mismatches
      • Flapping device states
      • Incorrect network topology

    This is common when running in Docker or multi-interface environments.

    ──────────────────────────────────────────────────────────────────────────
    Recommended fix (Docker Compose):

    sysctls:
      net.ipv4.conf.all.arp_ignore: 1
      net.ipv4.conf.all.arp_announce: 2

    ──────────────────────────────────────────────────────────────────────────
    Alternatively, apply on the host:

      net.ipv4.conf.all.arp_ignore=1
      net.ipv4.conf.all.arp_announce=2

    Detection accuracy may be reduced until this is configured.
══════════════════════════════════════════════════════════════════════════════
EOF
    >&2 printf "%s" "${RESET}"
fi
