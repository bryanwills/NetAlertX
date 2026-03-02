# ARP Flux Sysctls Not Set

## Issue Description

NetAlertX detected that ARP flux protection sysctls are not set as expected:

- `net.ipv4.conf.all.arp_ignore=1`
- `net.ipv4.conf.all.arp_announce=2`

## Security Ramifications

This is not a direct container breakout risk, but detection quality can degrade:

- Incorrect IP/MAC associations
- Device state flapping
- Unreliable topology or presence data

## Why You're Seeing This Issue

The running environment does not provide the expected kernel sysctl values. This is common in Docker setups where sysctls were not explicitly configured.

## How to Correct the Issue

Set these sysctls at container runtime.

- In `docker-compose.yml` (preferred):
  ```yaml
  services:
    netalertx:
      sysctls:
        net.ipv4.conf.all.arp_ignore: 1
        net.ipv4.conf.all.arp_announce: 2
  ```

- For `docker run`:
  ```bash
  docker run \
    --sysctl net.ipv4.conf.all.arp_ignore=1 \
    --sysctl net.ipv4.conf.all.arp_announce=2 \
    jokob-sk/netalertx:latest
  ```

## Additional Resources

For broader Docker Compose guidance, see:

- [DOCKER_COMPOSE.md](https://docs.netalertx.com/DOCKER_COMPOSE)
