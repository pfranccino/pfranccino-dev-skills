#!/usr/bin/env python3
"""Identify the change under review, so a verdict can be tied to exactly that change.

    python3 review_target.py              # the working tree: staged, unstaged and untracked changes
    python3 review_target.py main...HEAD  # a commit range

Prints JSON with `source_revision` (HEAD), `target` and `diff_hash`: a SHA-256 of the diff against
HEAD (or of the range's diff) plus, for the working tree, the length-prefixed path and content of each
untracked file outside build/android-feature-kit/, where the develop flow keeps its own files. Run it before each review round and again before accepting a READY verdict: a different
`diff_hash` means the reviewed change is no longer the current one.

Standard library only, Python 3.8+. Run it from the repository root.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys

WORKFLOW_DIR = "build/android-feature-kit/"  # the flow's own files (scope, review prompts and answers) are not the change


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def main(argv: list[str]) -> int:
    target = argv[0] if argv else "working-tree"
    try:
        head = git("rev-parse", "HEAD").decode().strip()
        digest = hashlib.sha256()
        untracked: list[str] = []
        if target == "working-tree":
            digest.update(git("diff", "HEAD", "--binary"))
            listed = git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
            untracked = [p for p in listed if p and not p.startswith(WORKFLOW_DIR)]
            for path in untracked:
                with open(path, "rb") as handle:
                    content = handle.read()
                name = path.encode()
                digest.update(len(name).to_bytes(8, "big") + name + len(content).to_bytes(8, "big") + content)
        else:
            digest.update(git("diff", "--binary", target))
    except (subprocess.CalledProcessError, OSError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps({"source_revision": head, "target": target, "diff_hash": digest.hexdigest(),
                      "untracked_files": untracked}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
