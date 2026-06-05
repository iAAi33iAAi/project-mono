"""
Aethel Grid -- Laminar Lattice Prime 3.6.9
Sovereign Stewardship of DNA/INA systems.

Public API surface for the stewardship kernel.
"""

from .stewardship import (
    AethelGrid,
    Domain,
    DomainScore,
    EffectivenessLedger,
    ExecutionLayer,
    GatewayLayer,
    LedgerEntry,
    OrchestrationLayer,
    ProcessManifest,
    SubstrateMetrics,
    compute_efficiency_score,
    compute_psi,
    psi_gate,
    validate_efficiency,
)

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

__version__ = "3.6.9"
__lattice__ = "Laminar Lattice Prime"
