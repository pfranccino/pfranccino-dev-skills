#!/usr/bin/env python3
"""Points the main session to the kit's diagnosis agents when a check fails.

Claude Code runs this script after Bash and PowerShell calls (PostToolUse and PostToolUseFailure) and after Agent
calls (PostToolUse). A shell command that exits with a code other than 0 is a failed tool call for Claude Code, so a
failing check arrives as PostToolUseFailure, with the command's output in `error` instead of `tool_response`.

- Shell: when the command ran gradle_summary.py or test_summary.py and the summary says the check failed or timed
  out, the script adds a note for Claude that names the agent that diagnoses it (the summary's `next_step`) and the
  summary's log. When gradle_summary.py ended without a summary (the shell call itself timed out), it names
  build-doctor.
- Agent: when one of the kit's writing agents replies with STATUS failed or blocked and its CHECKS report a failure,
  the script adds the same kind of note.

The note launches nothing. It tells Claude to call the agent now when the plan it follows approves diagnosis (the
Checks line of a develop plan), and to propose it to the user otherwise, before investigating the failure itself.
Calls made inside a subagent pass untouched: a layer agent fixes its own failures first, and the main session sees
what is left in its reply. Checks run in the background are not covered: their result arrives as a notification,
not as a tool call.

The script always exits 0; the note goes out as `additionalContext`.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

from layer_guard import PLUGIN, PYTHON_PROGRAMS, basename, is_operator, kit_agent_name, program_of

SHELL_TOOLS = {"Bash", "PowerShell"}
AGENT_TOOLS = {"Agent", "Task"}
WRITING_AGENTS = {"domain-builder", "data-builder", "ui-builder", "feature-integrator"}
DIAGNOSIS_MODELS = {"build-doctor": "haiku", "test-analyst": "haiku"}
CHECK_SCRIPTS = ("gradle_summary.py", "test_summary.py")
STATUS_LINE = re.compile(r"^\s*STATUS:\s*([A-Za-z_]+)", re.MULTILINE)
CHECKS_BLOCK = re.compile(r"^\s*CHECKS:(.*?)(?=^\s*[A-Z][A-Z_]{2,}:|\Z)", re.MULTILINE | re.DOTALL)
FAILURE_WORDS = re.compile(r"\b(?:fail(?:ed|s|ing|ures?)?|timeout|timed out|offline|hung|hangs)\b", re.IGNORECASE)
NEGATED_BEFORE = re.compile(r"(?:\b(?:no|0|zero|without)\s+|--)$", re.IGNORECASE)
ZERO_AFTER = re.compile(r"^\s*(?:[:=]\s*)?(?:0|none)\b", re.IGNORECASE)
NEXT_STEP = re.compile(r'"?next_step"?\s*[:=]\s*"?(build-doctor|test-analyst)\b')
RAW_LOG = re.compile(r'"raw_log_path"\s*:\s*"([^"]+)"')
TIMEOUT_STATUS = re.compile(r'"status"\s*:\s*"timeout"')
EXIT_CODE = re.compile(r"^\s*Exit code (\d+)")
TEST_TASK = re.compile(r"^(?:test|connected\w*|\w*UnitTest|\w*AndroidTest)$", re.IGNORECASE)
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2(?=[\s;&|()<>]|$)")
OPERATOR = re.compile(r"\n|;;|&&|\|\||\|&|&>>|&>|>>|>&|<&|>\||<<<|<<|<>|[;&|()<>]")
FALLBACK_TOKENS = re.compile(r"\n|[();<>|&]+|[^\s();<>|&]+")
SEPARATORS = {"|", "|&", "||", "&&", ";", "&", "\n", "(", ")", ";;"}


def texts(value) -> list[str]:
    """Every string inside a tool response, however Claude Code nests it."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in texts(item)]
    if isinstance(value, list):
        return [text for item in value for text in texts(item)]
    return []


def summaries(text: str) -> list[dict]:
    """The check summaries printed in a command's output, in order."""
    found, decoder, start = [], json.JSONDecoder(), text.find("{")
    while start != -1:
        try:
            value, end = decoder.raw_decode(text, start)
        except ValueError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict) and "schema_version" in value and "status" in value:
            found.append(value)
            start = text.find("{", end)
        else:
            start = text.find("{", start + 1)
    return found


def _next_line(command: str, i: int) -> tuple[str, int]:
    end = command.find("\n", i)
    return (command[i:], len(command)) if end == -1 else (command[i:end], end + 1)


def _skip_heredoc_bodies(command: str, i: int, pending: list) -> int:
    for strip_tabs, quoted, delimiter in pending:
        while i < len(command):
            line, i = _next_line(command, i)
            line = line.rstrip("\r")
            while not quoted and (len(line) - len(line.rstrip("\\"))) % 2 == 1 and i < len(command):
                more, i = _next_line(command, i)
                line = line[:-1] + more.rstrip("\r")
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                break
    return i


def shell_text(command: str, tool: str) -> str:
    """The command as the shell runs it: without comments, heredoc bodies and line continuations.

    Only used to find which check scripts ran. A mistake here costs a missing or an extra note, never a write: the
    layer guard decides what may run.
    """
    bash = tool != "PowerShell"
    escape = "\\" if bash else "`"
    out, pending, mode, in_word, i, n = [], [], "", False, 0, len(command)
    while i < n:
        c = command[i]
        if c == "\n" and mode in ("", "comment"):
            out.append(c)
            mode, in_word = "", False
            i = _skip_heredoc_bodies(command, i + 1, pending)
            pending = []
            continue
        if mode == "comment":
            i += 1
            continue
        if mode == "single":
            if c == "'":
                mode = ""
        elif mode in ("double", "ansi") or (mode == "" and c == escape):
            this_escape = "\\" if mode == "ansi" else escape
            if c == this_escape and i + 1 < n:
                if command[i + 1] != "\n" or mode == "ansi":
                    out.append(command[i:i + 2])
                    in_word = True
                i += 2
                continue
            if (mode == "double" and c == '"') or (mode == "ansi" and c == "'"):
                mode = ""
        elif bash and c == "$" and command[i + 1:i + 2] == "'":
            out.append("$'")
            mode, in_word, i = "ansi", True, i + 2
            continue
        elif c in "'\"":
            mode, in_word = ("single" if c == "'" else "double"), True
        elif c == "#" and not in_word:
            mode = "comment"
            i += 1
            continue
        elif c in " \t\r;|&()<>":
            in_word = False
            if bash and c == "<":
                match = HEREDOC.match(command, i)
                if match:
                    pending.append((match.group(1) == "-", bool(match.group(2)), match.group(3)))
                    out.append(match.group(0))
                    i = match.end()
                    continue
        else:
            in_word = True
        out.append(c)
        i += 1
    return "".join(out)


def command_segments(text: str) -> list[list[str]]:
    lex = shlex.shlex(text, posix=False, punctuation_chars="();<>|&\n")
    lex.whitespace, lex.whitespace_split, lex.commenters = " \t\r", True, ""
    try:
        tokens = list(lex)
    except ValueError:
        tokens = FALLBACK_TOKENS.findall(text)
    groups, current = [], []
    for token in tokens:
        for part in (OPERATOR.findall(token) if len(token) > 1 and is_operator(token) else [token]):
            if part in SEPARATORS:
                if current:
                    groups.append(current)
                current = []
            elif not is_operator(part):
                current.append(part[1:-1] if len(part) >= 2 and part[0] == part[-1] and part[0] in "'\"" else part)
    if current:
        groups.append(current)
    return groups


def checks_run(command: str, tool: str = "Bash") -> list[str]:
    """The check scripts the command runs with Python, not the ones it only names (rg, cat, comments, heredoc text)."""
    found = []
    for words in command_segments(shell_text(command, tool)):
        base, words = program_of(words)
        if base not in PYTHON_PROGRAMS:
            continue
        script = basename(next((word for word in words[1:] if not word.startswith("-")), ""))
        if script in CHECK_SCRIPTS:
            found.append(script)
    return found


def agent_for(summary: dict) -> str | None:
    """The summary's next_step; for summaries from before 0.4.1, the same rule gradle_summary.py applies."""
    if "next_step" in summary:
        step = summary.get("next_step")
        return step if step in DIAGNOSIS_MODELS else None
    status, tools = summary.get("status"), summary.get("tool_versions") or {}
    if isinstance(tools, dict) and "test_summary" in tools:
        return "test-analyst" if status == "failed" else None
    if status == "timeout":
        return "build-doctor"
    if status != "failed":
        return None
    tasks = summary.get("failed_tasks") or []
    only_tests = (summary.get("failed_tests_total", 0) > 0 and summary.get("failures_total", 0) == 0 and tasks
                  and all(TEST_TASK.match(str(task).rsplit(":", 1)[-1]) for task in tasks))
    return "test-analyst" if only_tests else "build-doctor"


def reports_failure(text: str) -> bool:
    """Whether the text reports a failure, leaving out "no failures", "0 failed", "failures: 0" and "--timeout"."""
    for match in FAILURE_WORDS.finditer(text):
        if NEGATED_BEFORE.search(text[max(0, match.start() - 12):match.start()]) or ZERO_AFTER.match(text[match.end():]):
            continue
        return True
    return False


def note(agent: str, what: str, evidence: str) -> str:
    return (f"[{PLUGIN}] {what} Its diagnosis goes to {agent} ({DIAGNOSIS_MODELS[agent]}) with {evidence}, before you "
            "investigate it yourself. If the plan you are following approves the diagnosis agents (the Checks line "
            "of a develop plan), call it now. Otherwise propose it to the user first.")


def shell_note(event: dict) -> str | None:
    scripts = checks_run(str((event.get("tool_input") or {}).get("command", "")), event.get("tool_name", "Bash"))
    if not scripts:
        return None
    failed_call = event.get("hook_event_name") == "PostToolUseFailure"
    if failed_call and event.get("is_interrupt"):
        return None  # the user stopped the command
    body = event.get("error") if failed_call else event.get("tool_response")
    found = [summary for text in texts(body) for summary in summaries(text)]
    routed = [(agent_for(summary), summary) for summary in found]
    routed = [(agent, summary) for agent, summary in routed if agent]
    if routed:
        agent, summary = routed[-1]
        what = {"timeout": "The check timed out.",
                "device_unavailable": "No device was ready, so Gradle did not run."}.get(summary.get("status"),
                                                                                         "The check failed.")
        log = summary.get("raw_log_path")
        evidence = f"the summary and its log ({log})" if log else "the summary"
        return note(agent, what, evidence)
    return cut_summary_note(scripts, "\n".join(texts(body)), failed_call, complete=bool(found))


def cut_summary_note(scripts: list[str], text: str, failed_call: bool, complete: bool) -> str | None:
    """A check whose summary is not complete JSON: Claude Code cut long output, a pipe such as `| head` cut it, or the
    shell call timed out.

    The summaries print `next_step` and `raw_log_path` near the top, so a cut usually keeps them; a `next_step` in a
    cut summary routes even when a complete summary before it passed. Without one, only a failed call (a non-zero exit
    code) with no complete summary at all is routed.
    """
    log = RAW_LOG.findall(text)
    evidence = f"its log ({log[-1]})" if log else "the command that ran"
    step = NEXT_STEP.findall(text)
    if step:
        what = "The check timed out." if TIMEOUT_STATUS.search(text) else "The check failed."
        return note(step[-1], f"{what} Its summary was cut in the output.", evidence)
    if not failed_call or complete:
        return None
    code = EXIT_CODE.match(text)
    if "test_summary.py" in scripts and code and code.group(1) == "1":
        return note("test-analyst", "The tests failed, and their summary was cut in the output.", "the module path")
    if "gradle_summary.py" in scripts:
        return note("build-doctor", "The check ended without a complete summary; the shell call may have timed out.",
                    evidence)
    return None


def agent_note(event: dict) -> str | None:
    if event.get("hook_event_name") != "PostToolUse":
        return None
    name = kit_agent_name((event.get("tool_input") or {}).get("subagent_type"))
    if name not in WRITING_AGENTS:
        return None
    reply = "\n".join(texts(event.get("tool_response")))
    statuses = STATUS_LINE.findall(reply)
    if not statuses or statuses[-1].lower() not in ("failed", "blocked"):
        return None
    checks = CHECKS_BLOCK.findall(reply)
    if not checks or not reports_failure(checks[-1]):
        return None
    step = NEXT_STEP.findall(reply)
    if step:
        return note(step[-1], f"{name} reported a failing check that it could not fix.",
                    "the check summary from its reply")
    return (f"[{PLUGIN}] {name} reported a failing check that it could not fix. Its diagnosis goes to build-doctor "
            "(haiku) for a build, environment or device failure or a timeout, or to test-analyst (haiku) for failing "
            "tests, with the check summary from the reply, before you investigate it yourself. If the plan you are "
            "following approves the diagnosis agents (the Checks line of a develop plan), call it now. Otherwise "
            "propose it to the user first.")


def decide(event: dict) -> str | None:
    if not isinstance(event, dict) or event.get("agent_type"):
        return None
    tool = event.get("tool_name", "")
    if tool in SHELL_TOOLS:
        return shell_note(event)
    if tool in AGENT_TOOLS:
        return agent_note(event)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    message = decide(event)
    if message:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event.get("hook_event_name", "PostToolUse"),
                                                 "additionalContext": message}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
