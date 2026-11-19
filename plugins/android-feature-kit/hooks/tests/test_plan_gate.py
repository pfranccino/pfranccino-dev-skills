"""Tests for the plan gate. Run from the plugin root: python -m unittest discover -s hooks/tests"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

import layer_guard  # noqa: E402
import plan_gate  # noqa: E402

PLAN = """# Cancel an order

Goal: the user cancels an order from its detail screen.
Modules: feature/orders
Agents: domain-builder (sonnet), data-builder (haiku), ui-builder (sonnet)
Work: domain first, then data and ui in parallel.
Review: android-reviewer, up to 2 rounds
"""


class PlanGateTest(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp(prefix="gate-project-")

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def enable_gate(self, value=True):
        os.makedirs(os.path.join(self.project, ".claude"), exist_ok=True)
        with open(os.path.join(self.project, ".claude", "android-feature-kit.json"), "w", encoding="utf-8") as handle:
            json.dump({"planGate": value}, handle)

    def scope(self, session_id):
        path = os.path.join(self.project, "build", "android-feature-kit")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "scope.json"), "w", encoding="utf-8") as handle:
            json.dump({"modules": ["feature/orders"], "session_id": session_id}, handle)

    def approve(self, plan=PLAN, session="s1", approved=None):
        event = {"hook_event_name": "PostToolUse", "tool_name": "ExitPlanMode", "session_id": session,
                 "tool_input": {"plan": plan, "planFilePath": "/plans/cancel-order.md"},
                 "tool_response": {"plan": approved if approved is not None else plan,
                                   "filePath": "/plans/cancel-order.md"}}
        return plan_gate.decide(event, self.project)

    def launch(self, agent, session="s1", tool="Agent", model=None):
        tool_input = {"subagent_type": agent, "prompt": "do it"}
        if model:
            tool_input["model"] = model
        event = {"hook_event_name": "PreToolUse", "tool_name": tool, "session_id": session, "tool_input": tool_input}
        return plan_gate.decide(event, self.project)

    def record(self):
        with open(os.path.join(self.project, "build", "android-feature-kit", "approved-plan.json"), encoding="utf-8") as handle:
            return json.load(handle)


class GateOff(PlanGateTest):
    def test_launches_pass_without_a_plan(self):
        self.assertIsNone(self.launch("android-feature-kit:domain-builder"))

    def test_approval_is_not_recorded(self):
        self.assertIsNone(self.approve())
        self.assertFalse(os.path.exists(os.path.join(self.project, "build", "android-feature-kit", "approved-plan.json")))

    def test_only_true_turns_it_on(self):
        self.enable_gate("yes")
        self.assertIsNone(self.launch("android-feature-kit:domain-builder"))


class GateOn(PlanGateTest):
    def setUp(self):
        super().setUp()
        self.enable_gate()

    def test_writing_agent_needs_an_approved_plan(self):
        problem = self.launch("android-feature-kit:domain-builder")
        self.assertIn("no plan approved", problem)

    def test_read_only_and_other_agents_pass(self):
        self.assertIsNone(self.launch("android-feature-kit:build-doctor"))
        self.assertIsNone(self.launch("android-feature-kit:android-reviewer"))
        self.assertIsNone(self.launch("Explore"))
        self.assertIsNone(self.launch("other-plugin:domain-builder"))

    def test_approval_records_the_agents_line(self):
        self.assertIsNone(self.approve())
        record = self.record()
        self.assertEqual(record["session_id"], "s1")
        self.assertEqual(record["agents"], ["domain-builder", "data-builder", "ui-builder"])
        self.assertEqual(record["models"], {"domain-builder": "sonnet", "data-builder": "haiku", "ui-builder": "sonnet"})
        self.assertEqual(record["plan_file"], "/plans/cancel-order.md")

    def test_the_plan_as_approved_wins_over_the_submitted_one(self):
        edited = PLAN.replace("Agents: domain-builder (sonnet), data-builder (haiku), ui-builder (sonnet)",
                              "Agents: ui-builder (sonnet)")
        self.approve(plan=PLAN, approved=edited)
        self.assertEqual(self.record()["agents"], ["ui-builder"])
        self.assertIsNotNone(self.launch("android-feature-kit:domain-builder"))

    def test_plan_only_in_the_response(self):
        event = {"hook_event_name": "PostToolUse", "tool_name": "ExitPlanMode", "session_id": "s1",
                 "tool_input": {}, "tool_response": {"plan": PLAN, "filePath": "/plans/x.md"}}
        self.assertIsNone(plan_gate.decide(event, self.project))
        self.assertEqual(self.record()["plan_file"], "/plans/x.md")
        self.assertIn("data-builder", self.record()["agents"])

    def test_model_must_match_the_plan(self):
        self.approve()
        self.assertIsNone(self.launch("android-feature-kit:data-builder", model="haiku"))
        self.assertIsNone(self.launch("android-feature-kit:data-builder"))  # its default model is haiku
        problem = self.launch("android-feature-kit:data-builder", model="sonnet")
        self.assertIn("runs data-builder on haiku", problem)

    def test_planned_model_other_than_the_default_needs_the_model_set(self):
        self.approve(plan="Agents: data-builder (sonnet)\n")
        self.assertIn("on sonnet", self.launch("android-feature-kit:data-builder"))
        self.assertIsNone(self.launch("android-feature-kit:data-builder", model="sonnet"))

    def test_markdown_around_names_keeps_the_model(self):
        self.approve(plan="Agents: `data-builder` (sonnet), **ui-builder** (`sonnet`)\n")
        self.assertEqual(self.record()["models"], {"data-builder": "sonnet", "ui-builder": "sonnet"})
        self.assertIsNotNone(self.launch("android-feature-kit:data-builder", model="haiku"))
        self.assertIsNone(self.launch("android-feature-kit:data-builder", model="sonnet"))

    def test_markdown_around_the_parenthesis_keeps_the_model(self):
        for plan in ("Agents: data-builder **(sonnet)**\n", "Agents: data-builder _(**sonnet**)_\n",
                     "Agents: `data-builder` *(sonnet)*, ui-builder (sonnet)\n"):
            self.approve(plan=plan)
            self.assertEqual(self.record()["models"].get("data-builder"), "sonnet", plan)
            self.assertIsNotNone(self.launch("android-feature-kit:data-builder", model="haiku"), plan)

    def test_an_agent_without_a_model_in_a_plan_that_gives_models_is_blocked(self):
        message = self.approve(plan="Agents: domain-builder (sonnet), data-builder - haiku\n")
        self.assertIn("could not read the model for data-builder", message)
        self.assertIsNotNone(self.launch("android-feature-kit:data-builder", model="haiku"))
        self.assertIsNone(self.launch("android-feature-kit:domain-builder", model="sonnet"))

    def test_unreadable_model_blocks_the_agent_and_warns(self):
        message = self.approve(plan="Agents: data-builder (the cheap one), ui-builder (sonnet)\n")
        self.assertIn("could not read the model for data-builder", message)
        self.assertIn("cannot read", self.launch("android-feature-kit:data-builder", model="haiku"))
        self.assertIsNone(self.launch("android-feature-kit:ui-builder", model="sonnet"))

    def test_no_model_in_the_plan_means_no_model_check(self):
        self.approve(plan="Agents: ui-builder\n")
        self.assertIsNone(self.launch("android-feature-kit:ui-builder", model="opus"))

    def test_default_models_come_from_the_agent_files(self):
        self.assertEqual(plan_gate.default_model("data-builder"), "haiku")
        self.assertEqual(plan_gate.default_model("domain-builder"), "sonnet")

    def test_listed_agents_pass_and_others_are_blocked(self):
        self.approve()
        self.assertIsNone(self.launch("android-feature-kit:domain-builder"))
        self.assertIsNone(self.launch("data-builder", tool="Task"))
        problem = self.launch("android-feature-kit:feature-integrator")
        self.assertIn("not in the approved plan", problem)

    def test_plan_from_another_session_does_not_count(self):
        self.approve(session="s1")
        self.assertIn("no plan approved", self.launch("android-feature-kit:domain-builder", session="s2"))

    def test_bold_label_and_list_under_it(self):
        plan = "**Agents:**\n- android-feature-kit:ui-builder (sonnet): the screen\n- feature-integrator (sonnet)\n\nWork: x\n"
        self.approve(plan=plan)
        self.assertEqual(self.record()["agents"], ["ui-builder", "feature-integrator"])

    def test_agents_mentioned_outside_the_agents_line_do_not_count(self):
        plan = "Agents: ui-builder (sonnet)\nWork: domain-builder is not needed; the contract exists.\n"
        self.approve(plan=plan)
        self.assertEqual(self.record()["agents"], ["ui-builder"])
        self.assertIsNotNone(self.launch("android-feature-kit:domain-builder"))

    def test_plan_without_agents_line_warns(self):
        message = self.approve(plan="Goal: small fix in the data layer, done in this session.\n")
        self.assertIn("no writing agents", message)
        self.assertEqual(self.record()["agents"], [])

    def test_plan_read_from_the_plan_file_when_neither_input_nor_response_has_it(self):
        plan_file = os.path.join(self.project, "plan.md")
        with open(plan_file, "w", encoding="utf-8") as handle:
            handle.write(PLAN)
        event = {"hook_event_name": "PostToolUse", "tool_name": "ExitPlanMode", "session_id": "s1",
                 "tool_input": {"planFilePath": plan_file}}
        self.assertIsNone(plan_gate.decide(event, self.project))
        self.assertIn("domain-builder", self.record()["agents"])

    def test_a_new_approval_replaces_the_previous_one(self):
        self.approve()
        self.approve(plan="Agents: feature-integrator (sonnet)\n")
        self.assertIsNotNone(self.launch("android-feature-kit:domain-builder"))
        self.assertIsNone(self.launch("android-feature-kit:feature-integrator"))


class CheckoutOwnership(PlanGateTest):
    def test_scope_of_another_session_blocks_writing_agents(self):
        self.scope("other-session")
        problem = self.launch("android-feature-kit:data-builder", session="s1")
        self.assertIn("Only one run works in a checkout", problem)

    def test_own_scope_passes(self):
        self.scope("s1")
        self.assertIsNone(self.launch("android-feature-kit:data-builder", session="s1"))

    def test_read_only_agents_are_not_blocked(self):
        self.scope("other-session")
        self.assertIsNone(self.launch("android-feature-kit:test-analyst", session="s1"))

    def test_scope_without_a_real_session_id_is_ignored(self):
        for value in (None, "", "${CLAUDE_SESSION_ID}"):
            self.scope(value)
            self.assertIsNone(self.launch("android-feature-kit:data-builder", session="s1"))


class KitRecordProtection(PlanGateTest):
    def guard(self, tool, tool_input, agent=None, session="s1"):
        event = {"tool_name": tool, "tool_input": tool_input, "cwd": self.project, "session_id": session}
        if agent:
            event["agent_type"] = agent
        return layer_guard.decide(event, self.project)

    def scope_path(self):
        return os.path.join(self.project, "build", "android-feature-kit", "scope.json")

    def test_another_sessions_scope_cannot_be_replaced(self):
        self.scope("other-session")
        self.assertIn("belongs to another Claude session", self.guard("Write", {"file_path": self.scope_path()}))
        self.assertIn("belongs to another Claude session", self.guard("Bash", {"command": "rm build/android-feature-kit/scope.json"}))

    def test_own_or_unowned_scope_can_be_written(self):
        self.assertIsNone(self.guard("Write", {"file_path": self.scope_path()}))
        self.scope("s1")
        self.assertIsNone(self.guard("Write", {"file_path": self.scope_path()}))
        self.assertIsNone(self.guard("Bash", {"command": "rm build/android-feature-kit/scope.json"}))

    def test_kit_agents_never_write_the_kit_files(self):
        self.scope("s1")
        problem = self.guard("Write", {"file_path": self.scope_path()}, agent="android-feature-kit:feature-integrator")
        self.assertIn("kit's own files", problem)

    def test_main_session_cannot_write_the_record(self):
        path = os.path.join(self.project, "build", "android-feature-kit", "approved-plan.json")
        self.assertIn("Only the plan gate", self.guard("Write", {"file_path": path}))
        self.assertIn("Only the plan gate", self.guard("Edit", {"file_path": "build/android-feature-kit/approved-plan.json"}))

    def test_shell_commands_cannot_touch_it(self):
        self.assertIn("Only the plan gate", self.guard("Bash", {"command": "echo '{}' > build/android-feature-kit/approved-plan.json"}))
        self.assertIn("Only the plan gate", self.guard("PowerShell", {"command": "Remove-Item build\\android-feature-kit\\Approved-Plan.json"}))
        heredoc = "cat > build/notes.md <<'EOF'\nThe plan gate reads approved-plan.json.\nEOF"
        self.assertIn("use the Write tool", self.guard("Bash", {"command": heredoc}))

    def test_other_files_are_untouched(self):
        self.assertIsNone(self.guard("Write", {"file_path": os.path.join(self.project, "build", "android-feature-kit", "scope.json")}))
        self.assertIsNone(self.guard("Bash", {"command": "git status"}))


class ScriptEntryPoint(PlanGateTest):
    def run_script(self, event):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project)
        return subprocess.run([sys.executable, str(HOOKS / "plan_gate.py")], input=json.dumps(event), text=True,
                              capture_output=True, env=env)

    def test_blocked_launch_exits_2_with_a_message(self):
        self.enable_gate()
        result = self.run_script({"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": "s1",
                                  "tool_input": {"subagent_type": "android-feature-kit:ui-builder"}})
        self.assertEqual(result.returncode, 2)
        self.assertIn("[android-feature-kit plan gate]", result.stderr)

    def test_allowed_launch_and_bad_input_exit_0(self):
        result = self.run_script({"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": "s1",
                                  "tool_input": {"subagent_type": "android-feature-kit:ui-builder"}})
        self.assertEqual(result.returncode, 0)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project)
        bad = subprocess.run([sys.executable, str(HOOKS / "plan_gate.py")], input="not json", text=True,
                             capture_output=True, env=env)
        self.assertEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
