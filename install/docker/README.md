# 🐳 Docker Compose Installation

This folder provides standard Docker Compose configurations to get **NetAlertX** up and running quickly. This method is ideal for users on **Proxmox**, **TrueNAS Scale**, **Portainer**, or standard Linux hosts who prefer a simple, declarative setup.

## 🚀 Getting Started

### 1. Choose your flavor

*   **Stable (Recommended):** Use `docker-compose.yml`. This tracks the latest stable release.
*   **Development:** Use `docker-compose.dev.yml`. This tracks the `dev` branch and contains the latest features (and potential bugs).

### 2. Deploy

Download the chosen file to a directory on your server (e.g., `netalertx/`). You can switch between Stable and Dev versions easily by pointing to the specific file.

**For Stable:**
```bash
docker compose -f docker-compose.yml up -d --force-recreate
```

**For Development:**
```bash
docker compose -f docker-compose.dev.yml up -d --force-recreate
```

> [!NOTE]
> The `--force-recreate` flag ensures that your container is rebuilt with the latest configuration, making it seamless to switch between versions. Initial startup might take a few minutes.

## ⚙️ Configuration

### Storage
By default, these files use a **Docker Named Volume** (`netalertx_data`) for persistent storage. This is the easiest way to get started and ensures data persists across upgrades.

> [!TIP]
> If you prefer to map a specific folder on your host (e.g., `/mnt/data/netalertx` on Proxmox or TrueNAS), edit the `volumes` section in the compose file to use a **bind mount** instead.

### Networking
The container uses `network_mode: host` by default. This is **required** for core features like ARP scanning (`arp-scan`) to work correctly, as the container needs direct access to the network interface to discover devices.

### Environment Variables
You can customize the application by editing the `environment` section in the compose file. Common overrides include:

*   Timezone is controlled by the read-only `/etc/localtime` bind mount (do not use a `TZ` variable).
*   `SCAN_SUBNETS`: Not present by default in the compose `environment` blocks. You must manually add it if you need to override subnet scanning (e.g., `192.168.1.0/24`).

For a full list of environment variables and configuration options, see the [Customize with Environment Variables](https://docs.netalertx.com/DOCKER_COMPOSE/?h=environmental+variables#customize-with-environmental-variables) section in the documentation.

---
[⬅️ Back to Main Repo](../../README.md)
