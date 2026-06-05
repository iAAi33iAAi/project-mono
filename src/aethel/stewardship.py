"""
Aethel Grid -- Stewardship Kernel
Laminar Lattice Prime 3.6.9

<Aethel_Grid_Context>
  Mission: Sovereign Stewardship of DNA/INA systems.
  Framework: Six-Domain Optimization.
  Constraint: Architect's Constant (0.01 * Vh).
  Current_State: Laminar Lattice Prime 3.6.9.
</Aethel_Grid_Context>

Gateway -> Orchestration -> Execution pattern.
All logic anchored to SPEC.md Section 2.
"""

from __future__ import annotations
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aethel.stewardship")


class Domain(Enum):
    ECONOMIC       = 1
    SOCIAL         = 2
    BIOLOGICAL     = 3
    DATA           = 4
    INFRASTRUCTURE = 5
    ETHICAL        = 6


@dataclass
class SubstrateMetrics:
    """V_h and Omega substrate measurements."""
    v_h: float
    omega: float
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.v_h <= 0:
            raise ValueError("V_h must be strictly positive.")
        if not (0.0 <= self.omega <= 1.0):
            raise ValueError("Omega must be in [0.0, 1.0].")

@dataclass
class ProcessManifest:
    """Plugin process declaration. Must declare all permissions before execution."""
    process_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    permissions: List[str] = field(default_factory=list)
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ProcessManifest.name cannot be empty.")

    def compute_signature(self, secret: bytes = b"aethel-lattice-prime") -> str:
        payload = f"{self.process_id}:{self.name}:{','.join(sorted(self.permissions))}"
        self.signature = hashlib.hmac_sha256_hex(
            secret, payload.encode()
        ) if hasattr(hashlib, "hmac_sha256_hex") else hashlib.sha256(
            secret + payload.encode()
        ).hexdigest()
        return self.signature


@dataclass
class EffectivenessLedger:
    """Tracks Six-Domain contributions from all active agents/processes."""
    entries: Dict[str, Dict[Domain, float]] = field(default_factory=dict)

    def record(self, process_id: str, domain: Domain, contribution: float) -> None:
        if not (0.0 <= contribution <= 1.0):
            raise ValueError("Contribution must be in [0.0, 1.0].")
        if process_id not in self.entries:
            self.entries[process_id] = {}
        self.entries[process_id][domain] = contribution
        logger.debug("Ledger: %s -> %s = %.4f", process_id, domain.name, contribution)

    def total_contribution(self, process_id: str) -> float:
        return sum(self.entries.get(process_id, {}).values())

    def audit_report(self) -> Dict[str, Any]:
        return {
            pid: {d.name: v for d, v in domains.items()}
            for pid, domains in self.entries.items()
        }


class GatewayLayer:
    """
    Trust boundary. Rejects non-loopback connections without valid session tokens.
    Spec Section 3 -- Gateway Layer.
    """
    _LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

    def __init__(self, allowed_tokens: Optional[List[str]] = None) -> None:
        self._tokens: List[str] = list(allowed_tokens or [])
        self._sessions: Dict[str, float] = {}

    def issue_token(self) -> str:
        token = uuid.uuid4().hex
        self._tokens.append(token)
        return token

    def open_session(self, token: str, peer: str) -> str:
        if peer not in self._LOOPBACK and token not in self._tokens:
            raise PermissionError(
                f"GatewayLayer: rejected non-loopback peer '{peer}' without a valid token."
            )
        session_id = uuid.uuid4().hex

class OrchestrationLayer:
    """
    Enforces Six-Domain Optimization Framework.
    All agents must report domain contributions to EffectivenessLedger.
    Spec Section 3 -- Orchestration Layer.
    """

    def __init__(self, ledger: EffectivenessLedger) -> None:
        self._ledger = ledger
        self._handlers: Dict[Domain, List[Callable]] = {d: [] for d in Domain}

    def register_handler(self, domain: Domain, handler: Callable) -> None:
        self._handlers[domain].append(handler)
        logger.debug("Handler registered for domain %s", domain.name)

    def dispatch(self, process_id: str, domain_scores: List[DomainScore]) -> None:
        for ds in domain_scores:
            self._ledger.record(process_id, ds.domain, ds.disruption)
            for handler in self._handlers[ds.domain]:
                try:
                    handler(process_id, ds)
                except Exception as exc:
                    logger.error(
                        "Handler error domain=%s pid=%s: %s",
                        ds.domain.name, process_id, exc
                    )

    def require_all_domains(self, process_id: str) -> bool:
        reported = set(self._ledger.entries.get(process_id, {}).keys())
        return reported == set(Domain)


class ExecutionLayer:
    """
    Sandboxed plugin execution. Plugins must declare permissions in a manifest.
    Unauthorized access triggers an immediate security audit.
    Spec Section 3 -- Execution Layer.
    """

    def __init__(
        self,
        gateway: GatewayLayer,
        orchestration: OrchestrationLayer,
        audit_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._gateway = gateway
        self._orchestration = orchestration
        self._audit_cb = audit_callback
        self._plugins: Dict[str, ProcessManifest] = {}

    def register_plugin(self, manifest: ProcessManifest) -> None:
        self._plugins[manifest.process_id] = manifest
        logger.info(
            "Plugin registered: %s (%s)", manifest.name, manifest.process_id
        )

    def run(
        self,
        manifest: ProcessManifest,
        session_id: str,
        domain_scores: List[DomainScore],
        action: Callable[[], Any],
    ) -> Any:
        if not self._gateway.validate_session(session_id):
            raise PermissionError("ExecutionLayer: invalid or expired session.")
        registered = self._plugins.get(manifest.process_id)
        if registered is None:
            self._trigger_audit(manifest.process_id, "unregistered plugin")
            raise PermissionError(
                f"ExecutionLayer: plugin '{manifest.name}' not registered."
            )

@dataclass
class AethelGrid:
    """
    Top-level facade binding Gateway, Orchestration, and Execution layers.
    Implements the Stewardship Specification -- Laminar Lattice Prime 3.6.9.
    """
    gateway: GatewayLayer = field(default_factory=GatewayLayer)
    ledger: EffectivenessLedger = field(default_factory=EffectivenessLedger)
    orchestration: OrchestrationLayer = field(init=False)
    execution: ExecutionLayer = field(init=False)
    _substrate: Optional[SubstrateMetrics] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.orchestration = OrchestrationLayer(self.ledger)
        self.execution = ExecutionLayer(self.gateway, self.orchestration)

    def set_substrate(self, metrics: SubstrateMetrics) -> None:
        self._substrate = metrics
        logger.info(
            "Substrate updated: V_h=%.4f Omega=%.4f",
            metrics.v_h, metrics.omega
        )

    def open_session(self, token: str, peer: str = "127.0.0.1") -> str:
        return self.gateway.open_session(token, peer)

    def issue_token(self) -> str:
        return self.gateway.issue_token()

    def run_plugin(
        self,
        manifest: ProcessManifest,
        session_id: str,
        domain_scores: List[DomainScore],
        action: Callable[[], Any],
    ) -> Any:
        if self._substrate is None:
            raise RuntimeError(
                "AethelGrid: substrate metrics not set. Call set_substrate() first."
            )
        psi = compute_psi(domain_scores, self._substrate)
        if psi > 1.0:
            raise RuntimeError(
                f"AethelGrid: Psi={psi:.4f} exceeds 1.0 threshold. "
                "Process throttled per Spec Section 2."
            )
        return self.execution.run(manifest, session_id, domain_scores, action)


# ---------------------------------------------------------------------------
# Standalone utility functions (Spec Section 2)
# ---------------------------------------------------------------------------

def compute_efficiency_score(output_capacity: float, v_h: float) -> float:
    """Efficiency_Score = Output_Capacity / (0.01 * V_h)."""
    if v_h <= 0:
        raise ValueError("V_h must be positive.")
    return output_capacity / (0.01 * v_h)


def compute_psi(
    domain_scores: List[DomainScore],
    substrate: SubstrateMetrics,
) -> float:
    """Psi = sum(D_n * Omega) / (0.01 * V_h) across all six domains."""
    total = sum(ds.disruption * substrate.omega for ds in domain_scores)
    return total / (0.01 * substrate.v_h)


def psi_gate(domain_scores: List[DomainScore], substrate: SubstrateMetrics) -> bool:
    """Return True if Psi <= 1.0 (process may proceed)."""
    return compute_psi(domain_scores, substrate) <= 1.0


def validate_efficiency(
    output_capacity: float,
    v_h: float,
    threshold: float = 1.0,
) -> bool:
    """Return True if Efficiency_Score >= threshold."""
    return compute_efficiency_score(output_capacity, v_h) >= threshold


__all__ = [
    "AethelGrid",
    "Domain",
    "DomainScore",
    "EffectivenessLedger",
    "ExecutionLayer",
    "GatewayLayer",
    "OrchestrationLayer",
    "ProcessManifest",
    "SubstrateMetrics",
    "compute_efficiency_score",
    "compute_psi",
    "psi_gate",
    "validate_efficiency",
]

        self._orchestration.dispatch(manifest.process_id, domain_scores)
        result = action()
        logger.info("Plugin executed: %s", manifest.name)
        return result

    def _trigger_audit(self, process_id: str, reason: str) -> None:
        logger.warning("AUDIT TRIGGERED: pid=%s reason=%s", process_id, reason)
        if self._audit_cb:
            self._audit_cb(process_id, reason)

        self._sessions[session_id] = time.time()
        logger.info("Session opened: %s (peer=%s)", session_id, peer)
        return session_id

    def validate_session(self, session_id: str, ttl: float = 3600.0) -> bool:
        opened_at = self._sessions.get(session_id)
        if opened_at is None:
            return False
        return (time.time() - opened_at) < ttl


@dataclass
class DomainScore:
    """Disruption score D_n for a single domain. Must be in [0.0, 1.0]."""
    domain: Domain
    disruption: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.disruption <= 1.0):
            raise ValueError(
                f"Domain disruption for {self.domain.name} must be in [0.0, 1.0]."
            )
