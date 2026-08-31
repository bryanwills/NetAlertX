#!/usr/bin/env python3
"""
Flag PRs that touch one half of a paired .gemini/.github skill file without
touching the other. `.gemini/skills/skills-index/SKILL.md` documents these
pairs and says to "keep body content identical between both files" - but
nothing previously enforced that, and the plugin-development pair had
already drifted apart before this check existed.

This can't verify the two files still say the *same thing* (that needs
judgment - some pairs are intentionally different in depth), only that a
change to one side didn't forget the other exists. Exit non-zero (but the
CI step calling this is non-blocking) when a pair looks one-sided.

    python3 scripts/check_skill_pairs.py origin/main
"""

import subprocess
import sys

# Kept in sync with the tables in .gemini/skills/skills-index/SKILL.md and
# .github/skills/skills-overview/SKILL.md.
PAIRS = [
    (".gemini/skills/plugin-development/plugin-skill.md", ".github/skills/plugin-run-development/SKILL.md"),
    (".gemini/skills/testing-workflow/SKILL.md", ".github/skills/testing-workflow/SKILL.md"),
    (".gemini/skills/settings/SKILL.md", ".github/skills/settings-management/SKILL.md"),
    (".gemini/skills/mcp-activation/SKILL.md", ".github/skills/mcp-activation/SKILL.md"),
    (".gemini/skills/project-navigation/SKILL.md", ".github/skills/project-navigation/SKILL.md"),
    (".gemini/skills/pr-analysis/SKILL.md", ".github/skills/pr-analysis/SKILL.md"),
    (".gemini/skills/logging-standards/SKILL.md", ".github/skills/logging-standards/SKILL.md"),
    (".gemini/skills/devcontainer-management/SKILL.md", ".github/skills/devcontainer-services/SKILL.md"),
    (".gemini/skills/devcontainer-management/SKILL.md", ".github/skills/devcontainer-setup/SKILL.md"),
    (".gemini/skills/devcontainer-management/SKILL.md", ".github/skills/devcontainer-configs/SKILL.md"),
]


def changed_files(base_ref):
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        capture_output=True, text=True, check=True,
    )
    return set(result.stdout.splitlines())


def main():
    if len(sys.argv) != 2:
        print("usage: check_skill_pairs.py <base-ref>", file=sys.stderr)
        return 2

    changed = changed_files(sys.argv[1])
    problems = []
    for gemini_path, github_path in PAIRS:
        gemini_changed = gemini_path in changed
        github_changed = github_path in changed
        if gemini_changed != github_changed:
            touched, untouched = (gemini_path, github_path) if gemini_changed else (github_path, gemini_path)
            problems.append(f"- {touched} changed but its pair {untouched} wasn't.")

    if problems:
        print("Possible skill-pair drift (only one side of a pair was touched):")
        print("\n".join(problems))
        print("\nIf the change is Gemini/Copilot-specific on purpose, ignore this. "
              "Otherwise update both sides - see .gemini/skills/skills-index/SKILL.md.")
        return 1

    print("No skill-pair drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
