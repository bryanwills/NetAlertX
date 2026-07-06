---
name: skills-index
description: Index of all available skills across both Gemini CLI (.gemini/skills/) and GitHub Copilot (.github/skills/). Load this to find the right skill for a task, or to locate the counterpart skill in the other AI system.
---

# Skills Index — Cross-Reference

Two AI assistants are configured for this project, each with their own skill directory:

- **Gemini CLI** → `.gemini/skills/`
- **GitHub Copilot** → `.github/skills/`

Skills with the same purpose exist in both, sometimes under different names and with different depth. This index maps them so you can find the richer version when needed.

---

## Shared Skills (exist in both)

| Topic | Gemini Skill | Copilot Skill | Notes |
|-------|-------------|--------------|-------|
| Testing | `testing-workflow` | `testing-workflow` | Gemini version emphasises full suite preference and container detection; Copilot version covers `testFailure` tool and PYTHONPATH |
| Settings & config | `settings` | `settings-management` | Gemini version is more comprehensive (22-point guide + PR checklist); Copilot version covers `ccd()` and `get_setting_value()` usage |
| MCP activation | `mcp-activation` | `mcp-activation` | Gemini version covers Gemini CLI session restart; Copilot version covers VS Code window reload |
| Project navigation | `project-navigation` | `project-navigation` | Copilot version has full path tables and env vars; Gemini version is a brief reference |
| Plugin dev | `plugin-development` | `plugin-run-development` | Copilot version is comprehensive (data contract, phases, formats); Gemini version is a brief checklist pointing to `docs/PLUGINS_DEV.md` |
| Devcontainer | `devcontainer-management` | `devcontainer-services` + `devcontainer-setup` + `devcontainer-configs` | Gemini combines into one (uses `docker exec`); Copilot splits into 3 focused skills |

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
