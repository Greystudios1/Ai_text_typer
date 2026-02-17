#!/usr/bin/env python3
"""Safely fast-forward update a git repo without crashing on missing upstream/remote."""

from __future__ import annotations

import subprocess
import sys
from typing import Optional


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        text=True,
        capture_output=True,
    )


def git_output(*args: str) -> Optional[str]:
    try:
        cp = run_git(*args)
    except subprocess.CalledProcessError:
        return None
    return cp.stdout.strip()


def main() -> int:
    if git_output("rev-parse", "--is-inside-work-tree") != "true":
        print("[update-skip] Not inside a git work tree; nothing to update.")
        return 0

    branch = git_output("rev-parse", "--abbrev-ref", "HEAD")
    if not branch or branch == "HEAD":
        print("[update-skip] Detached HEAD; skipping pull.")
        return 0

    remotes = git_output("remote")
    if not remotes:
        print("[update-skip] No git remote configured; skipping pull.")
        return 0

    run_git("fetch", "--all", "--prune", check=False)

    upstream = git_output("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if not upstream:
        candidate = f"origin/{branch}"
        if git_output("show-ref", "--verify", f"refs/remotes/{candidate}"):
            run_git("branch", "--set-upstream-to", candidate, branch, check=False)
            upstream = git_output("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")

    if not upstream:
        print("[update-skip] Branch has no upstream tracking branch; skipping pull.")
        return 0

    try:
        cp = run_git("pull", "--ff-only")
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        print("[update-error] git pull --ff-only failed.")
        if stderr:
            print(f"[update-error] {stderr}")
        return exc.returncode or 1

    out = (cp.stdout or "").strip()
    if out:
        print(out)
    print("[update-ok] Repository is up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
