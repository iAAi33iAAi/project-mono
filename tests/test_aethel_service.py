"""AETHEL interop service tests for fail-closed request handling."""
import pytest

import scripts.aethel_service as service
from invariants import InvariantResult


def _valid_payload(**overrides):
    payload = {
        "request_id": "r-test",
        "pr_number": 1,
        "commit_sha": "abc123",
        "actor": "test",
        "mode": "merge",
        "emergency": False,
        "diff_text": "diff --git a/example.py b/example.py\n+value = 1\n",
        "changed_files": ["example.py"],
        "ci_artifacts": {
            "pytest": {"exit_code": 0, "tests_passed": True},
            "ruff": "pass",
            "mypy": "pass",
        },
    }
    payload.update(overrides)
    return payload


def test_fail_closed_emergency():
    result = service.evaluate_change(_valid_payload(emergency=True, ci_artifacts={}))
    assert result["protocol"] == "aethel-interop/1"
    assert result["service"] == "project-mono"
    assert result["decision"] == "DENY"
    assert result["status"] == "FAIL"


def test_payload_cannot_select_kernel_repository_root(tmp_path, monkeypatch):
    trusted_root = tmp_path / "trusted-repo"
    attacker_root = tmp_path / "attacker-controlled"
    trusted_root.mkdir()
    attacker_root.mkdir()
    observed = {}

    class CaptureRootInvariant:
        name = "capture_root"

        def evaluate(self, ctx):
            observed["repo_root"] = ctx["repo_root"]
            return InvariantResult(name=self.name, status="pass", details="captured")

    monkeypatch.setattr(service, "PROJECT_ROOT", trusted_root)
    monkeypatch.setattr(service, "load_invariants", lambda: [CaptureRootInvariant()])

    result = service.evaluate_change(_valid_payload(repo_root=str(attacker_root)))
    assert result["decision"] == "APPROVE"
    assert observed["repo_root"] == trusted_root.resolve()


def test_service_fails_closed_when_invariant_registry_is_empty(monkeypatch):
    monkeypatch.setattr(service, "load_invariants", lambda: [])
    result = service.evaluate_change(_valid_payload())
    assert result["status"] == "FAIL"
    assert result["decision"] == "DENY"
    assert any("no invariants loaded" in reason for reason in result["reasons"])


def test_service_fails_closed_when_invariant_registry_throws(monkeypatch):
    def broken_registry():
        raise RuntimeError("simulated import failure")

    monkeypatch.setattr(service, "load_invariants", broken_registry)
    result = service.evaluate_change(_valid_payload())
    assert result["status"] == "ERROR"
    assert result["decision"] == "DENY"
    assert result["evidence"]["invariants_loaded"] == 0


def test_malformed_mode_is_denied_without_exception():
    result = service.evaluate_change(_valid_payload(mode=["merge"]))
    assert result["status"] == "FAIL"
    assert result["decision"] == "DENY"
    assert any("mode must be merge" in reason for reason in result["reasons"])


@pytest.mark.parametrize(
    "raw",
    [
        '{"protocol":"aethel-interop/1","protocol":"wrong/1"}',
        '{"persist": NaN}',
        '{"value": Infinity}',
        '{"value": -Infinity}',
    ],
)
def test_strict_json_rejects_duplicate_keys_and_nonstandard_numbers(raw):
    with pytest.raises(ValueError):
        service.strict_json_loads(raw)


def test_persistence_requires_configured_bearer_token():
    assert not service.persistence_authorized("Bearer secret", "")
    assert not service.persistence_authorized("Bearer wrong", "secret")
    assert service.persistence_authorized("Bearer secret", "secret")
    assert not service.persistence_authorized("", "secret")
