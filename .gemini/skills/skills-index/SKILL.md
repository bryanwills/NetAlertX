---
name: skills-index
description: Index of all available skills across Gemini CLI (.gemini/skills/), GitHub Copilot (.github/skills/), and Claude Code (.claude/skills/). Load this to find the right skill for a task, or to locate the counterpart skill in another assistant's tree.
---

# Skills Index — Cross-Reference

Three AI assistants are configured for this project, each with their own skill directory:

- **Gemini CLI** → `.gemini/skills/`
- **GitHub Copilot** → `.github/skills/`
- **Claude Code** → `.claude/skills/` (currently mirrors only the 3 highest-value skills below, not the full set)

Skills with the same purpose exist in more than one, sometimes under different names and with different depth. This index maps them so you can find the richer version when needed. A CI check (`scripts/check_skill_pairs.py`, run as `check-skill-pairs` in `.github/workflows/code-checks.yml`) flags PRs that touch some but not all files in a mirrored group - non-blocking, since some divergence is intentional.

---

## Shared Skills (exist in more than one tree)

| Topic | Gemini Skill | Copilot Skill | Claude Skill | Notes |
|-------|-------------|--------------|--------------|-------|
| Testing | `testing-workflow` | `testing-workflow` | `testing-workflow` | All three cover the full-suite-by-default rule, PYTHONPATH, auth/token retrieval, and the `sys.modules` stubbing pitfall |
| Settings & config | `settings` | `settings-management` | — | Gemini version is more comprehensive (22-point guide + PR checklist); Copilot version covers `ccd()` and `get_setting_value()` usage |
| MCP activation | `mcp-activation` | `mcp-activation` | — | Gemini version covers Gemini CLI session restart; Copilot version covers VS Code window reload |
| Project navigation | `project-navigation` | `project-navigation` | — | Copilot version has full path tables and env vars; Gemini version is a brief reference |
| Plugin dev | `plugin-development` | `plugin-run-development` | `plugin-development` | All three cover data contract, phases, formats, the `RUN_TIMEOUT` kill-timer gotcha (`timeoutMultiplier`/`per_item_timeout()`), and a pre-PR pointer to the Conventions Checklist in `docs/PLUGINS_DEV.md` |
| Devcontainer | `devcontainer-management` | `devcontainer-services` + `devcontainer-setup` + `devcontainer-configs` | — | Gemini combines into one (uses `docker exec`); Copilot splits into 3 focused skills |
| PR review | `pr-analysis` | `pr-analysis` | `pr-analysis` | How to classify and respond to PR comments; pre-flight skill loading checklist |
| Logging | `logging-standards` | `logging-standards` | — | `mylog` levels, message format, what not to log |

---

## Copilot-Only Skills

No Gemini equivalent yet:

| Copilot Skill | Purpose |
|--------------|---------|
| `api-development` | Creating REST API endpoints |
| `authentication` | API tokens and 401/403 debugging |
| `code-standards` | Coding conventions and style rules |
| `database-patterns` | Device table write paths, SQLite triggers, audit logging, `*Source` attribution |
| `database-reset` | Wipe and regenerate the database and config |
| `docker-build` | Build Docker images for testing or production |
| `docker-prune` | Clean unused Docker resources (destructive — requires confirmation) |
| `sample-data` | Load synthetic device data into the devcontainer |

---

## Gemini-Only Skills

No Copilot equivalent yet:

| Gemini Skill | Purpose |
|-------------|---------|
| `initiative-start` | Research methodology and structured approach for new tasks |

---

## Adding a New Skill

When adding a skill, create it in **both** directories to keep both AI systems current:

- `.gemini/skills/<name>/SKILL.md` — auto-discovered by Gemini CLI via YAML frontmatter
- `.github/skills/<name>/SKILL.md` — add an entry to the skills table in `.github/copilot-instructions.md`

Keep the body content identical between both files. Only the frontmatter `name`/`description` may differ slightly to match each system's discovery heuristics.

If the skill is high-value enough to also mirror to Claude Code, add `.claude/skills/<name>/SKILL.md` too, and add the group to `GROUPS` in `scripts/check_skill_pairs.py` so drift gets flagged. Claude Code has no `activate_skill()`/`testFailure`/`runTests`/`report_progress` equivalents - adapt any such tool references to plain `Bash` commands instead of copying them verbatim.
