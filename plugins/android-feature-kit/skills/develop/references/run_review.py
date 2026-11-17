#!/usr/bin/env python3
"""Run one round of the external reviewer configured for android-feature-kit, and check its answer.

The reviewer is any command-line tool set in `.claude/android-feature-kit.json` of the repository:

    {"reviewer": {"name": "Codex",
                  "command": ["codex", "exec", "-s", "read-only", "--output-schema", "{schema}", "-o", "{output}", "-"]}}

The command runs from the repository root with the round's prompt on standard input. `{schema}`, `{output}` and
`{prompt_file}` in its arguments become the schema path, the answer path and the prompt path. Without `{output}`,
the answer is read from standard output.

The answer must follow review.schema.json (next to this script) and repeat the target identity given here.
The script prints a JSON summary. Exit codes: 0 valid answer, 1 the tool failed or its answer is not valid,
2 no reviewer configured, the command was not found, or bad arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = "android-feature-kit"
SCHEMA_PATH = Path(__file__).resolve().parent / "review.schema.json"
REVIEW_DIR = Path("build") / PLUGIN / "review"
DEFAULT_TIMEOUT = 1800
IDENTITY = ("run_id", "round", "source_revision", "diff_hash", "rules_version")
TYPES = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}


def validate(value, schema: dict, path: str = "$") -> list[str]:
    """Problems with `value` against the subset of JSON Schema that review.schema.json uses."""
    expected = schema.get("type")
    if expected:
        python_type = TYPES[expected]
        if not isinstance(value, python_type) or (expected == "integer" and isinstance(value, bool)):
            return [f"{path} must be {expected}"]
    problems = []
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path} must be one of {', '.join(map(str, schema['enum']))}")
    if expected == "object":
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                problems.append(f"{path}.{name} is missing")
        for name, item in value.items():
            if name in properties:
                problems.extend(validate(item, properties[name], f"{path}.{name}"))
            elif schema.get("additionalProperties") is False:
                problems.append(f"{path}.{name} is not allowed")
    if expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            problems.extend(validate(item, schema["items"], f"{path}[{index}]"))
    return problems


def parse_answer(text: str):
    """The JSON object in a tool's output: the whole text, a ```json block, or the outermost braces."""
    text = text.strip()
    candidates = [text]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates.extend(reversed(fenced))
    if "{" in text and "}" in text:
        candidates.append(text[text.index("{"):text.rindex("}") + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def load_reviewer(config_path: Path) -> tuple[dict | None, str | None]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError:
        return None, f"{config_path} does not exist: no external reviewer is configured."
    except ValueError as error:
        return None, f"{config_path} is not valid JSON: {error}"
    reviewer = config.get("reviewer") if isinstance(config, dict) else None
    if not isinstance(reviewer, dict):
        return None, f"{config_path} has no \"reviewer\" object: no external reviewer is configured."
    command = reviewer.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
        return None, f"\"reviewer.command\" in {config_path} must be a non-empty list of strings."
    timeout = reviewer.get("timeout_seconds", DEFAULT_TIMEOUT)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        return None, f"\"reviewer.timeout_seconds\" in {config_path} must be a positive integer."
    return {"name": str(reviewer.get("name") or command[0]), "command": command, "timeout": timeout}, None


def summary(status: str, **fields) -> dict:
    return {"status": status, **fields}


def run(args: argparse.Namespace) -> tuple[int, dict]:
    reviewer, problem = load_reviewer(Path(args.config))
    if reviewer is None:
        return 2, summary("not_configured", problems=[problem])

    review_dir = REVIEW_DIR
    prompt = Path(args.prompt) if args.prompt else review_dir / f"round-{args.round}-prompt.md"
    if not prompt.is_file():
        return 2, summary("error", problems=[f"The prompt {prompt} does not exist; write it first."])
    output = review_dir / f"round-{args.round}.json"
    log = review_dir / f"round-{args.round}.log"
    review_dir.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    values = {"{schema}": str(SCHEMA_PATH), "{output}": str(output.resolve()), "{prompt_file}": str(prompt.resolve())}
    command = list(reviewer["command"])
    for index, part in enumerate(command):
        for placeholder, value in values.items():
            part = part.replace(placeholder, value)
        command[index] = part
    executable = shutil.which(command[0])
    if executable is None:
        return 2, summary("error", reviewer=reviewer["name"],
                          problems=[f"The reviewer command '{command[0]}' was not found on the PATH."])
    command[0] = executable

    base = {"reviewer": reviewer["name"], "answer_path": output.as_posix(), "log_path": log.as_posix()}
    try:
        with prompt.open("rb") as stdin:
            result = subprocess.run(command, stdin=stdin, capture_output=True, timeout=reviewer["timeout"])
    except subprocess.TimeoutExpired:
        return 1, summary("failed", **base, problems=[f"The reviewer did not finish in {reviewer['timeout']} seconds."])
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    log.write_text(f"$ {' '.join(command)}\nexit code: {result.returncode}\n\n--- stdout\n{stdout}\n--- stderr\n{stderr}",
                   encoding="utf-8")
    if result.returncode != 0:
        return 1, summary("failed", **base, problems=[f"The reviewer exited with code {result.returncode}; see the log."])

    uses_output = any("{output}" in part for part in reviewer["command"])
    if uses_output:
        if not output.is_file():
            return 1, summary("failed", **base, problems=["The reviewer wrote no answer file."])
        answer = parse_answer(output.read_text(encoding="utf-8", errors="replace"))
    else:
        answer = parse_answer(stdout)
    if answer is None:
        return 1, summary("invalid", **base, problems=["The reviewer's answer has no JSON object."])
    output.write_text(json.dumps(answer, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    problems = validate(answer, schema)
    expected = {"run_id": args.run_id, "round": args.round, "source_revision": args.source_revision,
                "diff_hash": args.diff_hash, "rules_version": args.rules_version}
    for name in IDENTITY:
        if name in answer and answer[name] != expected[name]:
            problems.append(f"{name} is {answer[name]!r}, expected {expected[name]!r}")
    fields = dict(base, verdict=answer.get("verdict"),
                  findings=len(answer["findings"]) if isinstance(answer.get("findings"), list) else None)
    if problems:
        return 1, summary("invalid", **fields, problems=problems)
    return 0, summary("ok", **fields, problems=[])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--diff-hash", required=True)
    parser.add_argument("--rules-version", required=True)
    parser.add_argument("--prompt", help="the prompt file (default: build/android-feature-kit/review/round-<n>-prompt.md)")
    parser.add_argument("--config", default=os.path.join(".claude", f"{PLUGIN}.json"))
    args = parser.parse_args(argv)
    code, result = run(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
