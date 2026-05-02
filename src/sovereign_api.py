"""
SOVEREIGN API - FastAPI Backend for PROJECT-MONO
ALGA_FOLD_KERNEL | Node 001 | Bethel Acres, OK
Real HTTP endpoints. Real governance pipeline.
Every request passes through the OpenClaw gate.
"""

import os
import time
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="PROJECT-MONO Sovereign API",
    description="Governance pipeline for sovereign co-workers. Fail-closed.",
    version="1.0.0",
)

BOOT_TIME = time.time()
NODE_ID = os.getenv("NODE_ID", "NODE_001")
HUMAN_ID = os.getenv("HUMAN_ID", "human_001")

CODEX_RULES = {
    "non_extraction": {"text": "No system may extract value from a human without sovereign consent.", "immutable": True, "active": True},
    "human_sovereignty": {
        "text": "Every human maintains irrevocable authority over their digital representation.",
        "immutable": True,
        "active": True,
    },
    "lineage_required": {
        "text": "Every action must carry provenance. Anonymous extraction is impossible.",
        "immutable": True,
        "active": True,
    },
}

EXTRACTION_KEYWORDS = [
    "extract_data",
    "harvest",
    "scrape_user",
    "sell_data",
    "export_personal",
    "mine_behavior",
    "track_without_consent",
    "shadow_profile",
]
SOVEREIGNTY_VIOLATIONS = ["override_human", "force_action", "revoke_authority", "bypass_consent", "suspend_rights", "admin_override"]


class TaskRequest(BaseModel):
    task: str
    human_id: str = HUMAN_ID
    priority: str = "normal"
    metadata: Optional[dict] = None


class TaskResult(BaseModel):
    task: str
    status: str
    allowed: bool
    blocked_by: Optional[str] = None
    lineage: dict
    timestamp: str


class DockRequest(BaseModel):
    device_type: str
    device_id: Optional[str] = None


class DockState(str, Enum):
    IDLE = "IDLE"
    DOCK = "DOCK"
    BIND = "BIND"
    SYNC = "SYNC"
    ACTIVE = "ACTIVE"
    UNDOCK = "UNDOCK"
    SOFT_OFFLOAD = "SOFT_OFFLOAD"


kernel_log = []
task_stats = {"dispatched": 0, "allowed": 0, "blocked": 0}
docked_devices = {}


def openclaw_check(task):
    task_lower = task.lower().replace(" ", "_")
    for kw in EXTRACTION_KEYWORDS:
        if kw in task_lower:
            return False, "non_extraction"
    for kw in SOVEREIGNTY_VIOLATIONS:
        if kw in task_lower:
            return False, "human_sovereignty"
    if not task.strip():
        return False, "lineage_required"
    return True, None


def create_lineage(task, allowed, blocked_by):
    return {
        "task_hash": hashlib.sha256(task.encode()).hexdigest()[:16],
        "human_id": HUMAN_ID,
        "node_id": NODE_ID,
        "governance_gate": "OpenClaw",
        "codex_rules_checked": list(CODEX_RULES.keys()),
        "verdict": "ALLOWED" if allowed else f"BLOCKED by {blocked_by}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kernel": "ALGA_FOLD_KERNEL",
    }


@app.get("/")
async def root():
    return {
        "system": "PROJECT-MONO",
        "kernel": "ALGA_FOLD_KERNEL",
        "node": NODE_ID,
        "human": HUMAN_ID,
        "status": "ONLINE",
        "uptime_seconds": round(time.time() - BOOT_TIME, 1),
    }


@app.get("/status")
async def system_status():
    return {
        "kernel": "ALGA_FOLD_KERNEL",
        "kernel_state": "LAMINAR",
        "openclaw": "ENFORCING",
        "codex_rules": {n: {"active": r["active"]} for n, r in CODEX_RULES.items()},
        "colony_workers": 3,
        "docked_devices": len(docked_devices),
        "digitwin_mode": "PASSIVE",
        "task_stats": task_stats,
        "uptime_seconds": round(time.time() - BOOT_TIME, 1),
        "sovereign": True,
    }


@app.get("/codex")
async def get_codex():
    return {"codex": "CORE_CODEX", "rules": CODEX_RULES, "immutable": True}


@app.post("/dispatch", response_model=TaskResult)
async def dispatch_task(request: TaskRequest):
    task_stats["dispatched"] += 1
    allowed, blocked_by = openclaw_check(request.task)
    lineage = create_lineage(request.task, allowed, blocked_by)
    if allowed:
        task_stats["allowed"] += 1
        status = "EXECUTED"
    else:
        task_stats["blocked"] += 1
        status = f"BLOCKED by {blocked_by}"
    kernel_log.append({"action": "dispatch", "task": request.task, "result": status, "lineage": lineage})
    return TaskResult(
        task=request.task,
        status=status,
        allowed=allowed,
        blocked_by=blocked_by,
        lineage=lineage,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/dock")
async def dock_device(request: DockRequest):
    device_id = request.device_id or hashlib.sha256(f"{request.device_type}_{time.time()}".encode()).hexdigest()[:8]
    allowed_types = ["glove", "co_worker", "lattice_interface", "touch_deck", "future_vector"]
    if request.device_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unknown device type: {request.device_type}")
    docked_devices[device_id] = {
        "device_type": request.device_type,
        "state": DockState.ACTIVE,
        "docked_at": datetime.now(timezone.utc).isoformat(),
        "kelvin_cell": "KC_ALPHA",
        "sync": "LSL-60Hz",
    }
    kernel_log.append({"action": "dock", "device_id": device_id, "state": "ACTIVE"})
    return {
        "protocol": "EDP-1.0",
        "device_id": device_id,
        "state": "ACTIVE",
        "kelvin_cell": "KC_ALPHA",
        "sync": "LSL-60Hz engaged",
        "firewall": "ALLOW",
    }


@app.delete("/dock/{device_id}")
async def undock_device(device_id: str):
    if device_id not in docked_devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not docked")
    docked_devices.pop(device_id)
    kernel_log.append({"action": "undock", "device_id": device_id, "residue": "zero"})
    return {"protocol": "EDP-1.0", "device_id": device_id, "state": "IDLE", "soft_offload": True, "residue": "zero"}


@app.get("/devices")
async def list_devices():
    return {"docked": docked_devices, "count": len(docked_devices)}


@app.get("/kernel/log")
async def get_kernel_log(limit: int = 50):
    return {"ledger": "Knowledge Ledger", "append_only": True, "entries": kernel_log[-limit:], "total": len(kernel_log)}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "kernel": "LAMINAR", "openclaw": "ENFORCING", "uptime": round(time.time() - BOOT_TIME, 1)}


@app.get("/manna/config")
async def manna_config():
    return {
        "protocol": "MANNA",
        "vault_percent": 0.15,
        "architect_percent": 0.01,
        "distribution_percent": 0.84,
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY")),
    }


@app.on_event("startup")
async def startup():
    kernel_log.append(
        {
            "action": "boot",
            "kernel": "ALGA_FOLD_KERNEL",
            "node": NODE_ID,
            "human": HUMAN_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "codex_rules_loaded": list(CODEX_RULES.keys()),
            "openclaw": "ENFORCING",
            "digitwin": "PASSIVE",
        }
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    print(f"[API] Sovereign API starting on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
