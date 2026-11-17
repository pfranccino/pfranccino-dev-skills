#!/usr/bin/env python3
"""PreToolUse guard for android-feature-kit's agents.

Claude Code runs this before Edit, Write, MultiEdit, NotebookEdit, Bash and PowerShell calls. It acts
only when the call comes from one of the kit's agents (the hook input names the agent in
`agent_type`); calls from the main session and from other plugins' agents pass untouched.

Writes:
- Every path is resolved against the call's working directory, and a write outside the project is
  blocked.
- Layer agents (domain-builder, data-builder, ui-builder) write only inside their layer's packages.
  When the develop flow has written its scope file (`build/android-feature-kit/scope.json`, with
  `{"modules": ["feature/orders"]}`), they also write only inside those modules.
- feature-integrator needs the scope file: it may not write in the scoped modules' `src/` folders
  (the layer agents own them) except their `src/*/AndroidManifest.xml` files, and may write elsewhere
  in the project, including the scoped modules' build files.
- Read-only agents (build-doctor, test-analyst, android-reviewer, android-architect) write nothing.

Shell commands from the kit's agents must start with an allowed program and use it in a read-only
way: the Gradle wrapper, read-only git subcommands without write or exec options, read-only file
tools, Android CLI documentation, preview and studio queries, or Python running the kit's check
scripts from `tools/agent-checks/` or the plugin. Redirection to files, command substitution and
PowerShell script blocks are blocked.

Every session, the main one included, is blocked from writing `build/android-feature-kit/approved-plan.json`
with the edit tools or mentioning it in a shell command: only plan_gate.py records plan approvals there. While
`scope.json` holds another session's id, no session may write it or mention it in a shell command either: one
kit run works in a checkout at a time, and the user releases a stale scope by deleting the file. The kit's agents
never write in `build/android-feature-kit/`.

Exit 0 lets the call run. Exit 2 blocks it, and the message on stderr is shown to the agent. This is a
guardrail, not a sandbox: Gradle runs the project's own build logic, and the repository's pre-commit
and CI checks are the boundary. A project can replace the layer patterns in
`.claude/android-feature-kit.json`:

    {"layers": {"domain-builder": {"allow": ["**/src/*/kotlin/**/domain/**"]}}}
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

PLUGIN = "android-feature-kit"
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCOPE_FILE = Path("build") / PLUGIN / "scope.json"
APPROVED_PLAN_FILE = Path("build") / PLUGIN / "approved-plan.json"

SOURCE = "**/src/*/{java,kotlin}/**"
DEFAULT_LAYERS = {
    "domain-builder": {"allow": [f"{SOURCE}/domain/**"]},
    "data-builder": {"allow": [f"{SOURCE}/data/**"]},
    "ui-builder": {
        "allow": [
            f"{SOURCE}/presentation/**",
            f"{SOURCE}/ui/**",
            f"{SOURCE}/navigation/**",
            "**/src/*/res/**",
        ]
    },
}
INTEGRATOR = "feature-integrator"
READ_ONLY_AGENTS = {"build-doctor", "test-analyst", "android-reviewer", "android-architect"}
KIT_AGENTS = set(DEFAULT_LAYERS) | {INTEGRATOR} | READ_ONLY_AGENTS

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}

READ_ONLY_PROGRAMS = {
    "ls", "dir", "cat", "type", "head", "tail", "wc", "pwd", "echo", "rg", "grep", "findstr", "find",
    "tree", "which", "where", "diff",
    "get-childitem", "gci", "get-content", "gc", "select-string", "sls", "get-location", "test-path",
    "resolve-path", "measure-object", "select-object", "where-object", "write-output", "out-string",
}
GIT_READ_SUBCOMMANDS = {"status", "diff", "log", "show", "blame", "ls-files", "rev-parse", "grep", "merge-base"}
GIT_BLOCKED_LONG = ("--output", "--open-files-in-pager", "--ext-diff", "--exec-path", "--config-env")
GIT_BLOCKED_SHORT = ("-o", "-c")
ANDROID_SUBCOMMANDS = {"docs", "preview", "studio", "help", "--help", "--version"}
PYTHON_PROGRAMS = {"python", "python3", "py", "python.exe", "python3.exe", "py.exe"}
CHECK_SCRIPTS = ("gradle_summary.py", "test_summary.py")
SCRIPT_OPTIONS = {"gradle_summary.py": {"--max"}, "test_summary.py": {"--module", "--results", "--max"}}
BLOCKED_FIND_FLAGS = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"}
SEPARATORS = {"|", "||", "&&", ";", "&", "\n", "(", ")", ";;"}
NULL_TARGETS = {"/dev/null", "$null", "nul"}


def kit_agent_name(agent_type: str | None) -> str | None:
    if not agent_type:
        return None
    if ":" in agent_type:
        plugin, _, name = agent_type.rpartition(":")
        if plugin.split(":")[0] != PLUGIN:
            return None
    else:
        name = agent_type
    return name if name in KIT_AGENTS else None


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "{":
            j = pattern.index("}", i)
            options = pattern[i + 1:j].split(",")
            out.append("(?:" + "|".join(re.escape(o) for o in options) + ")")
            i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE)


def matches(path: str, patterns: list[str]) -> bool:
    return any(glob_to_regex(p).match(path) for p in patterns)


def native(path: str) -> str:
    """On Windows, turn a Git Bash path (/c/Users/...) into a drive path (c:/Users/...) before any join."""
    path = path.replace("\\", "/")
    if os.name == "nt":
        path = re.sub(r"^/([A-Za-z])(/|$)", r"\1:/", path)
    return path


def normalize(path: str) -> str:
    return os.path.normcase(os.path.normpath(native(path))).replace("\\", "/")


def resolve(path: str, cwd: str) -> str:
    return normalize(os.path.join(native(cwd), native(path)))


def project_relative(file_path: str, cwd: str, project_dir: str) -> str | None:
    """The path relative to the project, after resolving it against cwd and removing `..`; None when outside."""
    absolute = resolve(file_path, cwd or project_dir)
    root = normalize(project_dir).rstrip("/")
    if absolute == root:
        return ""
    if not absolute.startswith(root + "/"):
        return None
    return absolute[len(root) + 1:]


def load_layers(project_dir: str) -> dict:
    layers = {name: dict(rules) for name, rules in DEFAULT_LAYERS.items()}
    try:
        with open(os.path.join(project_dir, ".claude", f"{PLUGIN}.json"), encoding="utf-8") as handle:
            custom = json.load(handle).get("layers", {})
    except (OSError, ValueError, AttributeError):
        return layers
    for name, rules in custom.items():
        if name in DEFAULT_LAYERS and isinstance(rules, dict) and isinstance(rules.get("allow"), list):
            layers[name] = {"allow": [str(p) for p in rules["allow"]]}
    return layers


def load_scope(project_dir: str) -> list[str] | None:
    try:
        with open(os.path.join(project_dir, SCOPE_FILE), encoding="utf-8") as handle:
            modules = json.load(handle).get("modules")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(modules, list) or not modules:
        return None
    return [normalize(str(m)).strip("/") for m in modules if str(m).strip("/.")]


def inside(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder + "/")


def check_write(agent: str, file_path: str, cwd: str, project_dir: str) -> str | None:
    if agent in READ_ONLY_AGENTS:
        return f"{agent} is read-only: it reports findings and proposed fixes, it never writes files."
    path = project_relative(file_path, cwd, project_dir)
    if path is None:
        return f"{agent} may not write outside the project ({file_path})."
    if inside(path, normalize(SCOPE_FILE.parent.as_posix())):
        return f"{agent} may not write the kit's own files in {SCOPE_FILE.parent.as_posix()}/."
    scope = load_scope(project_dir)
    if agent == INTEGRATOR:
        if scope is None:
            return (f"{agent} writes only when the develop flow has written {SCOPE_FILE.as_posix()} with the feature "
                    "modules, so it can keep out of their layers.")
        for module in scope:
            if inside(path, module + "/src") and not matches(path, [module + "/src/*/AndroidManifest.xml"]):
                return (f"{agent} may not write inside {module}/src, except its AndroidManifest.xml files: the layer "
                        "agents own it. Return the item to the orchestrator with its owner.")
        return None
    if scope is not None and not any(inside(path, module) for module in scope):
        return (f"{agent} may only write inside the modules of this task ({', '.join(scope)}); {path} is outside. "
                "Report the change under OUTSIDE_MODULE.")
    rules = load_layers(project_dir)[agent]
    if not matches(path, rules["allow"]):
        return (f"{agent} may only write inside its layer ({', '.join(rules['allow'])}); {path} is outside it. "
                "Report the change under OUTSIDE_MODULE or CONTRACT_REQUESTS so the orchestrator sends it to its owner.")
    return None


def unquoted_scan(command: str):
    """Yield (index, char) for characters outside single quotes, and whether they are inside double quotes."""
    single = double = False
    for i, c in enumerate(command):
        if c == "'" and not double:
            single = not single
            continue
        if c == '"' and not single:
            double = not double
            continue
        if not single:
            yield i, c, double


def check_expansion(command: str, tool: str) -> str | None:
    for i, c, double in unquoted_scan(command):
        if c == "$" and command[i + 1:i + 2] == "(":
            return "Command substitution is not allowed in the kit's agents' shell commands."
        if c == "`" and tool == "Bash":
            return "Command substitution is not allowed in the kit's agents' shell commands."
        if c in "<>" and command[i + 1:i + 2] == "(" and not double:
            return "Process substitution is not allowed in the kit's agents' shell commands."
        if c == "{" and tool == "PowerShell" and not double:
            return "PowerShell script blocks are not allowed in the kit's agents' shell commands; use Select-String to filter."
    return None


def tokenize(command: str) -> list[str]:
    """Words and operators, keeping quoted text (with its quotes) as one word."""
    lex = shlex.shlex(command, posix=False, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:
        return command.split()


def unquote(token: str) -> str:
    return token[1:-1] if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"" else token


def is_operator(token: str) -> bool:
    return bool(token) and set(token) <= set("();<>|&\n")


def check_redirects(tokens: list[str]) -> str | None:
    for i, token in enumerate(tokens):
        if ">" not in token or not is_operator(token):
            continue
        target = unquote(tokens[i + 1]).lower() if i + 1 < len(tokens) else ""
        if token == ">&" and target.isdigit():
            continue  # 2>&1
        if target in NULL_TARGETS:
            continue
        return "Output redirection to files is not allowed. Read the output directly, or use the check scripts, which save logs themselves."
    return None


def segments(tokens: list[str]) -> list[list[str]]:
    groups, current = [], []
    for token in tokens:
        if token in SEPARATORS:
            if current:
                groups.append(current)
            current = []
        elif is_operator(token):
            current.append(token)  # redirections stay with their command
        else:
            current.append(unquote(token))
    if current:
        groups.append(current)
    return groups


def basename(word: str) -> str:
    return word.replace("\\", "/").rsplit("/", 1)[-1].lower()


def program_of(words: list[str]) -> tuple[str, list[str]]:
    while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
        words = words[1:]  # VAR=value prefixes
    if words and words[0] in {"&", "."} and len(words) > 1:
        words = words[1:]  # PowerShell call operators
    if not words:
        return "", []
    return basename(words[0]), words


def is_gradle(base: str) -> bool:
    return base in {"gradlew", "gradlew.bat"}


def allowed_script(word: str, cwd: str, project_dir: str) -> bool:
    name = basename(word)
    if name not in CHECK_SCRIPTS:
        return False
    resolved = resolve(word, cwd or project_dir)
    allowed = {normalize(os.path.join(project_dir, "tools", "agent-checks", name)),
               normalize(str(PLUGIN_ROOT / "repo-tools" / "agent-checks" / name))}
    return resolved in allowed


def check_python(words: list[str], cwd: str, project_dir: str) -> str | None:
    if len(words) < 2 or words[1].startswith("-") or not allowed_script(words[1], cwd, project_dir):
        return ("Python may only run the kit's check scripts, as the first argument: tools/agent-checks/gradle_summary.py "
                "or test_summary.py in the repository, or the plugin's copies.")
    rest = words[2:]
    if "--" in rest:
        options, wrapped = rest[:rest.index("--")], rest[rest.index("--") + 1:]
    else:
        options, wrapped = rest, []
    allowed = SCRIPT_OPTIONS[basename(words[1])]
    i = 0
    while i < len(options):
        name, _, value = options[i].partition("=")
        if name not in allowed:
            return (f"{basename(words[1])} accepts only {', '.join(sorted(allowed))} here; "
                    f"{options[i]} is not allowed.")
        i += 1 if value else 2
    if wrapped:
        base, _ = program_of(wrapped)
        if not is_gradle(base):
            return "The check scripts may only wrap a Gradle wrapper command."
    return None


def git_blocked_long(option: str) -> bool:
    """A long option, or any abbreviation git would accept for it, that writes files or runs commands."""
    name = option.split("=", 1)[0]
    return name.startswith("--") and len(name) > 3 and any(blocked.startswith(name) for blocked in GIT_BLOCKED_LONG)


def check_words(words: list[str], cwd: str, project_dir: str) -> str | None:
    words = [w for w in words if not is_operator(w)]
    base, words = program_of(words)
    if not base:
        return None
    if is_gradle(base):
        return None
    if base in {"git", "git.exe"}:
        rest, sub = words[1:], ""
        while rest:
            if rest[0] == "-c" or git_blocked_long(rest[0]):
                return f"git {rest[0]} is not allowed: configuration can run commands."
            if rest[0] == "-C":
                rest = rest[2:]
            elif rest[0].startswith("-"):
                rest = rest[1:]
            else:
                sub = rest[0]
                rest = rest[1:]
                break
        if sub not in GIT_READ_SUBCOMMANDS:
            return f"git {sub or '(no subcommand)'} is not allowed; only {', '.join(sorted(GIT_READ_SUBCOMMANDS))}."
        for option in rest:
            if option in GIT_BLOCKED_SHORT or option.startswith("-O") or git_blocked_long(option):
                return f"git {sub} {option} is not allowed: it writes files or runs commands."
        return None
    if base in {"android", "android.exe"}:
        sub = next((w for w in words[1:] if not w.startswith("-")), words[1] if len(words) > 1 else "")
        if sub in ANDROID_SUBCOMMANDS:
            return None
        return f"android {sub} is not allowed; only docs, preview and studio queries."
    if base in PYTHON_PROGRAMS:
        return check_python(words, cwd, project_dir)
    if base == "find" and BLOCKED_FIND_FLAGS & set(words[1:]):
        return "find with -delete, -exec or -fprint is not allowed."
    if base == "rg" and any(w.startswith("--pre") for w in words[1:]):
        return "rg --pre runs a command and is not allowed."
    if base in READ_ONLY_PROGRAMS:
        return None
    return (
        f"'{words[0]}' is not an allowed command for the kit's agents. Use Edit or Write for files, and Gradle, "
        "read-only git, rg or the check scripts for everything else."
    )


def check_shell(command: str, tool: str, cwd: str, project_dir: str) -> str | None:
    problem = check_expansion(command, tool)
    if problem:
        return problem
    tokens = tokenize(command)
    problem = check_redirects(tokens)
    if problem:
        return problem
    for words in segments(tokens):
        problem = check_words(words, cwd, project_dir)
        if problem:
            return problem
    return None


def real_session_id(value) -> str | None:
    """A session id Claude Code would send; None for empty values and unexpanded placeholders."""
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "${}<>"):
        return None
    return value.strip()


def scope_owner(project_dir: str) -> str | None:
    try:
        with open(os.path.join(project_dir, SCOPE_FILE), encoding="utf-8") as handle:
            scope = json.load(handle)
    except (OSError, ValueError):
        return None
    return real_session_id(scope.get("session_id")) if isinstance(scope, dict) else None


def check_kit_records(event: dict, project_dir: str) -> str | None:
    """Only plan_gate.py writes the approval record, and no session replaces another session's scope."""
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    target, command = None, ""
    if tool in WRITE_TOOLS:
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if file_path:
            target = project_relative(file_path, event.get("cwd") or project_dir, project_dir)
    elif tool in SHELL_TOOLS:
        command = str(tool_input.get("command", "")).lower()
    if target == normalize(APPROVED_PLAN_FILE.as_posix()) or APPROVED_PLAN_FILE.name in command:
        return (f"Only the plan gate records plan approvals in {APPROVED_PLAN_FILE.as_posix()}, when the user "
                "approves a plan in Plan Mode. Read it with the Read tool if you need it.")
    if target == normalize(SCOPE_FILE.as_posix()) or SCOPE_FILE.name in command:
        owner = scope_owner(project_dir)
        if owner and owner != real_session_id(event.get("session_id")):
            return (f"{SCOPE_FILE.as_posix()} belongs to another Claude session ({owner}), which may still be running "
                    "a kit task in this checkout. Only one run works in a checkout at a time. Tell the user; if that "
                    "run is over, the user deletes the file.")
    return None


def decide(event: dict, project_dir: str) -> str | None:
    problem = check_kit_records(event, project_dir)
    if problem:
        return problem
    agent = kit_agent_name(event.get("agent_type"))
    if agent is None:
        return None
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    cwd = event.get("cwd") or project_dir
    if tool in WRITE_TOOLS:
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return check_write(agent, file_path, cwd, project_dir) if file_path else None
    if tool in SHELL_TOOLS:
        return check_shell(tool_input.get("command", ""), tool, cwd, project_dir)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    problem = decide(event, project_dir)
    if problem:
        print(f"[{PLUGIN} layer guard] {problem}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
