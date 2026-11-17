"""Tests for the check scripts. Run from repo-tools/agent-checks: python -m unittest discover tests"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import gradle_summary  # noqa: E402
import test_summary  # noqa: E402

GRADLE_LOG = """\
> Task :core:model:compileKotlin UP-TO-DATE
> Task :feature:orders:compileDebugKotlin FAILED
e: file:///C:/code/app/feature/orders/src/main/kotlin/com/acme/orders/data/OrderRepositoryImpl.kt:42:17 Unresolved reference 'toDomain'.
w: file:///C:/code/app/feature/orders/src/main/kotlin/com/acme/orders/domain/Order.kt:3:1 Parameter 'x' is never used
e: /home/ci/app/feature/orders/src/main/kotlin/com/acme/orders/ui/OrderScreen.kt: (10, 5): Type mismatch
/home/ci/app/legacy/src/main/java/com/acme/Legacy.java:7: error: cannot find symbol
ERROR: C:\\code\\app\\feature\\orders\\src\\main\\res\\values\\strings.xml:3: AAPT: error: resource string/missing not found.
com.acme.orders.domain.CancelOrderUseCaseTest > cancelsOpenOrder FAILED

FAILURE: Build failed with an exception.

* What went wrong:
Execution failed for task ':feature:orders:compileDebugKotlin'.
> A failure occurred while executing org.jetbrains.kotlin.compilerRunner.GradleCompilerRunnerWithWorkers$GradleKotlinCompilerWorkAction
   > Compilation error. See log for more details

* Try:
> Run with --stacktrace option to get the stack trace.
"""

JUNIT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.acme.orders.domain.CancelOrderUseCaseTest" tests="3" skipped="1" failures="1" errors="1">
  <testcase name="cancelsOpenOrder" classname="com.acme.orders.domain.CancelOrderUseCaseTest" time="0.01">
    <failure message="expected:&lt;Right&gt; but was:&lt;Left(AlreadyDelivered)&gt;" type="java.lang.AssertionError">java.lang.AssertionError: expected
	at org.junit.Assert.fail(Assert.java:89)
	at com.acme.orders.domain.CancelOrderUseCaseTest$cancelsOpenOrder$1.invokeSuspend(CancelOrderUseCaseTest.kt:31)
	at kotlinx.coroutines.test.TestBuildersKt.runTest(TestBuilders.kt:10)
</failure>
  </testcase>
  <testcase name="crashes" classname="com.acme.orders.domain.CancelOrderUseCaseTest" time="0.01">
    <error message="boom" type="java.lang.IllegalStateException">java.lang.IllegalStateException: boom
	at com.acme.orders.domain.CancelOrderUseCase.invoke(CancelOrderUseCase.kt:12)
</error>
  </testcase>
  <testcase name="skipped" classname="com.acme.orders.domain.CancelOrderUseCaseTest"><skipped/></testcase>
</testsuite>
"""


class GradleSummary(unittest.TestCase):
    def test_parses_tasks_errors_and_tests(self):
        parsed = gradle_summary.parse(GRADLE_LOG, "C:/code/app", 20)
        self.assertEqual(parsed["failed_tasks"], [":feature:orders:compileDebugKotlin"])
        files = [(f["kind"], f["file"], f["line"]) for f in parsed["failures"]]
        self.assertIn(("kotlin", "feature/orders/src/main/kotlin/com/acme/orders/data/OrderRepositoryImpl.kt", 42), files)
        self.assertIn(("kotlin", "/home/ci/app/feature/orders/src/main/kotlin/com/acme/orders/ui/OrderScreen.kt", 10), files)
        self.assertIn(("java", "/home/ci/app/legacy/src/main/java/com/acme/Legacy.java", 7), files)
        self.assertIn(("resource", "feature/orders/src/main/res/values/strings.xml", 3), files)
        self.assertEqual(parsed["warnings"]["count"], 1)
        self.assertEqual(parsed["failed_tests"], ["com.acme.orders.domain.CancelOrderUseCaseTest > cancelsOpenOrder"])
        self.assertIn("compileDebugKotlin", parsed["what_went_wrong"])
        self.assertEqual(parsed["failures"][0]["task"], ":feature:orders:compileDebugKotlin")

    def test_runs_the_command_and_keeps_its_exit_code(self):
        with tempfile.TemporaryDirectory() as root:
            script = os.path.join(root, "fake.py")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("import sys\nprint('> Task :a:compileKotlin FAILED')\nsys.exit(3)\n")
            result = subprocess.run(
                [sys.executable, str(HERE / "gradle_summary.py"), "--out", "logs", "--", sys.executable, script],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 3)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["failed_tasks"], [":a:compileKotlin"])
            self.assertIsNotNone(summary["note"])
            self.assertTrue(os.path.exists(os.path.join(root, summary["raw_log_path"])))

    def test_requires_a_command(self):
        result = subprocess.run([sys.executable, str(HERE / "gradle_summary.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 64)


class GradleFormats(unittest.TestCase):
    def test_paths_with_spaces_ksp_and_aapt_without_prefix(self):
        log = "\n".join([
            "e: file:///C:/Users/Paul%20Ayala/app/feature/orders/src/main/kotlin/A.kt:3:9 Unresolved reference 'x'.",
            "e: C:/Users/Paul Ayala/app/feature/orders/src/main/kotlin/B.kt:4:1 Type mismatch",
            "e: [ksp] C:/Users/Paul Ayala/app/feature/orders/src/main/kotlin/C.kt:7: Missing binding",
            "C:/Users/Paul Ayala/app/legacy/src/main/java/D.java:8: error: cannot find symbol",
            "C:/Users/Paul Ayala/app/feature/orders/src/main/res/values/strings.xml:2: AAPT: error: resource not found.",
        ])
        parsed = gradle_summary.parse(log, "C:/Users/Paul Ayala/app", 20)
        found = {(f["kind"], f["file"], f["line"]) for f in parsed["failures"]}
        self.assertEqual(found, {
            ("kotlin", "feature/orders/src/main/kotlin/A.kt", 3),
            ("kotlin", "feature/orders/src/main/kotlin/B.kt", 4),
            ("ksp", "feature/orders/src/main/kotlin/C.kt", 7),
            ("java", "legacy/src/main/java/D.java", 8),
            ("resource", "feature/orders/src/main/res/values/strings.xml", 2),
        })

    def test_parallel_runs_keep_separate_logs(self):
        with tempfile.TemporaryDirectory() as root:
            script = os.path.join(root, "ok.py")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("print('ok')\n")
            command = [sys.executable, str(HERE / "gradle_summary.py"), "--", sys.executable, script]
            first = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, text=True)
            second = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, text=True)
            paths = {json.loads(first.communicate()[0])["raw_log_path"], json.loads(second.communicate()[0])["raw_log_path"]}
            self.assertEqual(len(paths), 2)


class TestSummary(unittest.TestCase):
    def test_reports_failures_with_own_frames(self):
        with tempfile.TemporaryDirectory() as module:
            results = os.path.join(module, "build", "test-results", "testDebugUnitTest")
            os.makedirs(results)
            with open(os.path.join(results, "TEST-x.xml"), "w", encoding="utf-8") as handle:
                handle.write(JUNIT_XML)
            source = os.path.join(module, "src", "main", "kotlin", "com", "acme", "orders", "domain")
            os.makedirs(source)
            open(os.path.join(source, "CancelOrderUseCase.kt"), "w").close()
            summary = test_summary.summarize(test_summary.report_files([module]), module, 20)
            self.assertEqual(summary["totals"], {"tests": 3, "failures": 1, "errors": 1, "skipped": 1})
            first, second = summary["failures"]
            self.assertEqual(first["test"], "cancelsOpenOrder")
            self.assertEqual(first["location"]["file"], "CancelOrderUseCaseTest.kt")
            self.assertEqual(first["location"]["line"], 31)
            self.assertTrue(second["location"]["file"].endswith("domain/CancelOrderUseCase.kt"))
            self.assertIn("Right", first["message"])

    def test_nested_suites_count_each_test_once(self):
        nested = ('<testsuites><testsuite name="outer"><testsuite name="inner">'
                  '<testcase classname="A" name="t"><failure message="boom">x</failure></testcase>'
                  '</testsuite></testsuite></testsuites>')
        with tempfile.TemporaryDirectory() as module:
            results = os.path.join(module, "build", "test-results", "testDebugUnitTest")
            os.makedirs(results)
            with open(os.path.join(results, "TEST-nested.xml"), "w", encoding="utf-8") as handle:
                handle.write(nested)
            summary = test_summary.summarize(test_summary.report_files([module]), module, 20)
            self.assertEqual(summary["totals"]["tests"], 1)
            self.assertEqual(summary["failures_total"], 1)

    def test_unreadable_report_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as module:
            results = os.path.join(module, "build", "test-results", "testDebugUnitTest")
            os.makedirs(results)
            with open(os.path.join(results, "TEST-good.xml"), "w", encoding="utf-8") as handle:
                handle.write('<testsuite><testcase classname="A" name="ok"/></testsuite>')
            with open(os.path.join(results, "TEST-broken.xml"), "w", encoding="utf-8") as handle:
                handle.write('<testsuite><testcase classname="A" name="bad"><failure')
            result = subprocess.run([sys.executable, str(HERE / "test_summary.py"), "--module", module],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "incomplete")
            self.assertEqual(len(summary["unreadable"]), 1)

    def test_no_reports(self):
        with tempfile.TemporaryDirectory() as module:
            result = subprocess.run([sys.executable, str(HERE / "test_summary.py"), "--module", module],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "no_results")


if __name__ == "__main__":
    unittest.main()
