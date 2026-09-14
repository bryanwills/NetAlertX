---
name: plugin-review
description: Read when reviewing a plugin PR or auditing an existing plugin script (server/plugins/*/script.py or equivalent). Covers the one check not already mechanically enforced by test_plugin_conventions.py - plugin scripts embedding their own raw SQL instead of an existing/new model method - plus a worked real-PR example.
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
2. **If not, is it worth adding one** (`server/models/device_instance.py` etc.), or is this genuinely a one-off maintenance/schema query that belongs in the core-plugin exception list above?
3. **Check the collation the query relies on** against the column's actual schema (`server/db/schema/app.sql`) rather than assuming — `devMac`/`eveMac`/`sesMac`/`scanMac`/`devParentMAC` are declared `COLLATE NOCASE` at the column level, so an explicit `COLLATE NOCASE` against one of them in a new query is redundant (harmless, but a sign the author didn't check). `devName` has **no** column-level collation — an explicit `COLLATE NOCASE` there is genuinely necessary if case-insensitive name matching is intended, not a mistake.
4. **Parameterization** — `?` placeholders, never string-formatted values into the query (this part is usually already fine; flag it if not).

## Worked example: PR #1788 (DOCKERDISC plugin)

Two raw queries in `server/plugins/dockerdisc/script.py`:

- `lookup_device_mac()`: `SELECT 1 FROM Devices WHERE devMac = ? COLLATE NOCASE LIMIT 1` — an existence check. `DeviceInstance.getByMac(mac)` already does this exact lookup (`server/models/device_instance.py:102-105`); its `COLLATE NOCASE` is redundant since `devMac` already carries that collation at the column level. **Fix: `DeviceInstance().getByMac(mac) is not None`, delete the raw SQL.**
- `resolve_host_mac()`: `SELECT devMac FROM Devices WHERE devName = ? COLLATE NOCASE` — a name lookup with real 0/1/many-match handling (falls back to a manually-configured MAC on ambiguity or no match). No existing method covers this. `devName` has no column-level collation, so the explicit `COLLATE NOCASE` here is correct, not redundant. **Fix: add `DeviceInstance.getAllByName(name)` returning every match** (not just one — the plugin's own ambiguity detection needs the full set), and have the plugin call that instead.

This is the shape of the fix in general: an existence/single-row check usually already has a model method; a query with plugin-specific result handling (ambiguity, filtering) usually needs a small new method added rather than a workaround in the plugin itself.
