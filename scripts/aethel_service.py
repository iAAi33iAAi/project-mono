"""AETHEL Interop v1 service for ALGA_FOLD_KERNEL.

The endpoint performs invariant evaluation and returns the fail-closed decision.
Persistence is opt-in through the request body.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from invariants import KERNEL_VERSION, InvariantResult, load_invariants
from scripts.ledger_append import append_decision

PROTOCOL = "aethel-interop/1"
SERVICE = "project-mono"
VERSION = KERNEL_VERSION


def evaluate_change(payload: dict[str, Any], *, persist: bool = False) -> dict[str, Any]:
    request_id = str(payload.get("request_id", ""))
    ctx = {
        "pr_number": payload.get("pr_number", 0),
        "commit_sha": str(payload.get("commit_sha", "")),
        "actor": str(payload.get("actor", "aethel")),
        "mode": payload.get("mode", "merge"),
        "emergency": bool(payload.get("emergency", False)),
        "diff_text": str(payload.get("diff_text", "")),
        "changed_files": list(payload.get("changed_files", [])),
        "ci_artifacts": dict(payload.get("ci_artifacts", {})),
        "repo_root": Path(payload.get("repo_root", Path.cwd())).resolve(),
    }

    results: list[InvariantResult] = []
    for invariant in load_invariants():
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
    if ctx["emergency"] and failures:
        reasons.insert(0, "emergency flag cannot bypass fail-closed invariants")

    record = {
        "decision_id": request_id,
        "actor": ctx["actor"],
        "pr_number": ctx["pr_number"],
        "commit_sha": ctx["commit_sha"],
        "mode": ctx["mode"],
        "emergency": ctx["emergency"],
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
        ledger = Path(ctx["repo_root"]) / "ops" / "ledger" / "kernel-decisions.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        append_decision(record, ledger)
        persisted = True

    return {
        "protocol": PROTOCOL,
        "service": SERVICE,
        "version": VERSION,
        "request_id": request_id,
        "status": "PASS" if decision == "approve" else "FAIL",
        "decision": decision.upper(),
        "reasons": reasons,
        "result": record,
        "evidence": {"persisted": persisted},
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body, sort_keys=True).encode("utf-8")
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
                },
            )
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/aethel/evaluate":
            self._send(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            if body.get("protocol") != PROTOCOL:
                self._send(400, {"error": "unsupported protocol"})
                return
            if body.get("operation") != "change-control":
                self._send(400, {"error": "unsupported operation"})
                return
            payload = dict(body.get("payload", {}))
            payload["request_id"] = body["request_id"]
            self._send(
                200,
                evaluate_change(payload, persist=bool(body.get("persist", False))),
            )
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
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
