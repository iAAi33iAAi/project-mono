from scripts.aethel_service import evaluate_change


def test_fail_closed_emergency():
    result = evaluate_change(
        {
            "request_id": "r1",
            "pr_number": 1,
            "commit_sha": "abc",
            "actor": "test",
            "mode": "merge",
            "emergency": True,
            "changed_files": [],
            "ci_artifacts": {},
            "repo_root": ".",
        }
    )
    assert result["protocol"] == "aethel-interop/1"
    assert result["service"] == "project-mono"
    assert result["decision"] == "DENY"
