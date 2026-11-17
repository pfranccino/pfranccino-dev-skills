#!/usr/bin/env python3
"""Plan gate and checkout ownership for android-feature-kit's writing agents.

Claude Code runs this script on two events:

- PostToolUse of ExitPlanMode. The event fires after the user approves a plan presented in Plan Mode (a rejected
  plan is a permission denial, which fires no PostToolUse), and `tool_response.plan` holds the plan as approved,
  including the user's edits. When the plan gate is on, the script records the approval in
  `build/android-feature-kit/approved-plan.json`: the session id, and the kit agents named on the plan's `Agents:`
  line with the model in parentheses after each one.
- PreToolUse of Agent (Task in older versions), before the main session launches a subagent. It acts only when the
  subagent is one of the kit's writing agents (domain-builder, data-builder, ui-builder, feature-integrator):
  1. Always: when `build/android-feature-kit/scope.json` names another session in `session_id`, the launch is
     blocked, because only one kit run works in a checkout at a time.
  2. When the plan gate is on: the launch is blocked unless the plan approved in this session lists the agent, and
     unless it runs on the model the plan gives it (the Agent call's `model`, or the agent's default model).

The plan gate is off by default. A project turns it on in `.claude/android-feature-kit.json`:

    {"planGate": true}

Exit 0 lets the call run. Exit 2 blocks a PreToolUse call and shows stderr to Claude; after PostToolUse it only
shows stderr to Claude. Like the layer guard, this is a guardrail: the layer guard blocks writes to the approval
record and to another session's scope, but nothing here proves more than what Claude Code reports.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

from layer_guard import APPROVED_PLAN_FILE, PLUGIN, PLUGIN_ROOT, SCOPE_FILE, kit_agent_name, real_session_id, scope_owner

WRITING_AGENTS = ("domain-builder", "data-builder", "ui-builder", "feature-integrator")
READ_ONLY_AGENTS = ("build-doctor", "test-analyst", "android-reviewer", "android-architect")
MODELS = ("haiku", "sonnet", "opus", "fable", "inherit")
UNREADABLE = "unreadable"
AGENT_TOOLS = {"Agent", "Task"}
AGENTS_LINE = re.compile(r"^[\s>*_`#-]*agents[\s*_`]*:[\s*_`]*(.*)$", re.IGNORECASE)
NEXT_FIELD = re.compile(r"^[\s>*_`#-]*[A-Za-z][A-Za-z ]{0,40}[\s*_`]*:")


def gate_enabled(project_dir: str) -> bool:
    try:
        with open(os.path.join(project_dir, ".claude", f"{PLUGIN}.json"), encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError):
        return False
    return isinstance(config, dict) and config.get("planGate") is True


def read_json(project_dir: str, relative) -> dict | None:
    try:
        with open(os.path.join(project_dir, relative), encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def default_model(agent: str) -> str | None:
    """The `model` in the agent's frontmatter, which applies when the Agent call sets none."""
    try:
        with open(PLUGIN_ROOT / "agents" / f"{agent}.md", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    match = re.search(r"^model:\s*([\w.-]+)\s*$", text.split("\n---", 1)[0], re.MULTILINE)
    return match.group(1).lower() if match else None


def agents_in_plan(plan: str) -> dict[str, str | None]:
    """The kit agents named on the plan's `Agents:` line (or in the list right under an empty one), each with the
    model written in parentheses after it, or None when the plan names no model."""
    lines = plan.splitlines()
    text = []
    for index, line in enumerate(lines):
        match = AGENTS_LINE.match(line)
        if not match:
            continue
        text.append(match.group(1))
        if not match.group(1).strip():
            for following in lines[index + 1:]:
                if not following.strip() or NEXT_FIELD.match(following) and not following.lstrip().startswith(("-", "*")):
                    break
                text.append(following)
    joined = "\n".join(text)
    found: dict[str, str | None] = {}
    for name in WRITING_AGENTS + READ_ONLY_AGENTS:
        match = re.search(rf"(?<![\w-])(?:{PLUGIN}:)?{re.escape(name)}(?![\w-])[\s`*_]*(?:\(([^)]*)\))?", joined)
        if match:
            inside = match.group(1)
            if inside is None:
                found[name] = None
            else:
                word = re.match(r"[\s`*_]*([A-Za-z]+)", inside)
                model = word.group(1).lower() if word else ""
                found[name] = model if model in MODELS else UNREADABLE
    if any(model for model in found.values()):
        # The plan gives models; a writing agent without a readable one would otherwise run unchecked.
        for name in WRITING_AGENTS:
            if name in found and found[name] is None:
                found[name] = UNREADABLE
    return found


def approved_plan_text(tool_input: dict, tool_response) -> str:
    """The plan as the user approved it: `tool_response.plan`, then the input, then the plan file."""
    response = tool_response if isinstance(tool_response, dict) else {}
    for value in (response.get("plan"), tool_input.get("plan")):
        if isinstance(value, str) and value.strip():
            return value
    for path in (response.get("filePath"), tool_input.get("planFilePath")):
        if isinstance(path, str) and path:
            try:
                with open(path, encoding="utf-8") as handle:
                    return handle.read()
            except OSError:
                continue
    return ""


def record_approval(event: dict, project_dir: str) -> str | None:
    """Write the approval record. Returns a message for Claude, or None."""
    if not gate_enabled(project_dir):
        return None
    tool_input = event.get("tool_input") or {}
    response = event.get("tool_response") if isinstance(event.get("tool_response"), dict) else {}
    agents = agents_in_plan(approved_plan_text(tool_input, response))
    record = {
        "session_id": real_session_id(event.get("session_id")),
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan_file": response.get("filePath") or tool_input.get("planFilePath"),
        "agents": list(agents),
        "models": {name: model for name, model in agents.items() if model},
    }
    path = os.path.join(project_dir, APPROVED_PLAN_FILE)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2)
            handle.write("\n")
    except OSError as error:
        return f"The plan gate could not record the approved plan ({error}); the kit's writing agents stay blocked."
    if not any(agent in WRITING_AGENTS for agent in agents):
        return ("The plan gate recorded this approval with no writing agents, because the plan has no `Agents:` line "
                "naming them. If this plan uses the kit's writing agents, present it again with that line.")
    unreadable = [name for name, model in agents.items() if model == UNREADABLE and name in WRITING_AGENTS]
    if unreadable:
        return (f"The plan gate could not read the model for {', '.join(unreadable)}, so it will block them. Present "
                f"the plan again with one of {', '.join(MODELS)} in parentheses after each agent.")
    return None


def check_launch(event: dict, project_dir: str) -> str | None:
    tool_input = event.get("tool_input") or {}
    agent = kit_agent_name(tool_input.get("subagent_type"))
    if agent not in WRITING_AGENTS:
        return None
    session = real_session_id(event.get("session_id"))

    owner = scope_owner(project_dir)
    if owner and owner != session:
        return (f"Another Claude session ({owner}) is running a kit task in this checkout: "
                f"{SCOPE_FILE.as_posix()} belongs to it. Only one run works in a checkout at a time. Tell the user; "
                "if that run is over, the user deletes the file.")

    if not gate_enabled(project_dir):
        return None
    approval = read_json(project_dir, APPROVED_PLAN_FILE)
    if approval is None or not session or real_session_id(approval.get("session_id")) != session:
        return (f"The plan gate is on, and no plan approved in Plan Mode in this session lists {agent}. Present the "
                "plan with ExitPlanMode, with an `Agents:` line naming each agent, and wait for the user to approve it.")
    approved = approval.get("agents") if isinstance(approval.get("agents"), list) else []
    if agent not in approved:
        listed = ", ".join(approved) or "none"
        return (f"{agent} is not in the approved plan (its `Agents:` line lists: {listed}). Launching it changes the "
                "plan: ask the user, and present the updated plan for approval.")
    models = approval.get("models") if isinstance(approval.get("models"), dict) else {}
    planned = models.get(agent)
    if planned == UNREADABLE:
        return (f"The approved plan gives {agent} a model the plan gate cannot read. Present the plan again with one "
                f"of {', '.join(MODELS)} in parentheses after the agent.")
    if planned and planned != "inherit":
        requested = str(tool_input.get("model") or default_model(agent) or "").lower()
        if planned not in requested:
            return (f"The approved plan runs {agent} on {planned}, and this launch would run it on "
                    f"{requested or 'an unknown model'}. Set `model` to {planned}, or ask the user to approve the change.")
    return None


def decide(event: dict, project_dir: str) -> str | None:
    tool = event.get("tool_name", "")
    hook = event.get("hook_event_name", "")
    if hook == "PostToolUse" and tool == "ExitPlanMode":
        return record_approval(event, project_dir)
    if hook == "PreToolUse" and tool in AGENT_TOOLS:
        return check_launch(event, project_dir)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(event, dict):
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    message = decide(event, project_dir)
    if message:
        print(f"[{PLUGIN} plan gate] {message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
