import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "skills/gate-check/scripts/check.py"
ROUTE = ROOT / "skills/vault-route/scripts/route.py"
COMPLETION = ROOT / "skills/completion-check/scripts/check.py"
EXAMPLES = ROOT / "skills/completion-check/examples"
HEAD_A = "a" * 40
HEAD_B = "b" * 40
RESULT_BYTES = b'{"ok": true}\n'
RESULT_HASH = "55f66c2c5aeb275ff5b1ae26b321d5c0b8ceda8c034b19c2643e046d024919f3"
EXISTING_SKILLS = [
    "agent-status", "gate-check", "ledger-search",
    "vault-context", "vault-handoff", "vault-log", "vault-route",
]


class Helpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix=".test-")
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
        self.assertEqual(len(list(destination.glob("*/SKILL.md"))), 8)
        self.assertEqual((destination / "gate-check/scripts/check.py").read_bytes(), GATE.read_bytes())
        self.assertEqual((destination / "vault-route/scripts/route.py").read_bytes(), ROUTE.read_bytes())
        self.assertEqual((destination / "completion-check/scripts/check.py").read_bytes(), COMPLETION.read_bytes())

    def test_installer_refuses_eighth_over_existing_seven(self):
        destination = self.path / "installed"
        destination.mkdir()
        for name in EXISTING_SKILLS:
            (destination / name).mkdir()
        result = subprocess.run([sys.executable, str(ROOT / "install.py"), "--dest", str(destination)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((destination / "completion-check").exists())
        self.assertEqual(sorted(p.name for p in destination.iterdir()), EXISTING_SKILLS)


class CompletionCheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix=".test-")
        self.path = Path(self.temp.name)
        artifacts = self.path / "artifacts"
        artifacts.mkdir()
        (artifacts / "result.json").write_bytes(RESULT_BYTES)
        git = self.path / ".git" / "refs" / "heads"
        git.mkdir(parents=True)
        (self.path / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        (git / "main").write_text(HEAD_A + "\n")

    def tearDown(self):
        self.temp.cleanup()

    def run_helper(self, *args):
        result = subprocess.run([sys.executable, str(COMPLETION), *map(str, args)],
                                capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def contract(self, **fields):
        payload = {
            "workspace_root": str(self.path),
            "expected_outcome": "artifact written",
            "source_revision": {"path": ".", "expected_head": HEAD_A},
            "checks": [{
                "id": "result-hash",
                "kind": "sha256",
                "claim": "artifact written",
                "scope": "local-artifact",
                "path": "artifacts/result.json",
                "expected_sha256": RESULT_HASH,
            }],
        }
        payload.update(fields)
        path = self.path / "contract.json"
        path.write_text(json.dumps(payload))
        return self.run_helper("--input", path)

    def test_artifact_written_is_verified(self):
        code, data = self.contract()
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "verified")
        self.assertEqual(data["expected_outcome_status"], "not_evaluated")
        self.assertFalse(data["task_completion_verified"])
        self.assertEqual(data["checks"][0]["expected"]["sha256"], RESULT_HASH)
        self.assertEqual(data["checks"][0]["observed"]["sha256"], RESULT_HASH)
        self.assertEqual(data["checks"][0]["source_hash"], RESULT_HASH)
        self.assertTrue(data["checks"][0]["source_path"].endswith("artifacts/result.json"))
        self.assertEqual(data["source_revision"]["expected"], HEAD_A)
        self.assertEqual(data["source_revision"]["observed"], HEAD_A)
        self.assertFalse(data["action_authorized"])

    def test_wrong_hash_fails(self):
        code, data = self.contract(checks=[{
            "id": "result-hash",
            "kind": "sha256",
            "claim": "artifact written",
            "scope": "local-artifact",
            "path": "artifacts/result.json",
            "expected_sha256": "0" * 64,
        }])
        self.assertEqual((code, data["status"]), (1, "failed"))
        self.assertEqual(data["checks"][0]["observed"]["sha256"], RESULT_HASH)
        self.assertFalse(data["action_authorized"])

    def test_missing_artifact_fails(self):
        code, data = self.contract(checks=[{
            "id": "result-exists",
            "kind": "existence",
            "claim": "artifact written",
            "scope": "local-artifact",
            "path": "artifacts/missing.json",
        }])
        self.assertEqual((code, data["status"]), (1, "failed"))
        self.assertEqual(data["checks"][0]["observed"], {"exists": False})

    def test_json_value_match_and_mismatch(self):
        matching = {
            "id": "result-json",
            "kind": "json_value",
            "claim": "artifact written",
            "scope": "local-artifact",
            "path": "artifacts/result.json",
            "expected_json": {"ok": True},
        }
        code, data = self.contract(checks=[matching])
        self.assertEqual((code, data["status"]), (0, "verified"))
        wrong = dict(matching, expected_json={"ok": False})
        code, data = self.contract(checks=[wrong])
        self.assertEqual((code, data["status"]), (1, "failed"))

    def test_malformed_json_is_unverified(self):
        (self.path / "artifacts" / "result.json").write_text("{")
        code, data = self.contract(checks=[{
            "id": "result-json",
            "kind": "json_value",
            "claim": "artifact written",
            "scope": "local-artifact",
            "path": "artifacts/result.json",
            "expected_json": {"ok": True},
        }])
        self.assertEqual((code, data["status"], data["checks"][0]["status"]), (1, "unverified", "unverified"))

    def test_stale_evidence_is_unverified(self):
        code, data = self.contract(max_age_seconds=3600, evidence_timestamp="2020-01-01T00:00:00Z")
        self.assertEqual((code, data["status"]), (1, "unverified"))
        self.assertEqual(data["checks"][0]["reason"], "evidence is stale")

    def test_future_timestamp_is_unverified(self):
        code, data = self.contract(evidence_timestamp="2099-01-01T00:00:00Z")
        self.assertEqual((code, data["status"]), (1, "unverified"))
        self.assertEqual(data["checks"][0]["reason"], "evidence timestamp is in the future")

    def test_missing_timestamp_with_max_age_is_unverified(self):
        code, data = self.contract(max_age_seconds=60)
        self.assertEqual((code, data["status"]), (1, "unverified"))
        self.assertEqual(data["checks"][0]["reason"], "missing evidence timestamp")

    def test_wrong_revision_fails(self):
        code, data = self.contract(source_revision={"path": ".", "expected_head": HEAD_B})
        self.assertEqual((code, data["status"]), (1, "failed"))
        self.assertEqual(data["source_revision"]["observed"], HEAD_A)
        self.assertFalse(data["action_authorized"])

    def test_changed_source_revision_fails(self):
        code, data = self.contract()
        self.assertEqual(code, 0)
        (self.path / ".git" / "refs" / "heads" / "main").write_text(HEAD_B + "\n")
        code, data = self.contract()
        self.assertEqual((code, data["status"]), (1, "failed"))
        self.assertEqual(data["source_revision"]["expected"], HEAD_A)
        self.assertEqual(data["source_revision"]["observed"], HEAD_B)

    def test_duplicate_ids_error(self):
        check = {
            "id": "result",
            "kind": "existence",
            "claim": "artifact written",
            "scope": "local-artifact",
            "path": "artifacts/result.json",
        }
        code, data = self.contract(checks=[check, dict(check, kind="sha256", expected_sha256=RESULT_HASH)])
        self.assertEqual((code, data["status"]), (2, "error"))
        self.assertFalse(data["action_authorized"])

    def test_empty_checks_are_unverified(self):
        code, data = self.contract(checks=[])
        self.assertEqual((code, data["status"]), (1, "unverified"))
        self.assertEqual(data["reason"], "no checks were declared")
        self.assertFalse(data["action_authorized"])

    def test_invalid_hash_and_timestamp_are_errors(self):
        for fields in [
            {"checks": [{
                "id": "result-hash", "kind": "sha256", "claim": "artifact written",
                "scope": "local-artifact", "path": "artifacts/result.json",
                "expected_sha256": "not-a-hash",
            }]},
            {"evidence_timestamp": "yesterday"},
            {"source_revision": {"path": ".", "expected_head": "xyz"}},
            {"max_age_seconds": -1},
        ]:
            with self.subTest(fields=fields):
                code, data = self.contract(**fields)
                self.assertEqual((code, data["status"]), (2, "error"))
                self.assertFalse(data["action_authorized"])

    def test_outcome_labels_never_certify_task_completion(self):
        code, data = self.contract(expected_outcome="deployed successfully", checks=[{
            "id": "exists", "kind": "existence", "claim": "deployed successfully",
            "scope": "deployment", "path": "artifacts/result.json",
        }])
        self.assertEqual((code, data["checks_status"]), (0, "verified"))
        self.assertEqual(data["scope"], "local-artifact-checks-only")
        self.assertEqual(data["expected_outcome_status"], "not_evaluated")
        self.assertFalse(data["task_completion_verified"])
        self.assertFalse(data["source_revision"]["working_tree_verified"])
        self.assertFalse(data["action_authorized"])

    def test_json_boolean_is_not_number(self):
        code, data = self.contract(checks=[{
            "id": "json", "kind": "json_value", "claim": "result matches",
            "scope": "local-artifact", "path": "artifacts/result.json", "expected_json": {"ok": 1},
        }])
        self.assertEqual((code, data["checks_status"]), (1, "failed"))

    def test_nonstandard_or_ambiguous_json_never_passes(self):
        for raw in ['{"ok":NaN}', '{"ok":true,"ok":false}']:
            (self.path / "artifacts/result.json").write_text(raw)
            code, data = self.contract(checks=[{
                "id": "json", "kind": "json_value", "claim": "result matches",
                "scope": "local-artifact", "path": "artifacts/result.json", "expected_json": {"ok": False},
            }])
            self.assertEqual((code, data["checks_status"]), (1, "unverified"))

    def test_path_escape_rejected(self):
        code, data = self.contract(checks=[{
            "id": "escape",
            "kind": "existence",
            "claim": "artifact written",
            "scope": "local-artifact",
            "path": "../secret.txt",
        }])
        self.assertEqual((code, data["status"]), (2, "error"))

    def test_symlink_escape_rejected(self):
        outside = self.path.parent / "outside-missing.json"
        (self.path / "artifacts" / "link.json").symlink_to(outside)
        code, data = self.contract(checks=[{
            "id": "link",
            "kind": "existence",
            "claim": "artifact written",
            "scope": "local-artifact",
            "path": "artifacts/link.json",
        }])
        self.assertEqual((code, data["status"]), (2, "error"))

    def test_gitdir_escape_rejected(self):
        shutil.rmtree(self.path / ".git")
        (self.path / ".git").write_text("gitdir: ../outside.git\n")
        code, data = self.contract()
        self.assertEqual((code, data["status"]), (2, "error"))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can read mode-zero files")
    def test_unreadable_artifact_is_unverified(self):
        target = self.path / "artifacts" / "result.json"
        target.chmod(0)
        try:
            code, data = self.contract()
        finally:
            target.chmod(0o644)
        self.assertEqual((code, data["status"], data["checks"][0]["status"]), (1, "unverified", "unverified"))
        self.assertFalse(data["action_authorized"])

    def test_examples_are_sanitized_contracts(self):
        names = sorted(path.name for path in EXAMPLES.glob("*.json"))
        self.assertEqual(names, [
            "artifact-missing.json", "artifact-written.json", "artifact-wrong.json",
            "repeat-checks.json", "stale-receipt.json", "wrong-revision.json",
        ])
        for path in EXAMPLES.glob("*.json"):
            text = path.read_text()
            data = json.loads(text)
            self.assertEqual(data["workspace_root"], "/workspace")
            self.assertIn("expected_outcome", data)
            self.assertIsInstance(data["checks"], list)
            self.assertNotRegex(text.lower(), r"token|secret|password|api[_-]?key")


if __name__ == "__main__":
    unittest.main()
