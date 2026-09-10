---
name: scan-pipeline
description: Reference for how the scan pipeline actually works — process_scan()'s call order, the CurrentScan/Events/Sessions/DevicesView relationships, how a session actually "closes" (there is no close function), and the FIELD_SPECS field-write authority mechanism. Load this before modifying server/scan/session_events.py or server/scan/device_handling.py, or when reasoning about device presence, connect/disconnect events, or session/timeline behavior.
---

# Scan Pipeline & Device Presence Lifecycle

## Scope

This skill covers what happens *after* a plugin's rows land in `CurrentScan` — presence computation, event generation, and session/timeline derivation. It does not cover the plugin-authoring side (manifest, data contract, settings) — see the `plugin-development` skill and `docs/PLUGINS_DEV*.md` for that. It also does not cover the general `*Source` attribution system or SQLite triggers for audit logging — see the `database-patterns` skill (Copilot tree only, as of this writing) for that; the field-authority section below is the scan-pipeline-local half of that bigger system, and the two overlap.

## The core tables/views and their lifetimes

- **`CurrentScan`** — ephemeral scratch table. Populated by `process_plugin_events()` for any plugin whose `config.json` declares `mapped_to_table`, then fully deleted at the end of every `process_scan()` cycle (`DELETE FROM CurrentScan`). Never assume a value written into a `CurrentScan` row is readable outside the cycle it arrived in — by the time a later cycle needs to check "was this row flagged X," the row is gone. This bit a real design (see Gotcha 2 below).
- **`Devices`** — persistent identity + state table.
- **`Events`** — persistent, append-only log of state-transition events (`New Device`, `Connected`, `Down Reconnected`, `Device Down`, `Disconnected`, `IP Changed`). This *is* the audit trail; `Sessions` is derived from it, not the other way around.
- **`Sessions`** — not incrementally updated; fully wiped and rebuilt every cycle from a view (see `Convert_Events_to_Sessions` below). Don't reason about it as a live connection state machine — it's a materialized query result recomputed from `Events` each cycle.
- **`Online_History`** — persistent, one row per scan cycle, feeds the dashboard's online/offline graph. Purely a rollup of `devPresentLastScan`/`devAlertDown`/`devIsSleeping` counts on `DevicesView` — no independent state of its own.

## Key views

- **`LatestDeviceScan`** (`server/db/db_upgrade.py`) — `Devices` LEFT JOIN'd to the most recent `CurrentScan` row **per `(scanMac, scanSourcePlugin)` pair**, ranked via `ROW_NUMBER() OVER (PARTITION BY scanMac, scanSourcePlugin ...)`. This is why `update_devices_data_from_scan()` loops over `DISTINCT scanSourcePlugin` and re-queries this view once per plugin: when two plugins report the same device in the same cycle, they are *not* merged into one row before processing — each plugin's contribution is evaluated independently, per field, through the authority mechanism below.
- **`LatestEventsPerMAC`** — most recent Event per MAC, joined to `Devices` and `CurrentScan`. Used by the "New Connections" query in `insert_events()` to decide whether a device was previously down (→ `Down Reconnected`) or genuinely new (→ `Connected`).
- **`Convert_Events_to_Sessions`** — the actual definition of "is this device's session still open." **There is no `close_session()`-style function anywhere in this codebase.** A session closes purely as an emergent property: `pair_sessions_events()` sets `evePairEventRowid` on a `New Device`/`Connected`/`Down Reconnected` Event to point at the next `Disconnected`/`Device Down` Event for that MAC, and this view computes `sesStillConnected = 1` exactly when that pairing is still `NULL`. If a session needs to close, the fix is always "make sure the right `Events` row gets inserted" — never a direct `Sessions` mutation (the one exception is `create_new_devices()`'s reconnect-insert, noted below).
- **`DevicesView`** — adds computed `devIsSleeping`/`devFlapping`/`devStatus` on top of `Devices`. This is what the UI and `insertOnlineHistory()` actually read presence from, not the raw `Devices` table.

## `process_scan()` call order (`server/scan/session_events.py`) — the order is load-bearing, not incidental

1. `save_own_device()`, `exclude_ignored_devices()`
2. `insert_events(db)` — **runs before presence gets updated for this cycle.** Deliberate: the Down/Disconnected/Connected queries need the *previous* cycle's `devPresentLastScan` value to detect a transition (present last cycle but absent now, or vice versa). If this ran after the presence update, every query would see the already-updated value and the edge-triggered design would collapse into either never firing or firing every cycle.
3. `create_new_devices(db)` — the source comment is explicit: "after create events -> avoid 'connection' event." Brand-new devices get a `New Device` event instead of a `Connected` event, because at step 2 they didn't exist as `Devices` rows for either query to match. Also contains a raw `INSERT INTO Sessions ... sesStillConnected = 1` for devices that already exist but have no currently-open session — the one place outside the `Events`-derived path that writes `Sessions` directly.
4. `update_devices_data_from_scan(db)` — field-level updates for existing devices; see the authority mechanism below.
5. `update_sync_hub_node`, `update_devLastConnection_from_CurrentScan`
6. `update_presence_from_CurrentScan(db)` — sets `devPresentLastScan` from bare `CurrentScan` presence *for this cycle* (this becomes the "previous" value step 2 reads on the *next* cycle).
7. `update_devPresentLastScan_based_on_nics(db)` — NIC/parent-child presence aggregation; can override step 6's result for parent devices.
8. `update_devPresentLastScan_based_on_force_status(db)` — the user's manual `devForceStatus` override, runs **last**, wins unconditionally over everything above.
9. `update_vendors_from_mac`, `update_ipv4_ipv6`, `update_icons_and_types`
10. `pair_sessions_events(db)` — pairs `Events` rows as described above.
11. `create_sessions_snapshot(db)` — `DELETE FROM Sessions; INSERT INTO Sessions SELECT * FROM Convert_Events_to_Sessions`. This is the point where `Sessions` actually reflects step 10's pairing.
12. `insertOnlineHistory(db)` — dashboard graph rollup.
13. `skip_repeated_notifications(db)`
14. `DELETE FROM CurrentScan` — the ephemeral table's entire lifetime is one call to `process_scan()`.

## Field-write authority for scan-derived updates

`update_devices_data_from_scan()` (`server/scan/device_handling.py`) does not blindly overwrite fields from whichever plugin ran most recently. Each trackable field is declared once in `FIELD_SPECS` (`scan_col`, `source_col`, a `priority` list of plugin prefixes, optional `allow_override_if_changed`), and `can_overwrite_field()` uses that plus `get_plugin_authoritative_settings()` (which reads a plugin's own settings for an explicit authority override) to decide, per field per row, whether this plugin's value may replace what's there. The paired `<field>Source` column (`devNameSource`, `devLastIPSource`, etc.) records who currently owns the field. `devMac` itself is never a target of these updates — it's the join key, not a tracked field — so no scan-derived update path can ever alter a device's identity, only its attributes.

This is the scan-pipeline-local half of a bigger attribution system — see the `database-patterns` skill for `FIELD_SOURCE_MAP` / `server/db/authoritative_handler.py`, the full `*Source` attribution model, and how SQLite triggers consume it for audit logging. Read both if touching anything that writes a `*Source` column.

## Two real gotchas (not hypothetical — both surfaced live during a design review)

1. **A "presence" check almost always exists in more than one place.** When adding a per-row signal meaning "don't count this as a live sighting" (e.g. a proposed `scanPresence` column), every query that independently re-derives "is this MAC currently present" from `CurrentScan` has to be updated together — `update_presence_from_CurrentScan()`, the `insert_events()` "New Connections"/"Device Down"/"Disconnected" queries, and the raw `INSERT INTO Sessions` inside `create_new_devices()` all encode that same question separately. Patching one and missing a sibling produces a UI where the device badge, the Events log, and the Sessions timeline each tell a different story for the same device. See `.gemini/internal-docs/PRDs/plugin-import-behavior-controls.md` for the worked example — a `scanPresence = 0` transition that never closed its session because only one of three "is it present" queries had been patched.
2. **`CurrentScan` is deleted at the end of every cycle — a per-row flag on it cannot express a decision that needs to survive to a cycle where the row is absent.** Anything that fires specifically *because* a row is missing (`Device Down`, `Disconnected`) cannot read a flag that lived on that now-gone row. If a per-row plugin signal needs to affect behavior beyond the cycle it arrived in, persist it onto the `Devices` row at creation time (e.g. seeding `devAlertDown`/`devAlertEvents` from the row's flag instead of the global `NEWDEV_*` defaults) rather than trying to make the ephemeral table carry it forward.

## When to read this vs. other docs/skills

- Writing or reviewing a plugin's `config.json`/data contract → `plugin-development` skill, `docs/PLUGINS_DEV*.md`. This skill is about what happens *after* a plugin's rows land in `CurrentScan`, not the plugin-authoring contract itself.
- Devices-table write paths, `*Source` attribution, audit/history logging, SQLite triggers → `database-patterns` skill.
- Actually implementing a change here → read the relevant function in `server/scan/session_events.py` / `server/scan/device_handling.py` directly before trusting this skill's line-number references; they're a map, not a guarantee, and will drift as the code moves.
