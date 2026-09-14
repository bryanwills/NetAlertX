---
name: netalertx-skill-hygiene
description: Read before writing or editing any SKILL.md in this repo (.claude/.gemini/.github skills trees). Covers the two standing rules for skill prose - state current behavior only, and prefer plain, short wording - plus the grep sweep to run before calling a skill clean.
---

# Skill Hygiene

## What a skill is, and isn't

A skill is a live reference for how the system works *now*. It is not a lab notebook, a changelog, or a PRD. History, corrections, and discovery narratives belong in PRDs (`.gemini/internal-docs/PRDs/`, see `prd-writing`) or commit messages — never in a skill body. If a skill needs to change because the code changed, edit it in place; don't leave a trace of what it used to say.

This is a different rule from `prd-writing`'s "leave a visible trail of corrections" — that rule is specifically for PRDs, where the trail is the point. A skill has no reader who benefits from seeing your editing history; it only has readers who need the current fact, stated plainly.

## Rule 1: state current behavior only

Cut anything that narrates the past instead of stating the present:

| Smell | Why it's a problem | Fix |
|---|---|---|
| `"Correction: X — an earlier version of this note said Y"` | Narrates an edit, not a fact | Just state the current fact about X |
| `"(as of 2026-07-04)"` | Hedges instead of committing to the fact | State it as true now; update the line when it stops being true |
| `"This shipped for real in devParentRelType"` / `"...caught in review"` / `"...caught mid-review"` | Tells the story of finding a bug instead of the rule that prevents it | State the rule; use the real example as a plain parenthetical if it helps, without the origin story |
| `"Two real examples from this exact process:"` / `"during a past audit"` | Frames the skill as a diary of one session | Turn the anecdote into a timeless illustration, or drop it |
| `"X now does Y"` / `"X previously did Y"` / `"used to be"` / `"no longer"` when describing *the skill's own past text* | Describes the skill's edit history, not the system | Delete — say what's true now, full stop |

`"no longer"` describing real *system* behavior (e.g. "there is no longer a retry loop here") is fine — that's a fact about the code, not about the skill. The test is: does this sentence describe the codebase, or does it describe a previous version of this document?

## Rule 2: plain words, fewer words

If a shorter or simpler phrasing says the same thing, use it. Cut qualifiers that don't change the meaning ("actually," "really," "genuinely," "in this exact process"). Prefer a plain verb over a nominalization. A dense skill with real information beats a padded one — trim narration and hedging before trimming facts.

## Sweep before calling a skill clean

Run this across `.claude/skills/`, `.gemini/skills/`, `.github/skills/` (or a single file being edited):

```bash
grep -rniE "as of 202|caught in review|caught mid-review|correction:|correction \(|shipped for real|previously|used to be|no longer|originally|was later|historically|in the past|distilled from|real mistake|it turned out|turns out|discovered that|during a past" .claude/skills/ .gemini/skills/ .github/skills/
```

Read every hit in context — some are legitimate (a rule instructing PRD authors to write correction trails, or "previously down" describing device state, are not violations). Fix the ones that narrate the skill's own history instead of the system's current behavior.

## Keep the three trees in sync

Most skills exist as three near-identical copies (`.claude/skills/<name>/SKILL.md`, `.gemini/skills/<name>/SKILL.md`, `.github/skills/<name>/SKILL.md` — see `.gemini/skills/skills-index/SKILL.md` for the pairing map). When a hygiene fix changes a skill's body, apply the same fix to all paired copies so they stay identical (frontmatter `name`/`description` may differ per tree's own convention; the body should not). `scripts/check_skill_pairs.py`'s `GROUPS` list only flags when some-but-not-all paired files changed in a diff — it doesn't check the bodies actually match, so a manual diff after editing is still worth it.
