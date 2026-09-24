---
name: netalertx-plugin-review
description: Read when reviewing a plugin PR or auditing an existing plugin script (server/plugins/*/script.py or equivalent). Covers two checks not already mechanically enforced by test_plugin_conventions.py - plugin scripts embedding their own raw SQL instead of an existing/new model method, and suspicious/attacker-influenced plugin data not being logged - plus worked real-PR examples.
---

# Plugin Review

## Scope

This is a reviewer-facing checklist, complementary to [[plugin-development]] (which is author-facing). For `config.json` conventions already covered there and mechanically checked by `test/plugins/test_plugin_conventions.py` — `RUN` default, `RUN_TIMEOUT` reuse in a loop, `dataType`/`default_value` agreement, description length — defer to that skill's "Before Opening a PR" checklist rather than re-deriving them here.

## The check this skill adds: no raw SQL in a plugin script

Plugin scripts write their results to `RESULT_FILE` via `plugin_helper.Plugin_Objects` — the framework inserts those rows into the DB. A plugin that also runs its own `SELECT`/`INSERT`/`UPDATE` (via `sqlite3` directly or `database.get_temp_db_connection()`) is bypassing that contract, usually to read existing data before deciding what to write.

**Default for a new/contributed plugin: use an existing model method (`server/models/*.py`), or add one, instead of a raw SQL string in the plugin.** Not GraphQL — GraphQL (`/graphql`) is the frontend-facing API; no plugin in this codebase reaches it, and doing so would mean an HTTP round-trip (with an API token) from a subprocess that already has direct `server/` import access. Every plugin that currently touches the DB imports `server/` modules directly, matching how the rest of the backend is layered (`CLAUDE.md`: "Never query the DB from elsewhere — go through a model or `db_helper.py`" — this is that same rule, just also applying to plugins).

**Known exception — 5 existing core/infrastructure plugins legitimately use `get_temp_db_connection()` with raw SQL:** `db_cleanup` (retention `DELETE`s + `REINDEX` — no model method fits a multi-table retention sweep), `heartbeat`, `vendor_update`, `csv_backup`, `sync`. These predate this rule and do maintenance/schema-level work (bulk retention, `PRAGMA table_info`, full-table export) that doesn't map to a single-row model method. Don't treat their existence as precedent for a *new* plugin's simple lookup query — check whether an existing method already covers the new plugin's actual need first (it usually does, or is a one-line addition).

## Review flow for a raw SQL query in a plugin

1. **Does an existing model method already do this?** Check the relevant `server/models/*_instance.py` file (`DeviceInstance`, `EventInstance`, `PluginObjectInstance`, etc.) before assuming one needs to be added.
2. **If not, is it worth adding one** (`server/models/device_instance.py` etc.), or is this a one-off maintenance/schema query that belongs in the core-plugin exception list above?
3. **Check the collation the query relies on** against the column's actual schema (`server/db/schema/app.sql`) rather than assuming — `devMac`/`eveMac`/`sesMac`/`scanMac`/`devParentMAC` are declared `COLLATE NOCASE` at the column level, so an explicit `COLLATE NOCASE` against one of them in a new query is redundant (harmless, but a sign the author didn't check). `devName` has **no** column-level collation — an explicit `COLLATE NOCASE` there is necessary if case-insensitive name matching is intended, not a mistake.
4. **Parameterization** — `?` placeholders, never string-formatted values into the query (this part is usually already fine; flag it if not).

## Worked example: PR #1788 (DOCKERDISC plugin)

Two raw queries in `server/plugins/dockerdisc/script.py`:

- `lookup_device_mac()`: `SELECT 1 FROM Devices WHERE devMac = ? COLLATE NOCASE LIMIT 1` — an existence check. `DeviceInstance.getByMac(mac)` already does this exact lookup (`server/models/device_instance.py:102-105`); its `COLLATE NOCASE` is redundant since `devMac` already carries that collation at the column level. **Fix: `DeviceInstance().getByMac(mac) is not None`, delete the raw SQL.**
- `resolve_host_mac()`: `SELECT devMac FROM Devices WHERE devName = ? COLLATE NOCASE` — a name lookup with real 0/1/many-match handling (falls back to a manually-configured MAC on ambiguity or no match). No existing method covers this. `devName` has no column-level collation, so the explicit `COLLATE NOCASE` here is correct, not redundant. **Fix: add `DeviceInstance.getAllByName(name)` returning every match** (not just one — the plugin's own ambiguity detection needs the full set), and have the plugin call that instead.

This is the shape of the fix in general: an existence/single-row check usually already has a model method; a query with plugin-specific result handling (ambiguity, filtering) usually needs a small new method added rather than a workaround in the plugin itself.

## The second check this skill adds: suspicious/attacker-influenced plugin data must be logged

A plugin that parses data from an unauthenticated peer (DHCP options, mDNS/Avahi records, NetBIOS name-service responses, SSDP/UPnP, any broadcast/discovery protocol) is trusting the network, not the device it's nominally scanning — any device on the segment can answer. When such a value gets rejected, sanitized, or otherwise flagged as suspicious/malformed, that's a security-relevant event, not routine parsing noise: **is it logged?**

At minimum, every such detection needs `mylog("none", ...)` (`logger.py`'s `debugLevels` — `"none"` is level 0, the always-shown floor, not filtered out at any configured `LOG_LEVEL` — matching how this codebase already logs real errors, e.g. `mylog("none", f"[Plugins] ⚠ ERROR: {e}")`). A silently-dropped or silently-mangled value with no log trace is the finding to raise — an admin investigating "why does this device's name look wrong" or "was my network probed" has nothing to go on otherwise.

**A user-facing alert (`write_notification()`, `server/messaging/in_app.py`) is a separate, materially bigger decision: don't require it as a blocking condition the way the log line is.** It's persistent and unprompted, and (per existing precedent: `api_server_start.py`'s unauthorized-access-attempt alert fires unconditionally, with no rate-limiting anywhere in this codebase) a repeat offender re-sending the same payload every scan cycle can spam it indefinitely unless the PR gates it correctly on `process_plugin_events()`'s existing per-object status (`server/plugin.py:769-791`): fire only on `"new"` or `"watched-changed"`, never on `"watched-not-changed"` (that status is set every cycle a value stays the same, so alerting on it defeats the suppression entirely). For a missing-object alert, fire only on the transition into `"missing-in-last-scan"` (`server/plugin.py`'s `if tmpObj.status != "missing-in-last-scan":` guard around line 807), not on every cycle the object remains in that status. If a PR adds `write_notification()` for this without matching that gating, that's the thing to flag, not the absence of a user-facing alert on its own.

**Worked example (generalized):** a plugin parses an unauthenticated broadcast-protocol response (e.g. a DHCP option, an mDNS/NetBIOS record) and copies a field from it verbatim into a stored value with no validation. The fix centralizes both the sanitization *and* the `mylog("none", ...)` call in one shared, plugin-agnostic enforcement point (`plugin_object_class.__init__`, `server/plugin.py`) rather than leaving individual plugin authors to remember either — the same reasoning as the raw-SQL check above: a check that depends on every plugin author independently thinking to add it will eventually ship without it.
