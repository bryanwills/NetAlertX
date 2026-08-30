## Overview - PIHOLEMON Plugin — Pi-hole Monitor

The **PIHOLEMON** plugin does two jobs against the same Pi-hole connection(s):

1. **Device import** - same job as the official **PIHOLEAPI** (`pihole_api_scan`) plugin: pulls the device list from Pi-hole and feeds it into NetAlertX's normal device-scanner pipeline, so a device Pi-hole knows about but NetAlertX doesn't gets created automatically.
2. **Query anomaly detection** - flags a device whose *blocked*-query count spikes well above its own recent average, the classic signature of malware or a compromised device beaconing out to blocklisted domains. This is deliberately not the same thing as device discovery: it's about a device you already know suddenly behaving differently, not a new device showing up.

Both share one login per Pi-hole instance and one settings page, instead of being two separately configured pieces that happen to need the same credentials.

Two design choices worth knowing about:

* **Both a primary and an optional secondary/failover Pi-hole are checked, and their results combined.** Watching only one leaves an obvious blind spot for the anomaly detection - a device can simply point at the other resolver and never show up. Leave the secondary URL blank if you only run one Pi-hole; most setups do.
* **The anomaly baseline is keyed by MAC address, not IP.** DHCP-assigned IPs change; since this plugin already has the device list from Pi-hole itself, it resolves IP to MAC from that same data - no separate lookup needed for that part. A device owner, if you use NetAlertX's `devOwner` field, is looked up via NetAlertX's own GraphQL API purely to make the anomaly label friendlier; it's optional and never blocks import or detection if unavailable.

### Why not just run two copies of PIHOLEAPI for two Pi-holes?

We looked into this first. `pihole_api_scan.py` hardcodes its settings-key prefix (`PIHOLEAPI_URL`, `PIHOLEAPI_PASSWORD`, ...) as literal strings throughout the script rather than reading it from `config.json`. Duplicating the plugin folder gives you two copies that both read and write the *same* settings keys - not two independent instances - and NetAlertX's own plugin docs don't describe an officially supported way to run multiple instances of one plugin. Making a real second instance means forking the script and renaming every occurrence of the prefix by hand, which then has to be kept in sync manually with any upstream changes. This plugin exists so that isn't necessary: it accepts two sets of credentials natively and was designed to support that from the start - for both the device-import half and the anomaly-detection half.

### Quick setup guide

* You are running **Pi-hole v6** or newer on every instance you configure (this plugin uses `/api/auth`, `/api/network/devices`, and `/api/stats/top_clients`, none of which exist in v5).
* An **App Password** is generated on each Pi-hole (`Settings → Web Interface / API → App Password`) - recommended over using the admin login password directly.

#### 🔒 A note on `http://` vs `https://`

Most home Pi-hole setups (including the one this plugin was developed and tested against) run over plain `http://` on a trusted LAN, and that's what the examples below use - this plugin doesn't require `https://` or refuse an `http://` URL. Know the trade-off either way, though: over `http://`, the App Password/admin password is sent in cleartext on every run, readable by anything else that can see that network segment (a compromised device, a hostile guest network, etc.). If your Pi-hole's admin interface is reachable from anywhere less trusted than your own LAN, either put it behind `https://` (Pi-hole's own self-signed cert, or a reverse proxy with a real one) or keep it LAN-only. **PIHOLEMON_VERIFY_SSL** only matters once you're on `https://` - it's on by default, and turning it off to tolerate a self-signed cert accepts *any* certificate, including an attacker's; installing that self-signed CA as trusted on the machine running NetAlertX is the safer way to use a self-signed cert if you need one.

### Usage

- Head to **Settings** > **Pi-hole Monitor** to fill in the values below.

| Setting Key                       | Description                                                                                       |
| ---------------------------------- | --------------------------------------------------------------------------------------------------- |
| **PIHOLEMON_PRIMARY_URL**          | Required. URL to your primary Pi-hole, e.g. `http://192.168.1.10/`.                                |
| **PIHOLEMON_PRIMARY_PASSWORD**     | App Password (or admin password) for the primary Pi-hole.                                          |
| **PIHOLEMON_SECONDARY_URL**        | Optional. URL to a secondary/failover Pi-hole, e.g. `http://192.168.1.11:8080/`. Leave blank if you only run one. |
| **PIHOLEMON_SECONDARY_PASSWORD**   | Only used if a secondary URL is set.                                                                |
| **PIHOLEMON_GET_OFFLINE**          | Import devices even if not recently seen. Default off.                                             |
| **PIHOLEMON_CONSIDER_ONLINE**      | Seconds since last seen to still count a device as online. Default `300`.                          |
| **PIHOLEMON_VERIFY_SSL**           | Verify TLS certificates on an `https://` URL. Default **on**. Only disable if a Pi-hole uses a self-signed certificate you can't install as trusted - see the security note below. |
| **PIHOLEMON_API_MAXCLIENTS**       | Maximum devices requested **per instance**'s device list. Default `500`.                            |
| **PIHOLEMON_FAKE_MAC**             | Generate a fake MAC from the IP for devices with a non-standard hardware address. Default off.     |
| **PIHOLEMON_GRAPHQL_URL**          | NetAlertX's own GraphQL endpoint, for the optional owner lookup. Defaults to `http://127.0.0.1:20212/graphql` (this plugin runs inside the NetAlertX container). |
| **PIHOLEMON_GRAPHQL_TOKEN**        | API token for the GraphQL endpoint, if one is configured.                                          |
| **PIHOLEMON_MULTIPLIER**           | Flag a device when its blocked-query count exceeds this many times its own recent average. Default `4`. |
| **PIHOLEMON_MIN_BLOCKED**          | Ignore devices below this absolute blocked-query count, even if the multiplier is exceeded. Default `20`. |
| **PIHOLEMON_HISTORY_LENGTH**       | How many recent runs to keep per device for the rolling baseline. Default `28` (one week at the default 6-hour schedule). |
| **Watched** *(standard NetAlertX setting)* | Which columns count as "changed" for notification purposes. Defaults to `watchedValue4` (the anomaly/normal flag) only - the raw blocked-query count changes every run by design. |
| **Report on** *(standard NetAlertX setting)* | Which statuses actually notify. Defaults to `watched-changed` only, so you hear about it exactly when a device flips into (or out of) an anomaly. |

This plugin does **not** send notifications on its own - it relies on NetAlertX's own core, which diffs the columns picked in **Watched** between runs and, on a match against **Report on**, dispatches through whichever publisher(s) you already have enabled under **Settings → Notifications** (ntfy, Apprise, email, Telegram, ...).

One extra setting is required for that to actually reach you: NetAlertX's **Notification Processing** plugin (`NTFPRCS`) has its own **"Notify on"** setting (`NTFPRCS_INCLUDED_SECTIONS`), and its default value - `new_devices`, `down_devices`, `events` - does **not** include `plugins`. Without `plugins` in that list, this plugin's Watched/Report on matches are recorded correctly but never make it into a notification. Add `plugins` to `NTFPRCS_INCLUDED_SECTIONS` once, and it also covers any other plugin using the same mechanism, not just this one.

The default text notification for the `plugins` section is a generic vertical `Header: Value` dump. For something more readable, set `NTFPRCS`'s **"Text Template: Plugins"** (`NTFPRCS_TEXT_TEMPLATE_plugins`) to something like:

```
{objectPrimaryId} [{watchedValue2}] @ {objectSecondaryId} → {watchedValue4} ({watchedValue3} blocked)
```

Only the columns the `plugins` section actually selects are available as placeholders (`{plugin}`, `{objectPrimaryId}`, `{objectSecondaryId}`, `{dateTimeChanged}`, `{watchedValue1-4}`, `{status}`) - `extra` (where this plugin's `owner`/`ratio` detail lives) isn't one of them, so that richer text is only visible on the device's page in NetAlertX, not in the notification itself. This template setting is global to `NTFPRCS`, so it affects any plugin using Watched/Report on, not just this one.

If the same device (same MAC) is seen on both instances, the entry with the more recent "last seen" timestamp wins - it isn't imported twice, and its blocked-query counts from both instances are summed, not compared separately.

### Testing the notification pipeline end-to-end

Waiting for real, organic beaconing traffic to confirm notifications actually arrive isn't practical. The clean way to force a `normal` → `anomaly` transition on demand, without touching any internal state file by hand:

1. Temporarily set `PIHOLEMON_MULTIPLIER` to something like `1.01` and `PIHOLEMON_MIN_BLOCKED` to `1`.
2. Run the plugin (wait for its schedule, or trigger it manually from the UI).
3. Any device with a baseline and *any* blocked traffic should now flip to `anomaly` - confirming the whole chain: Watched/Report on match → `Plugins_Events` row → NetAlertX's Notification Processing (`NTFPRCS`, needs `plugins` in `NTFPRCS_INCLUDED_SECTIONS`, see above) → your configured publisher.
4. Set `PIHOLEMON_MULTIPLIER`/`PIHOLEMON_MIN_BLOCKED` back to their real values afterward - left at the test values, everything with any traffic at all reads as an anomaly.

### ⚠️ Troubleshooting

---

#### ❌ Authentication failed / no data from a Pi-hole instance

* Confirm the URL includes the scheme (`http://`/`https://`) and, if not on the default port, the port too - e.g. `http://192.168.1.10/` ✔, `http://192.168.1.10/admin` ❌.
* Confirm that instance is running **Pi-hole v6**, not v5.
* SSL verification matches your setup (disable for self-signed certificates).
* Try the App Password by hand first: `curl -X POST <url>/api/auth -d '{"password":"<app password>"}'` should return a `session.sid`.
* Check the plugin log for `[PIHOLEMON] <label>: ...` lines - `label` is `primary` or `secondary`, so you can tell which instance is the problem.

---

#### ❌ Some devices are missing

* Devices with an invalid MAC are skipped unless **Generate fake MAC** is enabled - turning it on trades data consistency for coverage (the "MAC" becomes a stand-in derived from the IP, not a real hardware address).
* Offline devices don't get a device-import row (name/vendor) unless **Import offline devices** is enabled - but their MAC is still used to attribute blocked-query counts correctly, so an offline-but-active device never falls back to being tracked by bare IP.

---

#### ❌ Notifications don't arrive even though an anomaly was detected

* Check NetAlertX's own **Notification Processing** settings - the `Notify on` setting (`NTFPRCS_INCLUDED_SECTIONS`) must include `plugins`, or Watched/Report on matches never reach a notification (see the note above `Watched`/`Report on` in the settings table).
* Confirm you actually have a publisher enabled and working under **Settings → Notifications** (ntfy, Apprise, email, ...) - this plugin never sends anything itself, so a working publisher there is a prerequisite, not optional.

---

#### ❌ Anomaly label missing an owner

* NetAlertX doesn't have `devOwner` set for that device yet, or the GraphQL lookup isn't reachable - neither blocks anomaly detection, the label is just less friendly.
* Confirm `PIHOLEMON_GRAPHQL_URL`/`PIHOLEMON_GRAPHQL_TOKEN` if you expect owners to resolve.

---

#### ❌ Getting flagged for normal usage / not getting flagged for a real spike

* Both `PIHOLEMON_MULTIPLIER` and `PIHOLEMON_MIN_BLOCKED` are starting values, not tuned defaults - let it run for a week and adjust based on what's actually normal for your network.
* A device with little to no query history yet won't be flagged (no baseline to compare against) - expected for the first `PIHOLEMON_HISTORY_LENGTH` runs after enabling the plugin.

### Notes

- Device-import parsing (online/offline handling, fake-MAC fallback, endpoints used) mirrors the official `pihole_api_scan` plugin - this isn't meant to reinvent that half, only to support a second Pi-hole instance without forking it.
- This plugin never blocks, unblocks, or otherwise changes anything on either Pi-hole - it only reads.
- The rolling per-device history is kept in this plugin's own log directory (`last_result`/`state` files), not in NetAlertX's database - safe to delete if you want to reset the baseline from scratch.

- Version: 1.0.1
- Author: [mauricio-camayo](https://github.com/mauricio-camayo/)
- Release Date: `2026-08-30`
