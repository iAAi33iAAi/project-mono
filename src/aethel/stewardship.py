"""Aethel Grid stewardship kernel.

Implements the Gateway -> Orchestration -> Execution pattern described by SPEC.md.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aethel.stewardship")

C_a_DIVISOR = 0.01
PSI_THRESHOLD = 1.0


class Domain(Enum):
    ECONOMIC = 1
    SOCIAL = 2
    BIOLOGICAL = 3
    DATA = 4
    INFRASTRUCTURE = 5
    ETHICAL = 6


@dataclass
class DomainScore:
    """Disruption score D_n in [0, 1]."""

    domain: Domain
    disruption: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.disruption <= 1.0:
            raise ValueError(
                f"Domain disruption for {self.domain.name} must be in [0.0, 1.0]."
            )


@dataclass(frozen=True)
class LedgerEntry:
    process_id: str
    domain: Domain
    contribution: float
    timestamp: float


@dataclass
class SubstrateMetrics:
    """V_h and Omega substrate measurements."""

    v_h: float
    omega: float
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.v_h <= 0:
            raise ValueError("V_h must be strictly positive.")
        if not 0.0 <= self.omega <= 1.0:
            raise ValueError("Omega must be in [0.0, 1.0].")


@dataclass
class ProcessManifest:
    """Plugin declaration; permissions are part of its identity."""

    process_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    permissions: List[str] = field(default_factory=list)
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ProcessManifest.name cannot be empty.")

    def _payload(self) -> bytes:
        payload = f"{self.process_id}:{self.name}:{','.join(sorted(self.permissions))}"
        return payload.encode("utf-8")

    def compute_signature(self, secret: bytes = b"aethel-lattice-prime") -> str:
        self.signature = hmac.new(secret, self._payload(), hashlib.sha256).hexdigest()
        return self.signature

    def verify_signature(self, secret: bytes = b"aethel-lattice-prime") -> bool:
        if not self.signature:
            return False
        expected = hmac.new(secret, self._payload(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)


@dataclass
class EffectivenessLedger:
    """Tracks domain contributions for each process."""

    entries: Dict[str, Dict[Domain, float]] = field(default_factory=dict)
    history: List[LedgerEntry] = field(default_factory=list)

    def record(self, process_id: str, domain: Domain, contribution: float) -> None:
        if not 0.0 <= contribution <= 1.0:
            raise ValueError("Contribution must be in [0.0, 1.0].")
        self.entries.setdefault(process_id, {})[domain] = contribution
        self.history.append(
            LedgerEntry(process_id, domain, contribution, time.time())
        )

    def total_contribution(self, process_id: str) -> float:
        return sum(self.entries.get(process_id, {}).values())

    def audit_report(self) -> Dict[str, Any]:
        return {
            process_id: {
                domain.name: value for domain, value in domains.items()
            }
            for process_id, domains in self.entries.items()
        }


class GatewayLayer:
    """Trust boundary: only loopback or token-authenticated peers are admitted."""

    _LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

    def __init__(self, allowed_tokens: Optional[List[str]] = None) -> None:
        self._tokens = list(allowed_tokens or [])
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
        self._sessions[session_id] = time.time()
        logger.info("Session opened: %s (peer=%s)", session_id, peer)
        return session_id

    def validate_session(self, session_id: str, ttl: float = 3600.0) -> bool:
        opened_at = self._sessions.get(session_id)
        if opened_at is None:
            return False
        if ttl <= 0:
            return False
        return (time.time() - opened_at) < ttl


class OrchestrationLayer:
    """Enforces six-domain reporting through the effectiveness ledger."""

    def __init__(self, ledger: EffectivenessLedger) -> None:
        self._ledger = ledger
        self._handlers: Dict[Domain, List[Callable[..., Any]]] = {
            domain: [] for domain in Domain
        }

    def register_handler(
        self,
        domain: Domain,
        handler: Callable[[str, DomainScore], Any],
    ) -> None:
        self._handlers[domain].append(handler)

    def dispatch(self, process_id: str, domain_scores: List[DomainScore]) -> None:
        for score in domain_scores:
            self._ledger.record(process_id, score.domain, score.disruption)
            for handler in self._handlers[score.domain]:
                try:
                    handler(process_id, score)
                except Exception as exc:
                    logger.error(
                        "Handler error domain=%s pid=%s: %s",
                        score.domain.name,
                        process_id,
                        exc,
                    )

    def require_all_domains(self, process_id: str) -> bool:
        reported = set(self._ledger.entries.get(process_id, {}))
        return reported == set(Domain)


class ExecutionLayer:
    """Executes only registered plugins with a valid gateway session."""

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
        logger.info("Plugin registered: %s (%s)", manifest.name, manifest.process_id)

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

        if registered is not manifest and registered.signature != manifest.signature:
            self._trigger_audit(manifest.process_id, "manifest identity mismatch")
            raise PermissionError("ExecutionLayer: manifest identity mismatch.")

        if len(domain_scores) != len(Domain):
            self._trigger_audit(manifest.process_id, "incomplete domain evaluation")
            raise PermissionError("ExecutionLayer: all six domains are required.")

        if not self._orchestration.require_all_domains(manifest.process_id):
            self._orchestration.dispatch(manifest.process_id, domain_scores)
        if not self._orchestration.require_all_domains(manifest.process_id):
            self._trigger_audit(manifest.process_id, "domain evaluation incomplete")
            raise PermissionError("ExecutionLayer: all six domains must be recorded.")

        result = action()
        logger.info("Plugin executed: %s", manifest.name)
        return result

    def _trigger_audit(self, process_id: str, reason: str) -> None:
        logger.warning("AUDIT TRIGGERED: pid=%s reason=%s", process_id, reason)
        if self._audit_cb:
            self._audit_cb(process_id, reason)


@dataclass
class AethelGrid:
    """Top-level Gateway -> Orchestration -> Execution facade."""

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
            raise RuntimeError("AethelGrid: substrate metrics not set. Call set_substrate() first.")
        psi = compute_psi(domain_scores, self._substrate)
        if psi > PSI_THRESHOLD:
            raise RuntimeError(
                f"AethelGrid: Psi={psi:.4f} exceeds 1.0 threshold. "
                "Process throttled per Spec Section 2."
            )
        return self.execution.run(manifest, session_id, domain_scores, action)


def compute_efficiency_score(output_capacity: float, v_h: float) -> float:
    if v_h <= 0:
        raise ValueError("V_h must be positive.")
    return output_capacity / (C_a_DIVISOR * v_h)


def compute_psi(
    domain_scores: List[DomainScore],
    substrate: SubstrateMetrics,
) -> float:
    total = sum(score.disruption * substrate.omega for score in domain_scores)
    return total / (C_a_DIVISOR * substrate.v_h)


def psi_gate(
    domain_scores: List[DomainScore],
    substrate: SubstrateMetrics,
) -> bool:
    return compute_psi(domain_scores, substrate) <= PSI_THRESHOLD


def validate_efficiency(
    output_capacity: float,
    v_h: float,
    threshold: float = 1.0,
) -> bool:
    return compute_efficiency_score(output_capacity, v_h) > threshold


__all__ = [
    "AethelGrid",
    "Domain",
    "DomainScore",
    "EffectivenessLedger",
    "ExecutionLayer",
    "GatewayLayer",
    "LedgerEntry",
    "OrchestrationLayer",
    "ProcessManifest",
    "SubstrateMetrics",
    "compute_efficiency_score",
    "compute_psi",
    "psi_gate",
    "validate_efficiency",
]
