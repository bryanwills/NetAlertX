"""
Repo-wide convention checks for `server/plugins/*/config.json`.

These enforce the "Conventions Checklist" in docs/PLUGINS_DEV.md so a plugin
PR fails CI instead of relying on a reviewer noticing by hand.

    pytest test/plugins/test_plugin_conventions.py -v
"""

import json
import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_PLUGINS_DIR = os.path.join(_ROOT, 'server', 'plugins')

# Core/maintenance plugins that intentionally run on a schedule out of the box
# (see docs/PLUGINS_DEV.md#conventions-checklist) instead of defaulting to
# "disabled" like every optional/import-style plugin.
_ALLOWED_NON_DISABLED_RUN_DEFAULTS = {
    "csv_backup": "schedule",
    "db_cleanup": "schedule",
    "maintenance": "schedule",
    "vendor_update": "schedule",
    "sync": "unused",
}

# Settings UI real-estate: descriptions render directly in Settings, not a
# README. Cap chosen well above every current plugin's length (longest is
# ~135 chars) so it only catches a genuine outlier, not routine phrasing.
_MAX_DESCRIPTION_LENGTH = 200


def _discover_plugin_dirs():
    """Every plugin folder with a config.json, skipping __-prefixed folders
    and any folder carrying an `ignore_plugin` marker (same rules the app's
    own loader uses - see server/utils/plugin_utils.py:get_plugins_configs)."""
    names = []
    for entry in sorted(os.listdir(_PLUGINS_DIR)):
        plugin_dir = os.path.join(_PLUGINS_DIR, entry)
        if not os.path.isdir(plugin_dir) or entry.startswith('__'):
            continue
        if os.path.isfile(os.path.join(plugin_dir, 'ignore_plugin')):
            continue
        if os.path.isfile(os.path.join(plugin_dir, 'config.json')):
            names.append(entry)
    return names


_PLUGIN_NAMES = _discover_plugin_dirs()


def _load_config(plugin_name):
    path = os.path.join(_PLUGINS_DIR, plugin_name, 'config.json')
    with open(path) as f:
        return json.load(f)


@pytest.mark.parametrize('plugin_name', _PLUGIN_NAMES)
def test_config_json_is_valid_json(plugin_name):
    path = os.path.join(_PLUGINS_DIR, plugin_name, 'config.json')
    with open(path) as f:
        content = f.read()
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        pytest.fail(f'{plugin_name}/config.json is not valid JSON: {e}')


@pytest.mark.parametrize('plugin_name', _PLUGIN_NAMES)
def test_run_defaults_to_disabled(plugin_name):
    config = _load_config(plugin_name)
    run_setting = next(
        (s for s in config.get('settings', []) if s.get('function') == 'RUN'),
        None,
    )
    if run_setting is None:
        return  # no RUN setting (e.g. a config-only plugin) - nothing to check

    default = run_setting.get('default_value')
    allowed = _ALLOWED_NON_DISABLED_RUN_DEFAULTS.get(plugin_name)
    if allowed is not None:
        assert default == allowed, (
            f'{plugin_name}: expected the allow-listed RUN default {allowed!r}, got {default!r}. '
            'If this plugin no longer needs an exception, remove it from '
            '_ALLOWED_NON_DISABLED_RUN_DEFAULTS.'
        )
    else:
        assert default == 'disabled', (
            f'{plugin_name}: RUN defaults to {default!r}, expected "disabled". '
            'Non-core plugins must load disabled until the user configures them - '
            'see docs/PLUGINS_DEV.md#conventions-checklist. If this is a core/maintenance '
            'plugin that legitimately needs to run out of the box, add it to '
            '_ALLOWED_NON_DISABLED_RUN_DEFAULTS in this test.'
        )


@pytest.mark.parametrize('plugin_name', _PLUGIN_NAMES)
def test_description_is_concise(plugin_name):
    config = _load_config(plugin_name)
    for desc in config.get('description', []):
        if desc.get('language_code') != 'en_us':
            continue
        text = desc.get('string', '')
        assert len(text) <= _MAX_DESCRIPTION_LENGTH, (
            f'{plugin_name}: description is {len(text)} chars (max {_MAX_DESCRIPTION_LENGTH}). '
            'This renders directly in the Settings UI - keep it short and move '
            'implementation rationale to the README instead. '
            'See docs/PLUGINS_DEV.md#conventions-checklist.'
        )
