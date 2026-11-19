"""Tests for the layer guard. Run from the plugin root: python -m unittest discover -s hooks/tests"""
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


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp(prefix="guard-project-")
        self.module = os.path.join(self.project, "feature", "orders")
        self.src = os.path.join(self.module, "src", "main", "kotlin", "com", "acme", "orders")

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def scope(self, *modules):
        path = os.path.join(self.project, "build", "android-feature-kit")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "scope.json"), "w", encoding="utf-8") as handle:
            json.dump({"modules": list(modules)}, handle)

    def write(self, agent, path, cwd=None):
        event = {"agent_type": agent, "tool_name": "Write", "tool_input": {"file_path": path}, "cwd": cwd or self.project}
        return layer_guard.decide(event, self.project)

    def shell(self, command, agent="android-feature-kit:data-builder", tool="Bash"):
        event = {"agent_type": agent, "tool_name": tool, "tool_input": {"command": command}, "cwd": self.project}
        return layer_guard.decide(event, self.project)

    def p(self, *parts):
        return os.path.join(self.project, *parts)


class AgentMatching(GuardTest):
    def test_main_session_and_other_plugins_are_ignored(self):
        self.assertIsNone(self.write(None, self.p("build.gradle.kts")))
        self.assertIsNone(self.write("other-plugin:data-builder", self.p("build.gradle.kts")))
        self.assertIsNone(self.write("reviewer", self.p("build.gradle.kts")))

    def test_prefixed_and_bare_names_match(self):
        self.assertIsNotNone(self.write("android-feature-kit:data-builder", self.p("build.gradle.kts")))
        self.assertIsNotNone(self.write("data-builder", self.p("build.gradle.kts")))


class LayerWrites(GuardTest):
    def test_layer_agents_write_in_their_layer(self):
        self.assertIsNone(self.write("domain-builder", os.path.join(self.src, "domain", "CancelOrderUseCase.kt")))
        self.assertIsNone(self.write("data-builder", os.path.join(self.src, "data", "di", "OrderDataModule.kt")))
        self.assertIsNone(self.write("ui-builder", os.path.join(self.src, "presentation", "OrderScreen.kt")))
        self.assertIsNone(self.write("ui-builder", os.path.join(self.src, "navigation", "OrdersGraph.kt")))
        self.assertIsNone(self.write("ui-builder", os.path.join(self.module, "src", "main", "res", "values", "strings.xml")))
        test = os.path.join(self.module, "src", "test", "kotlin", "com", "acme", "orders", "domain", "UseCaseTest.kt")
        self.assertIsNone(self.write("domain-builder", test))

    def test_layer_agents_are_blocked_outside_their_layer(self):
        self.assertIsNotNone(self.write("domain-builder", os.path.join(self.src, "data", "Repo.kt")))
        self.assertIsNotNone(self.write("data-builder", os.path.join(self.src, "domain", "Order.kt")))
        self.assertIsNotNone(self.write("ui-builder", os.path.join(self.src, "domain", "Order.kt")))
        self.assertIsNotNone(self.write("data-builder", self.p("gradle", "libs.versions.toml")))
        self.assertIsNotNone(self.write("ui-builder", os.path.join(self.module, "build.gradle.kts")))

    def test_traversal_and_outside_paths_are_blocked(self):
        sneaky = os.path.join(self.src, "data", "..", "domain", "Order.kt")
        self.assertIsNotNone(self.write("data-builder", sneaky))
        relative = "feature/orders/src/main/kotlin/com/acme/orders/data/../domain/Order.kt"
        self.assertIsNotNone(self.write("data-builder", relative))
        outside = os.path.join(tempfile.gettempdir(), "another-repo", "src", "main", "kotlin", "data", "X.kt")
        self.assertIsNotNone(self.write("data-builder", outside))

    def test_relative_paths_resolve_against_cwd(self):
        self.assertIsNone(self.write("data-builder", "src/main/kotlin/com/acme/orders/data/Repo.kt", cwd=self.module))
        self.assertIsNotNone(self.write("data-builder", "src/main/kotlin/com/acme/orders/domain/Repo.kt", cwd=self.module))

    def test_scope_limits_layer_agents_to_its_modules(self):
        self.scope("feature/orders")
        self.assertIsNone(self.write("data-builder", os.path.join(self.src, "data", "Repo.kt")))
        other = self.p("feature", "payments", "src", "main", "kotlin", "com", "acme", "payments", "data", "Repo.kt")
        self.assertIsNotNone(self.write("data-builder", other))

    def test_project_config_replaces_patterns(self):
        os.makedirs(self.p(".claude"))
        with open(self.p(".claude", "android-feature-kit.json"), "w", encoding="utf-8") as handle:
            json.dump({"layers": {"domain-builder": {"allow": ["**/src/*/kotlin/**/core/**"]}}}, handle)
        self.assertIsNone(self.write("domain-builder", os.path.join(self.src, "core", "Rule.kt")))
        self.assertIsNotNone(self.write("domain-builder", os.path.join(self.src, "domain", "Rule.kt")))


class IntegratorWrites(GuardTest):
    def test_needs_the_scope_file(self):
        self.assertIsNotNone(self.write("feature-integrator", self.p("gradle", "libs.versions.toml")))

    def test_writes_outside_the_scoped_modules_sources(self):
        self.scope("feature/orders")
        self.assertIsNone(self.write("feature-integrator", self.p("gradle", "libs.versions.toml")))
        self.assertIsNone(self.write("feature-integrator", os.path.join(self.module, "build.gradle.kts")))
        nav_host = self.p("app", "src", "main", "kotlin", "com", "acme", "app", "presentation", "navigation", "AppNavHost.kt")
        self.assertIsNone(self.write("feature-integrator", nav_host))
        self.assertIsNone(self.write("feature-integrator", self.p("core", "database", "src", "main", "kotlin", "AppDatabase.kt")))
        self.assertIsNotNone(self.write("feature-integrator", os.path.join(self.src, "navigation", "OrdersGraph.kt")))
        self.assertIsNotNone(self.write("feature-integrator", os.path.join(self.src, "domain", "Order.kt")))

    def test_read_only_agents_never_write(self):
        self.scope("feature/orders")
        for agent in ("build-doctor", "test-analyst", "android-reviewer", "android-architect"):
            self.assertIsNotNone(self.write(agent, self.p("notes.md")), agent)


class Shell(GuardTest):
    def test_gradle_and_reads_are_allowed(self):
        self.assertIsNone(self.shell("./gradlew :feature:orders:testDebugUnitTest --console=plain 2>&1 | tail -50"))
        self.assertIsNone(self.shell('rg -n "List<String>|Flow<Order>" feature/orders'))
        self.assertIsNone(self.shell("rg '>' feature/orders"))
        self.assertIsNone(self.shell("rg '`' feature/orders"))
        self.assertIsNone(self.shell("git -C feature status && git diff HEAD --stat"))
        self.assertIsNone(self.shell("ls feature/orders 2>/dev/null"))
        self.assertIsNone(self.shell('android docs search "Room 3"'))

    def test_check_scripts(self):
        self.assertIsNone(self.shell("python3 tools/agent-checks/gradle_summary.py -- ./gradlew :feature:orders:compileDebugKotlin"))
        self.assertIsNone(self.shell("python3 tools/agent-checks/gradle_summary.py --timeout 9 -- ./gradlew :app:connectedDebugAndroidTest"))
        self.assertIsNone(self.shell("python3 tools/agent-checks/gradle_summary.py --timeout=0 --max 5 -- ./gradlew :app:assembleDebug"))
        self.assertIsNone(self.shell(r'"C:\Users\x\AppData\Local\Android\android.exe" docs search room'))
        plugin_copy = layer_guard.PLUGIN_ROOT / "repo-tools" / "agent-checks" / "test_summary.py"
        self.assertIsNone(self.shell(f'python "{plugin_copy}" --module feature/orders'))
        self.assertIsNotNone(self.shell("python3 tools/agent-checks/gradle_summary.py -- rm -rf build"))
        self.assertIsNotNone(self.shell("python3 tools/agent-checks/gradle_summary.py --out src -- ./gradlew x"))
        self.assertIsNotNone(self.shell("python3 -c 'print(1)' tools/agent-checks/gradle_summary.py"))
        self.assertIsNotNone(self.shell("python3 -m gradle_summary"))
        self.assertIsNotNone(self.shell("python3 elsewhere/gradle_summary.py -- ./gradlew x"))

    def test_writes_and_execution_through_the_shell_are_blocked(self):
        for command in (
            "echo x > feature/orders/src/main/kotlin/A.kt",
            "cat <<EOF >> notes.md",
            "sed -i 's/a/b/' A.kt",
            "rm -rf build",
            "find . -name '*.kt' -delete",
            "ls; git commit -m wip",
            "git branch scratch",
            "git diff --output=outside.kt",
            "git diff --output outside.kt",
            "git -c core.pager=evil log",
            "git grep -Ovim pattern",
            "sort README.md -o outside.kt",
            "rg --pre ./evil.sh pattern",
            "android skills add x",
            'ls "$(rm -rf x)"',
            "ls `rm -rf x`",
            "codegraph init",
        ):
            self.assertIsNotNone(self.shell(command), command)

    def test_powershell(self):
        self.assertIsNone(self.shell(r".\gradlew.bat :feature:orders:testDebugUnitTest | Select-String 'FAILED'", tool="PowerShell"))
        self.assertIsNone(self.shell(r"Get-Content feature\orders\build.gradle.kts", tool="PowerShell"))
        self.assertIsNone(self.shell(r".\gradlew.bat build > $null", tool="PowerShell"))
        self.assertIsNotNone(self.shell(r"Set-Content -Path A.kt -Value x", tool="PowerShell"))
        self.assertIsNotNone(self.shell(r"Get-Content a.kt > b.kt", tool="PowerShell"))
        self.assertIsNotNone(self.shell(r"Get-Content README.md | Where-Object { Set-Content outside.kt x }", tool="PowerShell"))


class RoundTwo(GuardTest):
    def test_process_substitution_and_abbreviations_are_blocked(self):
        for command in (
            "cat <(touch outside.kt)",
            "cat < <(touch outside.kt)",
            "python3 tools/agent-checks/gradle_summary.py --ou src -- ./gradlew help",
            "git grep --open-files-in-page=sh -e needle",
            "git diff --out=outside.kt",
            "git --config-e=x log",
        ):
            self.assertIsNotNone(self.shell(command), command)
        self.assertIsNone(self.shell("git log --oneline -5"))
        self.assertIsNone(self.shell("python3 tools/agent-checks/test_summary.py --module feature/orders --max 5"))

    @unittest.skipUnless(os.name == "nt", "Git Bash paths exist only on Windows")
    def test_git_bash_paths(self):
        drive, rest = os.path.splitdrive(self.src)
        bash_path = "/" + drive[0].lower() + rest.replace("\\", "/") + "/data/Repo.kt"
        self.assertIsNone(self.write("data-builder", bash_path))

    def test_integrator_may_edit_the_feature_manifest(self):
        self.scope("feature/orders")
        self.assertIsNone(self.write("feature-integrator", os.path.join(self.module, "src", "main", "AndroidManifest.xml")))
        self.assertIsNotNone(self.write("feature-integrator", os.path.join(self.module, "src", "main", "res", "values", "x.xml")))


class Main(GuardTest):
    def test_exit_codes(self):
        script = HOOKS / "layer_guard.py"
        env = {**os.environ, "CLAUDE_PROJECT_DIR": self.project}
        blocked = {"agent_type": "android-feature-kit:ui-builder", "tool_name": "Write",
                   "tool_input": {"file_path": os.path.join(self.src, "data", "X.kt")}, "cwd": self.project}
        result = subprocess.run([sys.executable, str(script)], input=json.dumps(blocked), capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("layer guard", result.stderr)
        result = subprocess.run([sys.executable, str(script)], input=json.dumps(dict(blocked, agent_type=None)),
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0)
        result = subprocess.run([sys.executable, str(script)], input="not json", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
