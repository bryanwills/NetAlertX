---
name: netalertx-plugin-development
description: Create and run NetAlertX plugins. Use this when asked to create plugin, run plugin, test plugin, or develop plugin functionality.
---

# Plugin Development

## Expected Workflow

1. Read this skill and `docs/PLUGINS_DEV.md` for full context.
2. Find or create the plugin in `front/plugins/<code_name>/`.
3. Read the plugin's `config.json` and `script.py` to understand its functionality.
4. Run: `python3 front/plugins/<code_name>/script.py`
5. Retrieve the result from `/tmp/log/plugins/last_result.<PREF>.log` quickly — the backend deletes it after processing.

## Run a Plugin Manually

```bash
python3 front/plugins/<code_name>/script.py
```

Ensure `sys.path` includes `/app/front/plugins` and `/app/server` (as in the template).

## Plugin Structure

```text
front/plugins/<code_name>/
├── config.json      # Manifest with settings
├── script.py        # Main script
└── ...
```

## Plugin Prefix Rules

- Uppercase letters only (no underscores, no numbers)
- Must be unique across all plugins
- Short but readable (e.g., `ARPSCAN`, `MQTT`, `UNIFI`)

## Settings Pattern

- `<PREF>_RUN`: execution phase
- `<PREF>_RUN_SCHD`: cron-like schedule
- `<PREF>_CMD`: script path
- `<PREF>_RUN_TIMEOUT`: timeout in seconds
- `<PREF>_WATCH`: columns to watch for changes

## Data Contract

Scripts write to `/tmp/log/plugins/last_result.<PREF>.log` using `plugin_helper.py`:

```python
from plugin_helper import Plugin_Objects

plugin_objects = Plugin_Objects()
plugin_objects.add_object(...)  # During processing
plugin_objects.write_result_file()  # Exactly once at end
```

**Important:** The backend processes and deletes the result file almost immediately. Retrieve it quickly if inspecting output.

## Execution Phases

| Phase | Trigger |
|-------|---------|
| `once` | Once at startup |
| `schedule` | On cron schedule |
| `always_after_scan` | After every scan |
| `before_name_updates` | Before name resolution |
| `on_new_device` | When new device detected |
| `on_notification` | When notification triggered |

## Plugin Formats

| Format | Purpose | Phase |
|--------|---------|-------|
| publisher | Send notifications | `on_notification` |
| dev scanner | Create/manage devices | `schedule` |
| name discovery | Discover device names | `before_name_updates` |
| importer | Import from services | `schedule` |
| system | Core functionality | `schedule` |

## Starting Point

Copy from `front/plugins/__template` and customize. Read `docs/PLUGINS_DEV.md` for the full development guide.


