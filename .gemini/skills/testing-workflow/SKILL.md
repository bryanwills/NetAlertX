---
name: testing-workflow
description: Read before running tests. Detailed instructions for single, astandard unit tests (fast), full suites (slow), and handling authentication. Tests must be run when a job is complete.
---

# Testing Workflow
After code is developed, tests must be run to ensure the integrity of the final result.

**Crucial:** Tests MUST be run inside the container to access the correct runtime environment (DB, Config, Dependencies).


## 1. Full Test Suite (MANDATORY DEFAULT)

Unless the user **explicitly** requests "fast" or "quick" tests, you **MUST** run the full test suite. **Do not** optimize for time. Comprehensive coverage is the priority over speed.

```bash
cd /workspaces/NetAlertX; pytest test/
```

## 2. Fast Unit Tests (Conditional)

**ONLY** use this if the user explicitly asks for "fast tests", "quick tests", or "unit tests only". This **excludes** slow tests marked with `docker` or `feature_complete`.

```bash
cd /workspaces/NetAlertX; pytest test/ -m 'not docker and not feature_complete'
```

## 3. Running Specific Tests

To run a specific file or folder:

```bash
cd /workspaces/NetAlertX; pytest test/<path_to_test>
```

*Example:*
```bash
cd /workspaces/NetAlertX; pytest test/api_endpoints/test_mcp_extended_endpoints.py
```

## Authentication in Tests

The test environment uses `API_TOKEN`. The most reliable way to retrieve the current token from a running container is:

```bash
python3 -c "from helper import get_setting_value; print(get_setting_value('API_TOKEN'))"
```

### Troubleshooting

If tests fail with 403 Forbidden or empty tokens:
1. Verify server is running and use the setup script (`/workspaces/NetAlertX/.devcontainer/scripts/setup.sh`) if required.
2. Verify `app.conf` inside the container: `cat /data/config/app.conf`
3. Verify Python can read it: `python3 -c "from helper import get_setting_value; print(get_setting_value('API_TOKEN'))"`