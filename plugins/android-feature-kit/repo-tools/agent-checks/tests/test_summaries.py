"""Tests for the check scripts. Run from repo-tools/agent-checks: python -m unittest discover tests"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
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


class GradleTimeoutAndNextStep(unittest.TestCase):
    def run_script(self, root, body, *options):
        script = os.path.join(root, "fake.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(body)
        result = subprocess.run([sys.executable, str(HERE / "gradle_summary.py"), *options, "--", sys.executable, script],
                                cwd=root, capture_output=True, text=True, timeout=120)
        return result, json.loads(result.stdout)

    def test_timeout_stops_the_command_and_names_build_doctor(self):
        with tempfile.TemporaryDirectory() as root:
            result, summary = self.run_script(root, "import time\nprint('started', flush=True)\ntime.sleep(60)\n",
                                              "--timeout", "0.02")
            self.assertEqual(result.returncode, 124)
            self.assertEqual(summary["status"], "timeout")
            self.assertEqual(summary["next_step"], "build-doctor")
            self.assertEqual(summary["timeout_minutes"], 0.02)
            with open(os.path.join(root, summary["raw_log_path"]), encoding="utf-8") as handle:
                log = handle.read()
            self.assertIn("started", log)
            self.assertIn("Stopped after", log)

    def test_next_step_follows_what_failed(self):
        with tempfile.TemporaryDirectory() as root:
            _, compile_error = self.run_script(root, "import sys\nprint('e: A.kt:3:1 Unresolved reference')\nsys.exit(1)\n")
            self.assertEqual(compile_error["next_step"], "build-doctor")
            only_tests = ("import sys\nprint('> Task :app:testDebugUnitTest FAILED')\n"
                          "print('com.acme.ATest > works FAILED')\nsys.exit(1)\n")
            _, summary = self.run_script(root, only_tests)
            self.assertEqual(summary["next_step"], "test-analyst")
            _, truncated = self.run_script(root, only_tests, "--max", "0")
            self.assertEqual(truncated["next_step"], "test-analyst")
            _, passed = self.run_script(root, "print('BUILD SUCCESSFUL')\n")
            self.assertIsNone(passed["next_step"])
            self.assertEqual(passed["schema_version"], 2)

    def test_a_failing_test_does_not_hide_a_dependency_failure(self):
        parsed = gradle_summary.parse("\n".join([
            "> Task :app:checkDebugAarMetadata FAILED",
            "> Task :feature:orders:testDebugUnitTest FAILED",
            "com.acme.ATest > works FAILED",
        ]), "/repo", 20)
        self.assertEqual(gradle_summary.next_step("failed", parsed), "build-doctor")
        tests_only = gradle_summary.parse("> Task :app:connectedDebugAndroidTest FAILED\ncom.acme.UiTest > shows FAILED",
                                          "/repo", 20)
        self.assertEqual(gradle_summary.next_step("failed", tests_only), "test-analyst")
        no_task_line = gradle_summary.parse("com.acme.ATest > works FAILED", "/repo", 20)
        self.assertEqual(gradle_summary.next_step("failed", no_task_line), "build-doctor")

    def test_timeout_also_stops_the_processes_the_command_started(self):
        with tempfile.TemporaryDirectory() as root:
            marker = os.path.join(root, "worker-still-running")
            body = ("import subprocess, sys, time\n"
                    "subprocess.Popen([sys.executable, '-c', \"import sys, time; time.sleep(4); "
                    "open(sys.argv[1], 'w').write('x')\", " + repr(marker) + "])\n"
                    "print('started', flush=True)\ntime.sleep(60)\n")
            result, summary = self.run_script(root, body, "--timeout", "0.03")
            self.assertEqual(summary["status"], "timeout")
            time.sleep(6)
            self.assertFalse(os.path.exists(marker), "the worker kept running after the timeout")

    @unittest.skipIf(os.name == "nt", "process groups and SIGTERM forwarding are POSIX only")
    def test_stopping_the_script_stops_a_worker_that_ignores_sigterm(self):
        import signal
        with tempfile.TemporaryDirectory() as root:
            marker = os.path.join(root, "worker-still-running")
            script = os.path.join(root, "fake.py")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write(
                    "import subprocess, sys, time\n"
                    "subprocess.Popen([sys.executable, '-c', \"import signal, sys, time; "
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(10); open(sys.argv[1], 'w').write('x')\", "
                    + repr(marker) + "])\n"
                    "time.sleep(60)\n")
            process = subprocess.Popen([sys.executable, str(HERE / "gradle_summary.py"), "--", sys.executable, script],
                                       cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(1.5)
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=30)
            self.assertEqual(process.returncode, 128 + signal.SIGTERM)
            time.sleep(5)
            self.assertFalse(os.path.exists(marker), "a worker that ignores SIGTERM outlived the script")

    def test_next_step_and_log_come_before_the_long_lists(self):
        with tempfile.TemporaryDirectory() as root:
            result, _ = self.run_script(root, "import sys\nprint('e: A.kt:3:1 Unresolved reference')\nsys.exit(1)\n")
            self.assertLess(result.stdout.index('"next_step"'), result.stdout.index('"failures"'))
            self.assertLess(result.stdout.index('"raw_log_path"'), result.stdout.index('"failures"'))

    def test_connected_tasks_get_a_default_timeout(self):
        self.assertEqual(gradle_summary.default_timeout(["./gradlew", ":app:connectedDebugAndroidTest"]), 9.0)
        self.assertEqual(gradle_summary.default_timeout(["gradlew.bat", "connectedCheck", "--console=plain"]), 9.0)
        self.assertIsNone(gradle_summary.default_timeout(["./gradlew", ":app:assembleDebug", "-Pconnected=true"]))

    def test_wrapper_is_found_in_a_parent_folder_up_to_the_repository_root(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".git"))
            sub = os.path.join(root, "feature", "orders")
            os.makedirs(sub)
            self.assertIsNone(gradle_summary.find_wrapper_root(sub))
            for name in ("gradlew", "gradlew.bat"):
                with open(os.path.join(root, name), "w", encoding="utf-8") as handle:
                    handle.write("")
            self.assertEqual(os.path.normcase(gradle_summary.find_wrapper_root(sub)), os.path.normcase(os.path.abspath(root)))

    def test_runs_the_parent_wrapper_from_a_subfolder(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".git"))
            sub = os.path.join(root, "feature", "orders")
            os.makedirs(sub)
            if os.name == "nt":
                with open(os.path.join(root, "gradlew.bat"), "w", encoding="utf-8") as handle:
                    handle.write("@echo off\r\necho ^> Task :app:assembleDebug FAILED\r\nexit /b 2\r\n")
            else:
                path = os.path.join(root, "gradlew")
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("#!/bin/sh\necho '> Task :app:assembleDebug FAILED'\nexit 2\n")
                os.chmod(path, 0o755)
            result = subprocess.run([sys.executable, str(HERE / "gradle_summary.py"), "--", "./gradlew", ":app:assembleDebug"],
                                    cwd=sub, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 2, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["failed_tasks"], [":app:assembleDebug"])
            self.assertEqual(os.path.normcase(summary["working_directory"]),
                             os.path.normcase(os.path.abspath(root).replace("\\", "/")))
            self.assertTrue(os.path.exists(os.path.join(root, summary["raw_log_path"])))

    def test_an_explicit_wrapper_path_runs_as_given(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".git"))
            for folder in (root, os.path.join(root, "android")):
                os.makedirs(folder, exist_ok=True)
                open(os.path.join(folder, gradle_summary.WRAPPER), "w").close()
            android = os.path.join(root, "android")
            wrapper, run_from = gradle_summary.resolve_wrapper("./android/gradlew", root)
            self.assertEqual(os.path.normcase(wrapper), os.path.normcase(os.path.join(android, gradle_summary.WRAPPER)))
            self.assertEqual(run_from, root)
            sub = os.path.join(root, "feature")
            os.makedirs(sub)
            wrapper, run_from = gradle_summary.resolve_wrapper("./gradlew", sub)
            self.assertEqual(os.path.normcase(run_from), os.path.normcase(os.path.abspath(root)))
            wrapper, run_from = gradle_summary.resolve_wrapper("./missing/gradlew", sub)
            self.assertEqual(run_from, sub)  # a wrong explicit path fails as before, with exit code 127


class TestSummary(unittest.TestCase):
    def test_failures_name_test_analyst(self):
        with tempfile.TemporaryDirectory() as module:
            results = os.path.join(module, "build", "test-results", "testDebugUnitTest")
            os.makedirs(results)
            with open(os.path.join(results, "TEST-x.xml"), "w", encoding="utf-8") as handle:
                handle.write(JUNIT_XML)
            result = subprocess.run([sys.executable, str(HERE / "test_summary.py"), "--module", module],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["next_step"], "test-analyst")
            self.assertEqual(summary["schema_version"], 2)

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
