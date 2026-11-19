#!/usr/bin/env python3
"""Run a Gradle command and print a short JSON summary of what failed.

    python tools/agent-checks/gradle_summary.py [--out DIR] [--max N] [--timeout MIN] -- ./gradlew :feature:orders:compileDebugKotlin

The full log is saved to a file (`raw_log_path` in the summary); the summary lists failed tasks
and compiler or resource errors as file, line and message. Agents and people read the summary;
the raw log stays available as evidence. The script exits with the command's own exit code. When
the command fails and nothing could be parsed, `failures` is empty and `note` says to read the log.

When the command is a bare `./gradlew` and the current folder has none, the script looks for it in
the parent folders, up to the repository root, and runs Gradle from the folder where it found it.
A wrapper path such as `./android/gradlew` runs as given.

`--timeout` stops the command and its child processes after that many minutes; the summary then has
`status: "timeout"` and the script exits with 124. Connected tasks (`connected*`) stop after 9
minutes unless `--timeout` says otherwise, so a device that never answers ends with a summary before
a 10-minute shell call does. `--timeout 0` turns the limit off.

Before connected tasks, the script checks the device with adb (the SDK's, from local.properties,
ANDROID_HOME or ANDROID_SDK_ROOT, else the PATH): at least one device in the `device` state, or the
one ANDROID_SERIAL names, that has finished booting. When none is ready, Gradle does not run: the
summary says `status: "device_unavailable"` with what adb reported in `device_check`, and the script
exits with 125. It also warns when adb is older than the device's Android version. It never restarts
adb: that disconnects Android Studio and other sessions, so the note proposes it and the user
decides. `--no-device-check` skips the check; without adb it is skipped with a note.

`next_step` names the kit agent that diagnoses the result: `test-analyst` when only test tasks
failed, `build-doctor` for every other failure, a timeout or an unavailable device, and null when
the command passed.

Standard library only, Python 3.8+.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from urllib.parse import unquote, urlparse

SCRIPT_VERSION = "2"
SCHEMA_VERSION = 2
CONNECTED_TIMEOUT_MINUTES = 9.0
EXTERNAL_STOP_GRACE_SECONDS = 5
TIMEOUT_EXIT_CODE = 124
DEVICE_EXIT_CODE = 125
ADB_TIMEOUT_SECONDS = 20
ADB_VERSION = re.compile(r"Version (\d+)\.\S*")
WRAPPERS = ("gradlew", "gradlew.bat")
WRAPPER = "gradlew.bat" if os.name == "nt" else "gradlew"
TEST_TASK = re.compile(r"^(?:test|connected\w*|\w*UnitTest|\w*AndroidTest)$", re.IGNORECASE)

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


def is_wrapper(word: str) -> bool:
    return word.replace("\\", "/").rsplit("/", 1)[-1].lower() in WRAPPERS


def find_wrapper_root(start: str) -> str | None:
    """The nearest folder, from `start` up to the repository root, that holds this platform's Gradle wrapper."""
    folder = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(folder, WRAPPER)):
            return folder
        parent = os.path.dirname(folder)
        if os.path.exists(os.path.join(folder, ".git")) or parent == folder:
            return None
        folder = parent


def resolve_wrapper(word: str, cwd: str) -> tuple[str, str]:
    """The wrapper to run, and the folder to run Gradle from.

    A wrapper path that exists runs from the current folder, as given (gradlew.bat next to it on Windows). Only a bare
    `gradlew` or `./gradlew` that the current folder lacks is looked up in the parent folders, up to the repository
    root, and then Gradle runs from the folder where it was found.
    """
    path = word.replace("\\", "/")
    folder = os.path.dirname(os.path.abspath(os.path.join(cwd, path)))
    if os.path.isfile(os.path.join(folder, WRAPPER)):
        return os.path.join(folder, WRAPPER), cwd
    found = find_wrapper_root(cwd) if os.path.dirname(path) in ("", ".") else None
    if found:
        return os.path.join(found, WRAPPER), found
    return os.path.join(folder, WRAPPER), cwd


def is_connected(command: list[str]) -> bool:
    """Whether the command runs a connected task (`connected*`), which needs a device."""
    tasks = [word.rsplit(":", 1)[-1].lower() for word in command[1:] if not word.startswith("-")]
    return any(task.startswith("connected") for task in tasks)


def default_timeout(command: list[str]) -> float | None:
    return CONNECTED_TIMEOUT_MINUTES if is_connected(command) else None


def sdk_dirs(root: str) -> list[str]:
    """The Android SDK folders Gradle would use, in order: local.properties, ANDROID_HOME, ANDROID_SDK_ROOT."""
    dirs = []
    try:
        with open(os.path.join(root, "local.properties"), encoding="utf-8") as handle:
            for line in handle:
                key, _, value = line.partition("=")
                if key.strip() == "sdk.dir" and value.strip():
                    dirs.append(value.strip().replace("\\:", ":").replace("\\\\", "\\"))
    except OSError:
        pass
    return dirs + [os.environ[name] for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT") if os.environ.get(name)]


def find_adb(root: str) -> str | None:
    name = "adb.exe" if os.name == "nt" else "adb"
    for sdk in sdk_dirs(root):
        path = os.path.join(sdk, "platform-tools", name)
        if os.path.isfile(path):
            return path
    return shutil.which("adb")


def adb_call(adb: str, *args: str, serial: str | None = None) -> tuple[int | None, str]:
    """Run adb with a time limit; return its exit code (None when it did not answer) and its output."""
    command = [adb, *(["-s", serial] if serial else []), *args]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=ADB_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return None, f"adb {' '.join(args)} did not answer in {ADB_TIMEOUT_SECONDS} seconds"
    except OSError as error:
        return None, f"could not run adb: {error}"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def parse_devices(text: str) -> list[dict]:
    devices = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("List of devices", "*", "adb ")):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append({"serial": parts[0], "state": parts[1]})
    return devices


def check_devices(root: str, call=adb_call, adb: str | None = None) -> dict:
    """Whether a device is ready for connected tasks. Reads only; it never restarts adb or the emulator."""
    adb = adb or find_adb(root)
    if not adb:
        return {"result": "skipped", "problem": None, "warnings": [],
                "note": "adb was not found in the SDK (local.properties, ANDROID_HOME) or on the PATH; no device check."}
    check = {"result": "passed", "adb": adb.replace("\\", "/"), "adb_version": None, "devices": [], "problem": None,
             "warnings": [], "output": []}
    _, version_text = call(adb, "version")
    version = ADB_VERSION.search(version_text or "")
    check["adb_version"] = version.group(0).split(" ", 1)[1] if version else None
    code, devices_text = call(adb, "devices")
    check["output"].append(devices_text.strip())
    if code != 0:
        check.update(result="failed", problem=f"adb devices failed: {devices_text.strip()[:300]}")
        return check
    devices = parse_devices(devices_text)
    wanted = os.environ.get("ANDROID_SERIAL")
    if wanted:
        devices = [d for d in devices if d["serial"] == wanted] or [{"serial": wanted, "state": "not connected"}]
    for device in devices:
        if device["state"] == "device":
            _, boot = call(adb, "shell", "getprop", "sys.boot_completed", serial=device["serial"])
            _, sdk = call(adb, "shell", "getprop", "ro.build.version.sdk", serial=device["serial"])
            device["boot_completed"] = boot.strip() == "1"
            device["sdk"] = int(sdk.strip()) if sdk.strip().isdigit() else None
    check["devices"] = devices
    ready = [d for d in devices if d["state"] == "device" and d.get("boot_completed")]
    if not devices:
        check["problem"] = "no device or emulator is connected"
    elif not ready:
        states = ", ".join(f"{d['serial']} is {'still booting' if d['state'] == 'device' else d['state']}"
                           for d in devices)
        check["problem"] = f"no device is ready: {states}"
    major = int(version.group(1)) if version else None
    newest = max((d.get("sdk") or 0 for d in devices), default=0)
    if major and newest and major < newest:
        check["warnings"].append(f"adb {check['adb_version']} is older than the device's API {newest}; an older adb "
                                 "can leave a newer emulator offline. Update platform-tools.")
    if check["problem"]:
        check["result"] = "failed"
    return check


def device_note(check: dict) -> str:
    version = f" (this adb is {check['adb_version']})" if check.get("adb_version") else ""
    return (f"Gradle did not run: {check['problem']}. Usual fixes, which the user decides, because restarting adb "
            "disconnects Android Studio and other sessions: `adb kill-server` then `adb start-server`; start or unlock "
            f"the emulator and wait until it finishes booting; accept the debugging prompt on a device; update "
            f"platform-tools{version}.")


def stop_tree(process: subprocess.Popen) -> None:
    """Stop the command and every process it started. A Gradle daemon that was already running is not one of them.

    On Windows, taskkill /T stops the process tree (gradlew.bat runs cmd.exe, which starts the Gradle client).
    Elsewhere the command runs in its own process group: SIGTERM to the group, then SIGKILL to what is left.
    """
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    else:
        signal_group(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
    if os.name != "nt":
        signal_group(process.pid, signal.SIGKILL)
    process.wait()


def signal_group(group: int, signum: int) -> None:
    try:
        os.killpg(group, signum)
    except OSError:
        pass  # the group is already gone


def group_alive(group: int) -> bool:
    try:
        os.killpg(group, 0)
        return True
    except OSError:
        return False


def stop_group(group: int, grace: float) -> None:
    """SIGTERM to the group, then SIGKILL to whatever is left after `grace` seconds."""
    signal_group(group, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline and group_alive(group):
        time.sleep(0.2)
    signal_group(group, signal.SIGKILL)


def forward_signals(group: int) -> dict:
    """If this script is stopped (the shell call times out, or someone presses Ctrl+C), stop the command's group too."""
    def handler(signum, _frame):
        stop_group(group, EXTERNAL_STOP_GRACE_SECONDS)
        raise SystemExit(128 + signum)
    return {signum: signal.signal(signum, handler) for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}


def run(run_command: list[str], root: str, log_path: str, minutes: float | None) -> tuple[int, bool]:
    """Run the command with its output going to the log; return its exit code and whether it timed out."""
    with open(log_path, "wb") as log:
        try:
            process = subprocess.Popen(run_command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=os.name != "nt")
        except OSError as error:
            log.write(f"Could not start {run_command[0]}: {error}".encode("utf-8"))
            return 127, False
        previous = forward_signals(process.pid) if os.name != "nt" else {}
        try:
            return process.wait(timeout=minutes * 60 if minutes else None), False
        except subprocess.TimeoutExpired:
            stop_tree(process)
            log.seek(0, os.SEEK_END)
            log.write(f"\n[gradle_summary] Stopped after {minutes:g} minutes (--timeout).\n".encode("utf-8"))
            return TIMEOUT_EXIT_CODE, True
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)


def is_test_task(task: str) -> bool:
    return bool(TEST_TASK.match(task.rsplit(":", 1)[-1]))


def next_step(status: str, parsed: dict) -> str | None:
    """test-analyst only when every failed task runs tests and no compiler or resource error came up."""
    if status == "passed":
        return None
    only_tests = (status == "failed" and parsed["failed_tests_total"] > 0 and parsed["failures_total"] == 0
                  and parsed["failed_tasks"] and all(is_test_task(task) for task in parsed["failed_tasks"]))
    return "test-analyst" if only_tests else "build-doctor"


def main(argv: list[str]) -> int:
    if "--" not in argv:
        print("usage: gradle_summary.py [--out DIR] [--max N] [--timeout MIN] -- <gradle command>", file=sys.stderr)
        return 64
    split = argv.index("--")
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--out", default=os.path.join("build", "agent-checks"))
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=None, help="minutes; 0 turns the limit off")
    parser.add_argument("--no-device-check", action="store_true", help="skip the adb check before connected tasks")
    options = parser.parse_args(argv[:split])
    command = argv[split + 1:]
    if not command:
        print("gradle_summary.py: no command after --", file=sys.stderr)
        return 64
    root = os.getcwd()
    run_command = command
    if is_wrapper(command[0]):
        wrapper, root = resolve_wrapper(command[0], root)
        run_command = [wrapper, *command[1:]]
    minutes = default_timeout(command) if options.timeout is None else (options.timeout or None)
    out = options.out if os.path.isabs(options.out) else os.path.join(root, options.out)
    os.makedirs(out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(out, f"gradle-{stamp}-{os.getpid()}-{uuid.uuid4().hex[:8]}.log")
    check = check_devices(root) if is_connected(command) and not options.no_device_check else None
    if check and check["result"] == "failed":
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write(f"[gradle_summary] Device check before {' '.join(command)}\n{json.dumps(check, indent=2)}\n")
        summary = {
            "schema_version": SCHEMA_VERSION,
            "source_revision": source_revision(root),
            "command": command,
            "working_directory": root.replace("\\", "/"),
            "tool_versions": {"gradle_summary": SCRIPT_VERSION, "python": platform.python_version()},
            "status": "device_unavailable",
            "exit_code": DEVICE_EXIT_CODE,
            "next_step": "build-doctor",
            "raw_log_path": to_path(os.path.abspath(log_path), root),
            "device_check": check,
            **parse("", root, options.max),
            "note": device_note(check),
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return DEVICE_EXIT_CODE
    exit_code, timed_out = run(run_command, root, log_path, minutes)
    with open(log_path, "rb") as handle:
        output = handle.read().decode("utf-8", errors="replace")
    parsed = parse(output, root, options.max)
    status = "timeout" if timed_out else "passed" if exit_code == 0 else "failed"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "source_revision": source_revision(root),
        "command": command,
        "working_directory": root.replace("\\", "/"),
        "tool_versions": {"gradle_summary": SCRIPT_VERSION, "python": platform.python_version()},
        "status": status,
        "exit_code": exit_code,
        "next_step": next_step(status, parsed),  # near the top, so it survives when long output is cut
        "raw_log_path": to_path(os.path.abspath(log_path), root),
        "timeout_minutes": minutes,
        "device_check": check,
        **parsed,
        "note": None,
    }
    if timed_out:
        summary["note"] = (f"The command did not finish in {minutes:g} minutes and was stopped. A hang during connected "
                           "tests is usually the device or adb (offline, an install that never ends). Read the end of "
                           "raw_log_path.")
    elif exit_code != 0 and not parsed["failures"] and not parsed["failed_tests"]:
        summary["note"] = "The command failed and no error lines were recognized. Read raw_log_path."
    elif parsed["failed_tests"]:
        summary["note"] = "Tests failed. Run test_summary.py on the module for assertions and locations."
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
