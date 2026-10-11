"""AETHEL Interop v1 service for ALGA_FOLD_KERNEL.

The endpoint evaluates supplied change evidence. HTTP persistence is disabled
unless an explicit server-side bearer token is configured. The client cannot
choose the repository root used by the invariant engine.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from invariants import KERNEL_VERSION, InvariantResult, load_invariants
from scripts.ledger_append import append_decision

PROTOCOL = "aethel-interop/1"
SERVICE = "project-mono"
VERSION = KERNEL_VERSION
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_REQUEST_BYTES = 2_000_000


def _reject_json_constant(value: str):
    raise ValueError(f"non-standard JSON constant is forbidden: {value}")


def _reject_duplicate_object_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def strict_json_loads(text: str):
    """Reject duplicate keys and non-standard NaN/Infinity JSON extensions."""
    return json.loads(
        text,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_reject_duplicate_object_keys,
    )


def persistence_authorized(authorization_header: str, configured_token: str | None = None) -> bool:
    """Return true only for an explicitly configured, constant-time bearer-token match."""
    token = configured_token if configured_token is not None else os.getenv("AETHEL_KERNEL_PERSIST_TOKEN", "")
    if not isinstance(token, str) or not token:
        return False
    expected = f"Bearer {token}"
    return isinstance(authorization_header, str) and hmac.compare_digest(authorization_header, expected)


def _invalid_input(request_id: str, errors: list[str]) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "service": SERVICE,
        "version": VERSION,
        "request_id": request_id,
        "status": "FAIL",
        "decision": "DENY",
        "reasons": [f"invalid input: {error}" for error in errors],
        "result": {},
        "evidence": {"persisted": False, "input_valid": False},
    }


def evaluate_change(
    payload: dict[str, Any],
    *,
    persist: bool = False,
    _repo_root: Path | None = None,
) -> dict[str, Any]:
    """Evaluate a change using the server's repository root, never a client-supplied path.

    _repo_root is an internal injection point for unit tests/local callers. It is
    not accepted from the HTTP request payload.
    """
    if not isinstance(payload, dict):
        return _invalid_input("", ["payload must be an object"])

    request_id = payload.get("request_id")
    errors: list[str] = []
    if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
        errors.append("request_id must be a non-empty string of at most 128 characters")
        request_id = ""

    pr_number = payload.get("pr_number")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
        errors.append("pr_number must be a positive integer")

    commit_sha = payload.get("commit_sha")
    if not isinstance(commit_sha, str) or not commit_sha.strip():
        errors.append("commit_sha must be a non-empty string")

    actor = payload.get("actor")
    if not isinstance(actor, str) or not actor.strip():
        errors.append("actor must be a non-empty string")

    mode = payload.get("mode", "merge")
    if not isinstance(mode, str) or mode not in {"merge", "deploy", "apply"}:
        errors.append("mode must be merge, deploy, or apply")

    emergency = payload.get("emergency", False)
    if not isinstance(emergency, bool):
        errors.append("emergency must be a boolean")

    diff_text = payload.get("diff_text", "")
    if not isinstance(diff_text, str) or not diff_text.strip():
        errors.append("diff_text must be a non-empty string")

    changed_files = payload.get("changed_files", [])
    if not isinstance(changed_files, list) or any(not isinstance(p, str) for p in changed_files):
        errors.append("changed_files must be a list of strings")

    ci_artifacts = payload.get("ci_artifacts", {})
    if not isinstance(ci_artifacts, dict):
        errors.append("ci_artifacts must be an object")

    if errors:
        return _invalid_input(request_id, errors)

    trusted_root = Path(_repo_root).resolve() if _repo_root is not None else PROJECT_ROOT.resolve()
    ctx = {
        "pr_number": pr_number,
        "commit_sha": commit_sha,
        "actor": actor,
        "mode": mode,
        "emergency": emergency,
        "diff_text": diff_text,
        "changed_files": changed_files,
        "ci_artifacts": ci_artifacts,
        "repo_root": trusted_root,
    }

    try:
        invariants = load_invariants()
    except Exception as exc:
        return {
            "protocol": PROTOCOL,
            "service": SERVICE,
            "version": VERSION,
            "request_id": request_id,
            "status": "ERROR",
            "decision": "DENY",
            "reasons": [f"invariant registry failed to load: {exc}"],
            "result": {},
            "evidence": {"persisted": False, "invariants_loaded": 0},
        }
    if not invariants:
        return {
            "protocol": PROTOCOL,
            "service": SERVICE,
            "version": VERSION,
            "request_id": request_id,
            "status": "FAIL",
            "decision": "DENY",
            "reasons": ["no invariants loaded; cannot approve the change"],
            "result": {},
            "evidence": {"persisted": False, "invariants_loaded": 0},
        }

    results: list[InvariantResult] = []
    for invariant in invariants:
        try:
            results.append(invariant.evaluate(ctx))
        except Exception as exc:
            results.append(
                InvariantResult(
                    name=invariant.name,
                    status="error",
                    details=f"exception: {exc}",
                    remediation=["investigate invariant crash"],
                )
            )

    failures = [r for r in results if r.status in ("fail", "error")]
    decision = "deny" if failures else "approve"
    reasons = [f"{r.name}: {r.details}" for r in failures]
    if emergency and failures:
        reasons.insert(0, "emergency flag cannot bypass fail-closed invariants")

    record = {
        "decision_id": request_id,
        "actor": actor,
        "pr_number": pr_number,
        "commit_sha": commit_sha,
        "mode": mode,
        "emergency": emergency,
        "invariant_results": {
            r.name: {
                "status": r.status,
                "details": r.details,
                "remediation": r.remediation,
            }
            for r in results
        },
        "decision": decision,
        "reason": "; ".join(reasons) if reasons else "all invariants passed",
        "kernel_version": KERNEL_VERSION,
    }

    persisted = False
    if persist:
        ledger = trusted_root / "ops" / "ledger" / "kernel-decisions.jsonl"
        try:
            append_decision(record, ledger)
            persisted = True
        except Exception as exc:
            return {
                "protocol": PROTOCOL,
                "service": SERVICE,
                "version": VERSION,
                "request_id": request_id,
                "status": "ERROR",
                "decision": "DENY",
                "reasons": [f"ledger persistence failed: {exc}"],
                "result": record,
                "evidence": {"persisted": False, "repo_root": str(trusted_root)},
            }

    return {
        "protocol": PROTOCOL,
        "service": SERVICE,
        "version": VERSION,
        "request_id": request_id,
        "status": "PASS" if decision == "approve" else "FAIL",
        "decision": decision.upper(),
        "reasons": reasons,
        "result": record,
        "evidence": {"persisted": persisted, "repo_root": str(trusted_root)},
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body, sort_keys=True, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/aethel/health":
            self._send(
                200,
                {
                    "protocol": PROTOCOL,
                    "service": SERVICE,
                    "version": VERSION,
                    "request_id": "health",
                    "status": "PASS",
                    "decision": "HEALTHY",
                    "reasons": [],
                    "result": {},
                    "evidence": {},
                },
            )
            return
        if self.path == "/aethel/capabilities":
            self._send(
                200,
                {
                    "protocol": PROTOCOL,
                    "service": SERVICE,
                    "version": VERSION,
                    "operations": ["change-control"],
                    "dry_run_default": True,
                    "persistence_requires_bearer_token": True,
                },
            )
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/aethel/evaluate":
            self._send(404, {"error": "not found"})
            return
        try:
            raw_size = self.headers.get("Content-Length", "")
            if not raw_size.isdigit():
                self._send(400, {"error": "valid Content-Length is required"})
                return
            size = int(raw_size)
            if size <= 0:
                self._send(400, {"error": "request body is required"})
                return
            if size > MAX_REQUEST_BYTES:
                self._send(413, {"error": "request body too large"})
                return

            body = strict_json_loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(body, dict):
                self._send(400, {"error": "request body must be a JSON object"})
                return
            if body.get("protocol") != PROTOCOL:
                self._send(400, {"error": "unsupported protocol"})
                return
            if body.get("operation") != "change-control":
                self._send(400, {"error": "unsupported operation"})
                return

            request_id = body.get("request_id")
            if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
                self._send(400, {"error": "request_id must be a non-empty string of at most 128 characters"})
                return
            payload = body.get("payload")
            if not isinstance(payload, dict):
                self._send(400, {"error": "payload must be an object"})
                return
            persist = body.get("persist", False)
            if not isinstance(persist, bool):
                self._send(400, {"error": "persist must be a boolean"})
                return
            if persist and not persistence_authorized(self.headers.get("Authorization", "")):
                self._send(403, {"error": "persistence requires a valid server-configured bearer token"})
                return

            payload = dict(payload)
            payload["request_id"] = request_id
            # Deliberately ignore payload["repo_root"]; evaluate_change selects
            # the trusted service repository root or a private in-process test path.
            payload.pop("repo_root", None)
            result = evaluate_change(payload, persist=persist)
            self._send(200, result)
        except (TypeError, ValueError, KeyError, UnicodeDecodeError) as exc:
            self._send(400, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8102)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
