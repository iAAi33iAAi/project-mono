"""
Aethel Grid 1440 System -- QUIBIDT Operational Parameters.

Every constant in this module is drawn from the canonical
parameter table.  These values are the constitutional bedrock
of the system: the Architect's Constant ensures technology
serves humanity (1% tech, 99% human), and every threshold,
ratio, and priority flows from that premise.

Modification of these values requires a Broken-to-Better
case and unanimous Approver sign-off.
"""

from __future__ import annotations

# -- Architect's Constant ------------------------------------
# Hard-coded normalization floor: technology thrives at 1%
# so humans thrive at 99%.  Applied as 0.01 x V_h.
ARCHITECTS_CONSTANT: float = 0.01

# -- QUIBIDT Safety Kernel: Flow States ----------------------
# Love Invariant: minimum tribal equilibrium score to enter
# the Laminar (flow) state.
LOVE_INVARIANT: float = 0.07

# Score below which the system exits Laminar -> Stagnant.
LAMINAR_EXIT_THRESHOLD: float = 0.04

# Score at which the system enters Turbulent (high entropy).
TURBULENT_ENTER_THRESHOLD: float = -0.05

# -- 1440 System Treasury ------------------------------------
# Ratio of treasury assets (gold + digital) to outstanding
# minute-unit claims.  Below MINIMUM triggers automatic halt.
COLLATERAL_RATIO_TARGET: float = 1.1
COLLATERAL_RATIO_MINIMUM: float = 1.0

# -- Cryptographic Standard ----------------------------------
# Formally verified, fast hashing for the immutable,
# hash-chained audit ledger.
HASHING_METHOD: str = "BLAKE3"

# -- Apollo Executive Layer: Interrupt Priorities -------------
# Lower number = higher priority.
# Priority 0: biological presence causes immediate jettison
# of low-priority AI tasks.
BIO_PRESENCE_INTERRUPT: int = 0

# Priority 1: fluidics / thermal failure -- second only to
# biological presence.
THERMAL_CRITICAL: int = 1

# -- Timing --------------------------------------------------
# Real-Time Operating target in milliseconds.  Failure to
# meet this heartbeat triggers immediate state degradation.
RTO_TARGET_MS: float = 3.7
RTO_TARGET_NS: int = 3_700_000

# Prime Grapple jitter lock (71 x 1.5 = 106.5 ns).  When
# average timing jitter exceeds this, operations halt.
PRIME_GRAPPLE_NS: float = 106.5
PRIME_GRAPPLE_BASE: int = 71
PRIME_GRAPPLE_FACTOR: float = 1.5

# -- Aethel Grid Architecture --------------------------------
# Power of Seven resonance harmonic (7^3 = 343).
# Used for grid-wide synchronization as 0.343.
POWER_OF_SEVEN: int = 343
POWER_OF_SEVEN_HARMONIC: float = 0.343

# -- Physical Infrastructure ---------------------------------
# Node-001 (Bethel Acres, OK): Class 5 vault for gold.
VAULT_SECURITY_CLASS: int = 5
NODE_001_LOCATION: str = "Bethel Acres, OK"

# Node-002 48V DC bus: soft-halt at 45C busbar temperature.
BUSBAR_THERMAL_HALT_C: int = 45

# -- MANNA Colony Safety Kernel ------------------------------
# Deduction applied to corporate-flagged transactions.
CORPORATE_SIPHON_RATE: float = 0.15
