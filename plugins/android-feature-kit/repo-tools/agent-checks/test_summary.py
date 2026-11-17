#!/usr/bin/env python3
"""Summarize failing tests from JUnit XML reports as JSON.

    python tools/agent-checks/test_summary.py [--module feature/orders] [--results DIR ...] [--max N]

Reads the XML reports Gradle writes (`build/test-results/**` for unit tests and
`build/outputs/androidTest-results/**` for instrumented tests) under the module, or under the
given result folders. For each failing test it reports the class, the test, the failure type and
message, and the first stack frame in the project's own code. Exit code: 0 when every test
passed, 1 when some failed, 2 when no reports were found or some could not be read.

Standard library only, Python 3.8+.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

SCRIPT_VERSION = "1"
FRAME = re.compile(r"^\s*at ([\w.$<>]+)\.([\w$<>-]+)\(([\w$.-]+\.(?:kt|java)):(\d+)\)")
LIBRARY_PREFIXES = (
    "java.", "javax.", "jdk.", "sun.", "kotlin.", "kotlinx.", "org.junit.", "junit.", "org.gradle.",
    "androidx.test.", "app.cash.turbine.", "io.mockk.", "org.mockito.", "com.google.common.truth.",
    "org.assertj.", "org.hamcrest.", "worker.org.gradle.", "dalvik.", "android.", "com.android.",
)


def source_revision(root: str) -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    head = git("rev-parse", "HEAD")
    return {"head": head or None, "dirty": bool(git("status", "--porcelain")) if head else None}


def report_files(bases: list[str]) -> list[str]:
    files = []
    for base in bases:
        for pattern in ("**/build/test-results/**/*.xml", "**/build/outputs/androidTest-results/**/*.xml", "**/*.xml"):
            if pattern == "**/*.xml" and "test-results" not in base.replace("\\", "/") and "androidTest-results" not in base.replace("\\", "/"):
                continue
            files.extend(glob.glob(os.path.join(base, pattern), recursive=True))
    return sorted(set(files))


def first_own_frame(text: str, search_root: str) -> dict | None:
    for line in text.splitlines():
        match = FRAME.match(line)
        if not match or match.group(1).startswith(LIBRARY_PREFIXES):
            continue
        file_name, line_number = match.group(3), int(match.group(4))
        candidates = glob.glob(os.path.join(search_root, "**", "src", "**", file_name), recursive=True)
        path = candidates[0].replace("\\", "/") if len(candidates) == 1 else None
        return {"class": match.group(1), "method": match.group(2), "file": path or file_name, "line": line_number}
    return None


def summarize(files: list[str], search_root: str, limit: int) -> dict:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    failures, unreadable = [], []
    for path in files:
        try:
            root = ElementTree.parse(path).getroot()
        except (ElementTree.ParseError, OSError) as error:
            unreadable.append({"report": path.replace("\\", "/"), "error": str(error)[:200]})
            continue
        for case in root.iter("testcase"):  # every testcase once, however the suites are nested
            totals["tests"] += 1
            if case.find("skipped") is not None:
                totals["skipped"] += 1
            for tag in ("failure", "error"):
                node = case.find(tag)
                if node is None:
                    continue
                totals["failures" if tag == "failure" else "errors"] += 1
                text = (node.text or "").strip()
                message = node.get("message") or (text.splitlines()[0] if text else "")
                failures.append({
                    "class": case.get("classname"),
                    "test": case.get("name"),
                    "kind": tag,
                    "type": node.get("type"),
                    "message": message.strip()[:400],
                    "location": first_own_frame(text, search_root),
                    "report": path.replace("\\", "/"),
                })
    return {"totals": totals, "failures": failures[:limit], "failures_total": len(failures), "unreadable": unreadable}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--module", default=".")
    parser.add_argument("--results", action="append", default=[])
    parser.add_argument("--max", type=int, default=20)
    options = parser.parse_args(argv)
    root = os.getcwd()
    files = report_files(options.results or [options.module])
    result = summarize(files, options.module, options.max)
    if not files or len(result["unreadable"]) == len(files):
        status, exit_code = "no_results", 2
    elif result["failures_total"]:
        status, exit_code = "failed", 1
    elif result["unreadable"]:
        status, exit_code = "incomplete", 2
    else:
        status, exit_code = "passed", 0
    summary = {
        "schema_version": 1,
        "source_revision": source_revision(root),
        "command": None,
        "tool_versions": {"test_summary": SCRIPT_VERSION, "python": platform.python_version()},
        "status": status,
        "exit_code": exit_code,
        **result,
        "reports_scanned": len(files),
        "note": "No JUnit XML reports found. Run the tests first, or pass --results." if not files else
                "Some reports could not be read (see unreadable); the result does not cover them." if result["unreadable"] else
                "Reports from earlier runs are included; check the report paths if a failure looks stale.",
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
