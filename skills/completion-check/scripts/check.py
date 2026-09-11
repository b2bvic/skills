#!/usr/bin/env python3
"""Verify declared local completion evidence without authorizing actions."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import sys

SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_ID = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
KINDS = {"existence", "sha256", "json_value"}


def reject_constant(value):
    raise ValueError(f"Nonstandard JSON constant: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(text):
    return json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_object)


def equal_json(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(equal_json(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(equal_json(a, b) for a, b in zip(left, right))
    return left == right


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{label} is not a valid timestamp") from None
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def inside(root, relative, label):
    if not isinstance(relative, str) or not relative.strip() or Path(relative).is_absolute():
        raise ValueError(f"{label} must be a relative path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{label} leaves the workspace root")
    return path


def stay(root, path, label):
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} leaves the workspace root")
    return resolved


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packed_ref(git_dir, ref, root):
    packed = stay(root, git_dir / "packed-refs", "packed-refs")
    if not packed.is_file():
        return None
    for line in packed.read_text(encoding="utf-8").splitlines():
        if not line or line[0] in "#^":
            continue
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref and GIT_ID.fullmatch(parts[0]):
            return parts[0]
    return None


def git_head(repo, root):
    git_meta = stay(root, repo / ".git", "Git metadata")
    if git_meta.is_file():
        text = git_meta.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir:"):
            return None, "source revision is unreadable"
        target = Path(text.split(":", 1)[1].strip())
        git_dir = stay(root, target if target.is_absolute() else git_meta.parent / target, "gitdir")
    elif git_meta.is_dir():
        git_dir = git_meta
    else:
        return None, "source revision is unreadable"
    head_file = stay(root, git_dir / "HEAD", "HEAD")
    if not head_file.is_file():
        return None, "source revision is unreadable"
    head = head_file.read_text(encoding="utf-8").strip()
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        if not ref or Path(ref).is_absolute() or ".." in Path(ref).parts:
            return None, "source revision is unreadable"
        ref_file = stay(root, git_dir / ref, "Git ref")
        if ref_file.is_file():
            token = ref_file.read_text(encoding="utf-8").split()
            sha = token[0] if token else ""
        else:
            sha = packed_ref(git_dir, ref, root) or ""
    else:
        sha = head
    if not GIT_ID.fullmatch(sha):
        return None, "source revision is unreadable"
    return sha, None


def age_state(checked_at, moment, max_age):
    if moment is not None and moment > checked_at:
        return "unverified", "evidence timestamp is in the future"
    if max_age is None:
        return None, None
    if moment is None:
        return "unverified", "missing evidence timestamp"
    if (checked_at - moment).total_seconds() > max_age:
        return "unverified", "evidence is stale"
    return None, None


def require_str(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def load_contract(payload):
    if not isinstance(payload, dict):
        raise ValueError("The contract must be a JSON object")
    raw_root = payload.get("workspace_root")
    if not isinstance(raw_root, str) or not raw_root.strip():
        raise ValueError("workspace_root must be an absolute path")
    root = Path(raw_root).expanduser()
    if not root.is_absolute():
        raise ValueError("workspace_root must be an absolute path")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")
    expected_outcome = require_str(payload.get("expected_outcome"), "expected_outcome")
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError("checks must be a list")
    max_age = payload.get("max_age_seconds")
    if max_age is not None and (type(max_age) is not int or max_age < 0):
        raise ValueError("max_age_seconds must be an integer of 0 or more")
    global_time = payload.get("evidence_timestamp")
    if global_time is not None:
        global_time = parse_time(global_time, "evidence_timestamp")
    ids = []
    parsed = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise ValueError("Each check must be a JSON object")
        ident = require_str(check.get("id"), f"checks[{index}].id")
        ids.append(ident)
        kind = require_str(check.get("kind"), f"checks[{index}].kind")
        if kind not in KINDS:
            raise ValueError(f"Unsupported check kind: {kind}")
        claim = require_str(check.get("claim"), f"checks[{index}].claim")
        scope = require_str(check.get("scope"), f"checks[{index}].scope")
        path = inside(root, check.get("path"), f"checks[{index}].path")
        local_time = check.get("evidence_timestamp")
        if local_time is not None:
            local_time = parse_time(local_time, f"checks[{index}].evidence_timestamp")
        item = {"id": ident, "kind": kind, "claim": claim, "scope": scope, "path": path,
                "timestamp": local_time if local_time is not None else global_time}
        if kind == "sha256":
            digest = check.get("expected_sha256")
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                raise ValueError(f"checks[{index}].expected_sha256 must be a lowercase SHA-256 hex digest")
            item["expected_sha256"] = digest
        elif kind == "json_value":
            if "expected_json" not in check:
                raise ValueError(f"checks[{index}] needs expected_json")
            item["expected_json"] = check["expected_json"]
        parsed.append(item)
    if len(ids) != len(set(ids)):
        raise ValueError("Check ids must be unique")
    revision = payload.get("source_revision")
    source = None
    if revision is not None:
        if not isinstance(revision, dict):
            raise ValueError("source_revision must be an object")
        expected_head = revision.get("expected_head")
        if not isinstance(expected_head, str) or not GIT_ID.fullmatch(expected_head):
            raise ValueError("source_revision.expected_head must be a lowercase Git object name")
        source = {"path": inside(root, revision.get("path"), "source_revision.path"),
                  "expected_head": expected_head}
    return root, expected_outcome, parsed, max_age, source


def check_artifact(item, checked_at, max_age):
    path = item["path"]
    source_path = str(path)
    status, reason = age_state(checked_at, item["timestamp"], max_age)
    expected = ({"exists": True} if item["kind"] == "existence" else
                {"sha256": item["expected_sha256"]} if item["kind"] == "sha256" else
                {"json": item["expected_json"]})
    base = {"id": item["id"], "kind": item["kind"], "claim": item["claim"], "scope": item["scope"],
            "expected": expected, "source_path": source_path, "source_hash": None,
            "evidence_timestamp": stamp(item["timestamp"]) if item["timestamp"] else None,
            "timestamp_source": "contract-supplied"}
    if status:
        return {**base, "status": status, "observed": {}, "reason": reason}
    if not path.is_file():
        return {**base, "status": "failed", "observed": {"exists": False},
                "reason": "artifact is missing"}
    try:
        raw = path.read_bytes() if item["kind"] == "json_value" else None
        digest = hashlib.sha256(raw).hexdigest() if raw is not None else sha256_file(path)
    except OSError:
        return {**base, "status": "unverified", "observed": {"exists": True},
                "reason": "artifact is unreadable"}
    base["source_hash"] = digest
    if item["kind"] == "existence":
        return {**base, "status": "verified", "observed": {"exists": True, "sha256": digest}}
    if item["kind"] == "sha256":
        matched = digest == item["expected_sha256"]
        return {**base, "status": "verified" if matched else "failed",
                "observed": {"exists": True, "sha256": digest},
                **({} if matched else {"reason": "sha256 does not match"})}
    try:
        value = strict_json(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return {**base, "status": "unverified", "observed": {"exists": True, "sha256": digest},
                "reason": "artifact is unreadable"}
    except ValueError:
        return {**base, "status": "unverified", "observed": {"exists": True, "sha256": digest},
                "reason": "artifact is not valid JSON"}
    matched = equal_json(value, item["expected_json"])
    return {**base, "status": "verified" if matched else "failed",
            "observed": {"exists": True, "sha256": digest, "json": value},
            **({} if matched else {"reason": "JSON value does not match"})}


def check_revision(source, root):
    expected = source["expected_head"]
    repo = source["path"]
    receipt = {"path": str(repo), "expected": expected, "observed": None,
               "scope": "git-head-reference-only", "working_tree_verified": False}
    if not repo.is_dir():
        return {**receipt, "status": "unverified", "reason": "source revision is unreadable"}
    observed, reason = git_head(repo, root)
    receipt["observed"] = observed
    if reason:
        return {**receipt, "status": "unverified", "reason": reason}
    if observed != expected:
        return {**receipt, "status": "failed", "reason": "source revision does not match"}
    return {**receipt, "status": "verified"}


def worse(left, right):
    rank = {"verified": 0, "unverified": 1, "failed": 2}
    if right is None:
        return left
    return left if rank[left] >= rank[right] else right


def rollup(results, expected_outcome, revision):
    checks_status = "verified" if results else "unverified"
    for item in results:
        checks_status = worse(checks_status, item["status"])
    combined = worse(checks_status, None if revision is None else revision["status"])
    claims = [{"id": item["id"], "claim": item["claim"], "scope": item["scope"],
               "check_status": item["status"]} for item in results]
    reason = "Only declared local checks are evaluated; outcome and claim text are user-supplied labels."
    if not results:
        reason = "no checks were declared"
    return combined, checks_status, "not_evaluated", claims, reason


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = strict_json(args.input.expanduser().resolve(strict=True).read_text(encoding="utf-8"))
        root, expected_outcome, checks, max_age, source = load_contract(payload)
        checked_at = utcnow()
        revision = check_revision(source, root) if source else None
        results = [check_artifact(item, checked_at, max_age) for item in checks]
        status, checks_status, outcome_status, claims, reason = rollup(results, expected_outcome, revision)
        receipt = {
            "status": status,
            "scope": "local-artifact-checks-only",
            "task_completion_verified": False,
            "checks_status": checks_status,
            "expected_outcome": expected_outcome,
            "expected_outcome_status": outcome_status,
            "checked_at": stamp(checked_at),
            "workspace_root": str(root),
            "tested_claims": claims,
            "checks": results,
            "source_revision": revision,
            "action_authorized": False,
        }
        if reason:
            receipt["reason"] = reason
        print(json.dumps(receipt))
        return 0 if status == "verified" else 1
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "action_authorized": False, "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
