#!/usr/bin/env python3
"""Atomic append-only writer for the Knowledge Ledger.

Writes use a temp-file-then-rename strategy so a crash never
corrupts existing entries.
"""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from typing import Any

__all__ = ["append_decision"]

_REQUIRED_FIELDS = frozenset({
    "decision_id", "timestamp", "actor", "pr_number",
    "commit_sha", "mode", "invariant_results",
    "decision", "reason", "kernel_version",
})


def _validate(record: dict[str, Any]) -> None:
    missing = _REQUIRED_FIELDS - record.keys()
    if missing:
        raise ValueError(f"decision record missing fields: {sorted(missing)}")
    if record["decision"] not in ("approve", "deny"):
        raise ValueError(f"decision must be 'approve' or 'deny', got {record['decision']!r}")


def append_decision(record: dict[str, Any], ledger_path: Path) -> None:
    """Atomically append *record* as a single JSON line."""
    _validate(record)
    ledger_path = ledger_path.resolve()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    new_line = json.dumps(record, separators=(',', ':'), sort_keys=True) + '\n'
    existing = ledger_path.read_text(encoding='utf-8') if ledger_path.is_file() else ''
    fd, tmp_path = tempfile.mkstemp(
        dir=str(ledger_path.parent), prefix='.ledger-tmp-', suffix='.jsonl',
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(existing)
            fh.write(new_line)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, str(ledger_path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_ledger(ledger_path: Path) -> list[dict[str, Any]]:
    """Read and parse every record from the ledger."""
    if not ledger_path.is_file():
        return []
    records = []
    for line in ledger_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records
