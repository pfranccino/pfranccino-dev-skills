"""Tests for run_review.py. Run from the references folder: python -m unittest discover -s tests"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_review  # noqa: E402

IDENTITY = {"run_id": "review-1", "round": 1, "source_revision": "abc", "diff_hash": "def", "rules_version": "0.4.0"}


def answer(**overrides) -> dict:
    value = dict(IDENTITY, verdict="READY", summary="ok", findings=[], responses_to_previous=[], open_questions=[],
                 checks_run=[], limitations=[])
    value.update(overrides)
    return value


class RunReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous = os.getcwd()
        os.chdir(self.root)
        prompt = self.root / "build" / "android-feature-kit" / "review" / "round-1-prompt.md"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("Review this change.", encoding="utf-8")

    def tearDown(self):
        os.chdir(self.previous)
        self.temp.cleanup()

    def fake_tool(self, body: str) -> str:
        script = self.root / "fake_reviewer.py"
        script.write_text(textwrap.dedent(body), encoding="utf-8")
        return str(script)

    def configure(self, command: list[str], **extra):
        config = self.root / ".claude" / "android-feature-kit.json"
        config.parent.mkdir(exist_ok=True)
        config.write_text(json.dumps({"reviewer": dict(command=command, **extra)}), encoding="utf-8")

    def run_round(self, *extra: str) -> tuple[int, dict]:
        argv = ["--round", "1", "--run-id", "review-1", "--source-revision", "abc", "--diff-hash", "def",
                "--rules-version", "0.4.0", *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_review.main(argv)
        return code, json.loads(out.getvalue())

    def writes_answer(self, value: dict) -> list[str]:
        script = self.fake_tool(f"""
            import json, sys
            sys.stdin.read()
            open(sys.argv[1], "w", encoding="utf-8").write(json.dumps({value!r}))
        """)
        return [sys.executable, script, "{output}"]

    def test_valid_answer_in_the_output_file(self):
        self.configure(self.writes_answer(answer()), name="Fake")
        code, result = self.run_round()
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["reviewer"], "Fake")
        self.assertEqual(result["verdict"], "READY")
        self.assertTrue((self.root / "build/android-feature-kit/review/round-1.json").is_file())
        self.assertTrue((self.root / "build/android-feature-kit/review/round-1.log").is_file())

    def test_answer_on_standard_output_inside_a_code_block(self):
        script = self.fake_tool(f"""
            import json, sys
            sys.stdin.read()
            print("Here is the review:")
            print("```json")
            print(json.dumps({answer()!r}))
            print("```")
        """)
        self.configure([sys.executable, script])
        code, result = self.run_round()
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "ok")

    def test_the_prompt_arrives_on_standard_input(self):
        script = self.fake_tool(f"""
            import json, sys
            prompt = sys.stdin.read()
            value = {answer()!r}
            value["summary"] = prompt
            print(json.dumps(value))
        """)
        self.configure([sys.executable, script])
        code, _ = self.run_round()
        self.assertEqual(code, 0)
        saved = json.loads((self.root / "build/android-feature-kit/review/round-1.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["summary"], "Review this change.")

    def test_identity_mismatch_is_invalid(self):
        self.configure(self.writes_answer(answer(diff_hash="other")))
        code, result = self.run_round()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("diff_hash" in problem for problem in result["problems"]))

    def test_schema_violation_is_invalid(self):
        bad_finding = {"id": "C1", "severity": "critical", "rule": "DOM-01", "file": "a.kt", "line": 3, "claim": "x",
                       "evidence": "y", "recommendation": "z", "owner": "domain-builder", "confidence": "high"}
        self.configure(self.writes_answer(answer(verdict="NOT_READY", findings=[bad_finding], extra=1)))
        code, result = self.run_round()
        self.assertEqual(code, 1)
        problems = " ".join(result["problems"])
        self.assertIn("severity", problems)
        self.assertIn("extra is not allowed", problems)

    def test_missing_fields_are_invalid(self):
        value = answer()
        del value["limitations"]
        self.configure(self.writes_answer(value))
        code, result = self.run_round()
        self.assertEqual(code, 1)
        self.assertIn("$.limitations is missing", result["problems"])

    def test_tool_failure(self):
        script = self.fake_tool("""
            import sys
            sys.stdin.read()
            sys.exit(3)
        """)
        self.configure([sys.executable, script])
        code, result = self.run_round()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "failed")

    def test_no_json_in_the_answer(self):
        script = self.fake_tool("""
            import sys
            sys.stdin.read()
            print("Looks good to me.")
        """)
        self.configure([sys.executable, script])
        code, result = self.run_round()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "invalid")

    def test_not_configured(self):
        code, result = self.run_round()
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "not_configured")

    def test_command_not_found(self):
        self.configure(["no-such-reviewer-command-xyz", "{output}"])
        code, result = self.run_round()
        self.assertEqual(code, 2)
        self.assertIn("not found", result["problems"][0])

    def test_missing_prompt(self):
        self.configure(self.writes_answer(answer()))
        code, result = self.run_round("--prompt", "nowhere.md")
        self.assertEqual(code, 2)

    def test_stale_answer_is_not_reused(self):
        stale = self.root / "build/android-feature-kit/review/round-1.json"
        stale.write_text(json.dumps(answer()), encoding="utf-8")
        script = self.fake_tool("""
            import sys
            sys.stdin.read()
        """)
        self.configure([sys.executable, script, "{output}"])
        code, result = self.run_round()
        self.assertEqual(code, 1)
        self.assertIn("no answer file", result["problems"][0])


if __name__ == "__main__":
    unittest.main()
