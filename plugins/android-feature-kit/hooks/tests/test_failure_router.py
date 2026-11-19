"""Tests for the failure router. Run from the plugin root: python -m unittest discover -s hooks/tests"""
import json
import pathlib
import subprocess
import sys
import unittest

HOOKS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

import failure_router  # noqa: E402

GRADLE = "python tools/agent-checks/gradle_summary.py -- ./gradlew :app:assembleDebug"
CONNECTED = "python tools/agent-checks/gradle_summary.py -- ./gradlew :app:connectedDebugAndroidTest"
TESTS = "python tools/agent-checks/test_summary.py --module feature/orders"


def gradle_summary(status, next_step="build-doctor", **extra):
    summary = {"schema_version": 2, "tool_versions": {"gradle_summary": "2"}, "status": status, "next_step": next_step,
               "raw_log_path": "build/agent-checks/gradle-1.log", "failures": [], "failed_tests": []}
    summary.update(extra)
    return json.dumps(summary, indent=2)


def failed_shell(command, output, tool="Bash", **extra):
    event = {"hook_event_name": "PostToolUseFailure", "tool_name": tool, "tool_input": {"command": command},
             "error": f"Exit code 1\n{output}", "is_interrupt": False}
    event.update(extra)
    return failure_router.decide(event)


def passed_shell(command, output, tool="Bash"):
    event = {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": {"command": command},
             "tool_response": {"stdout": output, "stderr": "", "interrupted": False}}
    return failure_router.decide(event)


def agent_reply(subagent, reply):
    event = {"hook_event_name": "PostToolUse", "tool_name": "Agent",
             "tool_input": {"subagent_type": subagent, "prompt": "..."},
             "tool_response": {"content": [{"type": "text", "text": reply}]}}
    return failure_router.decide(event)


class ShellChecks(unittest.TestCase):
    def test_failed_build_names_build_doctor_and_the_log(self):
        message = failed_shell(GRADLE, gradle_summary("failed"))
        self.assertIn("build-doctor (haiku)", message)
        self.assertIn("build/agent-checks/gradle-1.log", message)
        self.assertIn("propose it to the user", message)

    def test_timeout_names_build_doctor(self):
        message = failed_shell(CONNECTED, gradle_summary("timeout"))
        self.assertIn("timed out", message)
        self.assertIn("build-doctor", message)

    def test_failed_tests_name_test_analyst(self):
        message = failed_shell(GRADLE, gradle_summary("failed", next_step="test-analyst"))
        self.assertIn("test-analyst (haiku)", message)
        summary = json.dumps({"schema_version": 2, "tool_versions": {"test_summary": "2"}, "status": "failed",
                              "failures_total": 2, "next_step": "test-analyst"})
        self.assertIn("test-analyst", failed_shell(TESTS, summary, tool="PowerShell"))

    def test_passing_checks_and_other_commands_say_nothing(self):
        self.assertIsNone(passed_shell(GRADLE, gradle_summary("passed", next_step=None)))
        self.assertIsNone(failed_shell("./gradlew :app:assembleDebug", "BUILD FAILED"))
        self.assertIsNone(failed_shell("rg -n foo", "Exit code 2"))

    def test_no_test_reports_say_nothing(self):
        summary = json.dumps({"schema_version": 2, "tool_versions": {"test_summary": "2"}, "status": "no_results",
                              "next_step": None})
        self.assertIsNone(failed_shell(TESTS, summary))

    def test_summaries_without_next_step_still_route(self):
        old = json.loads(gradle_summary("failed"))
        del old["next_step"]
        old.update(schema_version=1, failures_total=0, failed_tests_total=1, failed_tasks=[":app:checkDebugAarMetadata"])
        self.assertIn("build-doctor", failed_shell(GRADLE, json.dumps(old)))
        old["failed_tasks"] = [":app:testDebugUnitTest"]
        self.assertIn("test-analyst", failed_shell(GRADLE, json.dumps(old)))
        old_tests = {"schema_version": 1, "tool_versions": {"test_summary": "1"}, "status": "failed"}
        self.assertIn("test-analyst", failed_shell(TESTS, json.dumps(old_tests)))

    def test_piped_check_that_exits_0_still_routes(self):
        self.assertIn("build-doctor", passed_shell(GRADLE + " | head -80", gradle_summary("failed")))

    def test_gradle_check_without_a_summary_names_build_doctor(self):
        message = failed_shell(CONNECTED, "Command timed out after 10m")
        self.assertIn("ended without a complete summary", message)
        self.assertIn("build-doctor", message)

    def test_naming_a_script_is_not_running_it(self):
        self.assertIsNone(failed_shell("rg -n gradle_summary.py README.md", "Exit code 1"))
        self.assertIsNone(failed_shell("cat tools/agent-checks/gradle_summary.py", "No such file"))
        self.assertIsNone(failed_shell('git log --grep "gradle_summary.py"', "Exit code 1"))
        heredoc = "cat <<'EOF'\npython tools/agent-checks/gradle_summary.py -- ./gradlew :app:assembleDebug\nEOF\nfalse"
        self.assertIsNone(failed_shell(heredoc, ""))

    def test_cut_summaries_still_route(self):
        head = gradle_summary("failed", next_step="build-doctor")[:200]  # next_step and raw_log_path come first
        self.assertIn('"next_step"', head)
        message = failed_shell(GRADLE, head + "\n... [output truncated] ...\n}")
        self.assertIn("build-doctor", message)
        self.assertIn("build/agent-checks/gradle-1.log", message)
        tests_head = '{\n  "schema_version": 2,\n  "status": "failed",\n  "exit_code": 1,\n  "next_step": "test-analyst",\n'
        self.assertIn("test-analyst", failed_shell(TESTS, tests_head + "... [output truncated] ..."))
        self.assertIn("test-analyst", failed_shell(TESTS, '{\n  "schema_version": 2, ... [output truncated] ...'))
        no_reports = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "tool_input": {"command": TESTS},
                      "error": "Exit code 2\n{\n  ... [output truncated] ...", "is_interrupt": False}
        self.assertIsNone(failure_router.decide(no_reports))

    def test_a_summary_cut_by_a_pipe_that_exits_0_still_routes(self):
        head = gradle_summary("failed", next_step="build-doctor")[:200]
        self.assertIn("build-doctor", passed_shell(GRADLE + " | head -8", head))
        self.assertIsNone(passed_shell(GRADLE + " | head -8", '{\n  "schema_version": 2,\n  "status": "pas'))

    def test_a_cut_failing_summary_after_a_complete_passing_one_routes(self):
        passing = gradle_summary("passed", next_step=None)
        cut = '{\n  "schema_version": 2,\n  "status": "failed",\n  "next_step": "test-analyst",\n'
        command = GRADLE + " && " + TESTS + " | head -5"
        self.assertIn("test-analyst", passed_shell(command, passing + "\n" + cut))
        self.assertIsNone(failed_shell(GRADLE + " && false", passing))

    def test_a_comment_line_does_not_hide_the_check_after_it(self):
        command = "echo checking # build first\n" + GRADLE
        self.assertIn("build-doctor", failed_shell(command, gradle_summary("failed")))
        for command in ("echo ok;# note\n" + GRADLE, "echo ok;\n" + GRADLE, "echo ok # note\n\n" + GRADLE):
            self.assertIn("build-doctor", failed_shell(command, gradle_summary("failed")), command)
        self.assertIsNone(failed_shell("# " + GRADLE + "\nfalse", ""))

    def test_quoted_paths_and_powershell_call_operator_are_recognized(self):
        command = r'python "C:\Users\Paul Ayala\app\tools\agent-checks\gradle_summary.py" -- .\gradlew.bat :app:assembleDebug'
        self.assertIn("build-doctor", failed_shell(command, gradle_summary("failed"), tool="PowerShell"))
        command = r"& py -3 tools\agent-checks\test_summary.py --module feature\orders"
        summary = json.dumps({"schema_version": 2, "tool_versions": {"test_summary": "2"}, "status": "failed",
                              "next_step": "test-analyst"})
        self.assertIn("test-analyst", failed_shell(command, summary, tool="PowerShell"))

    def test_user_interrupt_and_subagents_are_left_alone(self):
        self.assertIsNone(failed_shell(GRADLE, gradle_summary("failed"), is_interrupt=True))
        self.assertIsNone(failed_shell(GRADLE, gradle_summary("failed"), agent_type="android-feature-kit:data-builder"))


class AgentReplies(unittest.TestCase):
    def test_failed_agent_with_a_failing_check(self):
        reply = ("Done what I could.\nSTATUS: failed\nFILES: ...\n"
                 "CHECKS: gradle_summary :feature:orders:testDebugUnitTest FAILED (2 tests)\nLIMITATIONS: None\n")
        message = agent_reply("android-feature-kit:data-builder", reply)
        self.assertIn("build-doctor", message)
        self.assertIn("test-analyst", message)

    def test_next_step_in_the_reply_picks_the_agent(self):
        reply = ('STATUS: blocked\nCHECKS: gradle_summary timed out on connectedDebugAndroidTest '
                 '{"status": "timeout", "next_step": "build-doctor"}\n')
        message = agent_reply("ui-builder", reply)
        self.assertIn("build-doctor (haiku)", message)
        self.assertNotIn("test-analyst", message)
        plain = ("STATUS: failed\nCHECKS:\n- testDebugUnitTest: status failed, next_step: test-analyst, "
                 "raw_log_path: build/agent-checks/gradle-2.log\nLIMITATIONS: None\n")
        message = agent_reply("domain-builder", plain)
        self.assertIn("test-analyst (haiku)", message)
        self.assertNotIn("build-doctor", message)

    def test_done_or_passing_checks_say_nothing(self):
        self.assertIsNone(agent_reply("data-builder", "STATUS: done\nCHECKS: compile and tests passed\n"))
        self.assertIsNone(agent_reply("data-builder", "STATUS: blocked\nQUESTIONS: which endpoint?\n"
                                                      "CHECKS: compile passed, no failures\n"))
        self.assertIsNone(agent_reply("data-builder", "STATUS: blocked\nCHECKS: tests passed; failures: 0\n"))
        self.assertIsNone(agent_reply("ui-builder", "STATUS: blocked\nCHECKS: ran with --timeout 9, 0 failed, passed\n"))

    def test_read_only_and_other_agents_are_ignored(self):
        reply = "STATUS: failed\nCHECKS: FAILED\n"
        self.assertIsNone(agent_reply("android-feature-kit:build-doctor", reply))
        self.assertIsNone(agent_reply("other-plugin:data-builder", reply))
        self.assertIsNone(agent_reply("Explore", reply))


class Script(unittest.TestCase):
    def run_script(self, payload):
        return subprocess.run([sys.executable, str(HOOKS / "failure_router.py")], input=payload, text=True,
                              capture_output=True)

    def test_note_goes_out_as_additional_context_and_exit_is_0(self):
        event = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "tool_input": {"command": GRADLE},
                 "error": "Exit code 1\n" + gradle_summary("failed"), "is_interrupt": False}
        result = self.run_script(json.dumps(event))
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUseFailure")
        self.assertIn("build-doctor", output["additionalContext"])

    def test_silent_cases_print_nothing(self):
        event = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "git status"},
                 "tool_response": {"stdout": "clean"}}
        for payload in (json.dumps(event), "not json"):
            result = self.run_script(payload)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
