import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "skills/gate-check/scripts/check.py"
ROUTE = ROOT / "skills/vault-route/scripts/route.py"


class Helpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".git")
        self.path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_helper(self, script, *args):
        result = subprocess.run([sys.executable, str(script), *map(str, args)],
                                capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def gate(self, output, code=0, config="[scoring]\npassing_score = 75\n"):
        stub = self.path / "observer"
        stub.write_text(f"#!{sys.executable}\nimport sys\nsys.stdin.read()\nprint({output!r})\nsys.exit({code})\n")
        stub.chmod(0o755)
        spec = self.path / "spec.toml"
        spec.write_text(config)
        text = self.path / "response.txt"
        text.write_text("A synthetic response.")
        return self.run_helper(GATE, "--text-file", text, "--config", spec, "--binary", stub)

    def test_score_pass_is_not_action_approval(self):
        code, data = self.gate("Class: generic\nScore: 75/100\nNo violations.")
        self.assertEqual((code, data["status"]), (0, "pass"))
        self.assertFalse(data["action_authorized"])

    def test_successful_process_can_have_failing_score(self):
        code, data = self.gate("Class: generic\nScore: 74/100\nA violation.")
        self.assertEqual((code, data["status"]), (1, "fail"))

    def test_errors_never_pass(self):
        for output, exit_code, config in [
            ("Class: generic\nScore: 100/100", 3, "[scoring]\npassing_score = 75\n"),
            ("garbled", 0, "[scoring]\npassing_score = 75\n"),
            ("Class: generic\nScore: 101/100", 0, "[scoring]\npassing_score = 75\n"),
            ("Class: generic\nScore: 100/100", 0, "[scoring]\npassing_score = true\n"),
        ]:
            with self.subTest(output=output, code=exit_code, config=config):
                code, data = self.gate(output, exit_code, config)
                self.assertEqual((code, data["status"]), (2, "error"))
                self.assertFalse(data["action_authorized"])

    def map(self, domains=None):
        folder = self.path / ".agent-oversight"
        folder.mkdir(exist_ok=True)
        domains = domains if domains is not None else [
            {"name": "Work", "path": "Work", "keywords": ["sprint", "API"]},
            {"name": "Personal", "path": "Personal", "keywords": ["journal"]},
        ]
        (folder / "domains.json").write_text(json.dumps({"domains": domains}))

    def test_route_does_not_need_context_contents(self):
        self.map()
        code, data = self.run_helper(ROUTE, "--root", self.path, "--prompt", "plan the sprint")
        self.assertEqual((code, data["status"]), (0, "matched"))
        self.assertEqual(data["matches"][0]["name"], "Work")
        self.assertFalse(data["context_loaded"])
        self.assertFalse((self.path / "Work/_context.md").exists())

    def test_ambiguity_and_no_match_are_explicit(self):
        self.map()
        for prompt, expected in [("sprint journal", "ambiguous"), ("capital", "unmatched")]:
            code, data = self.run_helper(ROUTE, "--root", self.path, "--prompt", prompt)
            self.assertEqual((code, data["status"]), (1, expected))

    def test_explicit_domain(self):
        self.map()
        code, data = self.run_helper(ROUTE, "--root", self.path, "--domain", "work")
        self.assertEqual((code, data["matches"][0]["name"]), (0, "Work"))

    def test_path_escape_rejected(self):
        self.map([{"name": "Escape", "path": "../outside", "keywords": ["escape"]}])
        code, data = self.run_helper(ROUTE, "--root", self.path, "--domain", "Escape")
        self.assertEqual((code, data["status"]), (2, "error"))

    def test_symlink_escape_rejected(self):
        self.map()
        (self.path / "Work").mkdir()
        (self.path / "Work/_context.md").symlink_to(self.path.parent / "outside.md")
        code, data = self.run_helper(ROUTE, "--root", self.path, "--domain", "Work")
        self.assertEqual((code, data["status"]), (2, "error"))

    def test_installer_preserves_existing_names(self):
        destination = self.path / "installed"
        destination.mkdir()
        conflict = destination / "vault-route"
        conflict.mkdir()
        (conflict / "keep.txt").write_text("keep")
        result = subprocess.run([sys.executable, str(ROOT / "install.py"), "--dest", str(destination)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(sorted(p.name for p in destination.iterdir()), ["vault-route"])
        self.assertEqual((conflict / "keep.txt").read_text(), "keep")

    def test_installer_copies_helpers_and_skills(self):
        destination = self.path / "installed"
        subprocess.run([sys.executable, str(ROOT / "install.py"), "--dest", str(destination)],
                       capture_output=True, text=True, check=True)
        self.assertEqual(len(list(destination.glob("*/SKILL.md"))), 7)
        self.assertEqual((destination / "gate-check/scripts/check.py").read_bytes(), GATE.read_bytes())
        self.assertEqual((destination / "vault-route/scripts/route.py").read_bytes(), ROUTE.read_bytes())


if __name__ == "__main__":
    unittest.main()
