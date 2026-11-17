#!/usr/bin/env python3
"""Run a Gradle command and print a short JSON summary of what failed.

    python tools/agent-checks/gradle_summary.py [--out DIR] [--max N] -- ./gradlew :feature:orders:compileDebugKotlin

The full log is saved to a file (`raw_log_path` in the summary); the summary lists failed tasks
and compiler or resource errors as file, line and message. Agents and people read the summary;
the raw log stays available as evidence. The script exits with the command's own exit code. When
the command fails and nothing could be parsed, `failures` is empty and `note` says to read the log.

Standard library only, Python 3.8+.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import re
import subprocess
import sys
import uuid
from urllib.parse import unquote, urlparse

SCRIPT_VERSION = "1"

TASK_FAILED = re.compile(r"^> Task (\S+) FAILED\s*$")
# File paths may contain spaces (C:/Users/Paul Ayala/...), so each pattern anchors on the location suffix.
KOTLIN_NEW = re.compile(r"^(?P<level>[ew]): (?P<file>.+?\.(?:kts?|java)):(?P<line>\d+):(?P<col>\d+) (?P<msg>.+)$")
KOTLIN_OLD = re.compile(r"^(?P<level>[ew]): (?P<file>.+?\.kts?): \((?P<line>\d+), (?P<col>\d+)\): (?P<msg>.+)$")
KSP = re.compile(r"^(?P<level>[ew]): \[ksp\] (?P<file>.+?\.(?:kts?|java)):(?P<line>\d+): (?P<msg>.+)$")
JAVA = re.compile(r"^(?P<file>.+?\.java):(?P<line>\d+): (?P<level>error|warning): (?P<msg>.+)$")
AAPT = re.compile(r"^(?:ERROR:\s*)?(?P<file>.+?\.xml):(?P<line>\d+):?\s*(?:AAPT: )?(?:error|ERROR): (?P<msg>.+)$")
TEST_FAILED = re.compile(r"^(?P<cls>[\w.$]+) > (?P<name>.+) FAILED\s*$")
TASK_HEADER = re.compile(r"^> Task (\S+)")


def to_path(raw: str, root: str) -> str:
    if raw.startswith("file:"):
        parsed = urlparse(raw)
        raw = unquote(parsed.path)
        if re.match(r"^/[A-Za-z]:", raw):
            raw = raw[1:]
    path = raw.replace("\\", "/")
    base = root.replace("\\", "/").rstrip("/") + "/"
    if path.lower().startswith(base.lower()):
        path = path[len(base):]
    return path


def source_revision(root: str) -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    head = git("rev-parse", "HEAD")
    return {"head": head or None, "dirty": bool(git("status", "--porcelain")) if head else None}


def parse(log: str, root: str, limit: int) -> dict:
    failures, warnings, failed_tasks, failed_tests = [], [], [], []
    what_went_wrong, current_task = [], None
    lines = log.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        header = TASK_HEADER.match(line)
        if header:
            current_task = header.group(1)
        failed = TASK_FAILED.match(line)
        if failed:
            failed_tasks.append(failed.group(1))
        match, kind = KSP.match(line), "ksp"
        if not match:
            match, kind = KOTLIN_NEW.match(line) or KOTLIN_OLD.match(line), "kotlin"
        if not match:
            match, kind = JAVA.match(line), "java"
        if not match:
            match, kind = AAPT.match(line), "resource"
        if match:
            level = match.groupdict().get("level", "e")
            entry = {
                "kind": kind,
                "task": current_task,
                "file": to_path(match.group("file"), root),
                "line": int(match.group("line")),
                "column": int(match.group("col")) if "col" in match.groupdict() and match.group("col") else None,
                "message": match.group("msg").strip(),
            }
            (warnings if level in ("w", "warning") else failures).append(entry)
        test = TEST_FAILED.match(line)
        if test:
            failed_tests.append(f"{test.group('cls')} > {test.group('name')}")
        if line.strip() == "* What went wrong:":
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("* Try:"):
                what_went_wrong.append(lines[i].rstrip())
                i += 1
            continue
        i += 1
    return {
        "failed_tasks": failed_tasks,
        "failures": failures[:limit],
        "failures_total": len(failures),
        "failed_tests": failed_tests[:limit],
        "failed_tests_total": len(failed_tests),
        "warnings": {"count": len(warnings), "first": warnings[:5]},
        "what_went_wrong": "\n".join(what_went_wrong[:30]) or None,
    }


def main(argv: list[str]) -> int:
    if "--" not in argv:
        print("usage: gradle_summary.py [--out DIR] [--max N] -- <gradle command>", file=sys.stderr)
        return 64
    split = argv.index("--")
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--out", default=os.path.join("build", "agent-checks"))
    parser.add_argument("--max", type=int, default=20)
    options = parser.parse_args(argv[:split])
    command = argv[split + 1:]
    if not command:
        print("gradle_summary.py: no command after --", file=sys.stderr)
        return 64
    root = os.getcwd()
    os.makedirs(options.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(options.out, f"gradle-{stamp}-{os.getpid()}-{uuid.uuid4().hex[:8]}.log")
    run_command = command
    if os.name == "nt" and command[0].replace("\\", "/").rsplit("/", 1)[-1].lower() in ("gradlew", "gradlew.bat"):
        run_command = [os.path.join(root, "gradlew.bat"), *command[1:]]
    try:
        result = subprocess.run(run_command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = result.stdout.decode("utf-8", errors="replace")
        exit_code = result.returncode
    except OSError as error:
        output, exit_code = f"Could not start {command[0]}: {error}", 127
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(output)
    parsed = parse(output, root, options.max)
    summary = {
        "schema_version": 1,
        "source_revision": source_revision(root),
        "command": command,
        "tool_versions": {"gradle_summary": SCRIPT_VERSION, "python": platform.python_version()},
        "status": "passed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        **parsed,
        "raw_log_path": to_path(os.path.abspath(log_path), root),
        "note": None,
    }
    if exit_code != 0 and not parsed["failures"] and not parsed["failed_tests"]:
        summary["note"] = "The command failed and no error lines were recognized. Read raw_log_path."
    elif parsed["failed_tests"]:
        summary["note"] = "Tests failed. Run test_summary.py on the module for assertions and locations."
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
