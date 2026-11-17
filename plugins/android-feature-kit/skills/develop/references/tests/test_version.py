"""The develop skill's VERSION must match the plugin version. Run from the references folder: python -m unittest discover -s tests"""
import json
import unittest
from pathlib import Path

REFERENCES = Path(__file__).resolve().parents[1]
PLUGIN_JSON = REFERENCES.parents[2] / ".claude-plugin" / "plugin.json"


class VersionTest(unittest.TestCase):
    def test_version_file_matches_the_plugin(self):
        version = (REFERENCES / "VERSION").read_text(encoding="utf-8").strip()
        plugin = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
        self.assertEqual(version, plugin, "Bump skills/develop/references/VERSION together with .claude-plugin/plugin.json")


if __name__ == "__main__":
    unittest.main()
