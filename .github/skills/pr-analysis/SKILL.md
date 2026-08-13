---
name: netalertx-pr-analysis
description: How to analyze and respond to GitHub PR review comments in NetAlertX. Use this whenever you are addressing PR feedback, review threads, or inline code comments.
---

# PR Analysis

## Before Acting on Any PR Comment

1. Load `code-standards` skill — all code changes must comply with it before replying.
2. Load `testing-workflow` skill — any test additions or changes must follow it.
3. Load any domain-specific skill relevant to the files being changed (e.g. `database-patterns` for DB writes, `settings-management` for config).

## Comment Classification

For each comment, determine:

| Type | Action |
|------|--------|
| Request for code change | Make the change, validate it, then reply with the short commit hash |
| Question about code | Reply with a concise answer (no restatement of the question) |
| Suggestion / feedback | Decide if it is actionable. If yes, act and reply. If not, do not reply. |
| General / praise | Do not reply. |

## Acting on Comments — Step by Step

1. **Identify all actionable comments** before touching any file.
2. **Load relevant skills** to understand conventions that apply.
3. **Prepare a plan** — list each file and the exact change required.
4. **Make changes one comment at a time** — keep commits focused.
5. **Run targeted tests** after each change (`testing-workflow` skill).
6. **Reply** only after the commit is pushed via `report_progress`. Include the short SHA.

## Reply Guidelines

- Be concise. Do not summarize or restate the original comment.
- State what was done and (optionally) why.
- Include the short commit hash when relevant.
- Do not thank or compliment the reviewer.

## What to Check After Every Batch of Changes

- All MACs are lowercase everywhere (code-standards).
- No mocks or DB helpers are re-defined locally — use `test/db_test_helpers.py` (code-standards).
- No inline imports — all imports at the top of the file (code-standards).
- Tests live under a subdirectory of `test/` matching the source path, not in `test/` root (code-standards).
- Secret scan (`runtime-tools-secret_scanning`) before committing.

## Stacked / Base-Branch Issues

When a PR targets a non-default branch (e.g. `next_release`):
- Do **not** retarget the branch yourself; note it in a reply so the author can do it from the GitHub UI.
- Check CI failures on the **base branch** first before checking your branch.
