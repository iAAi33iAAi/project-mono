# Aethel Grid 1440  Operational Parameters

> Canonical reference for the QUIBIDT governance engine and 1440 Treasury.

## Overview

The Aethel Grid 1440 system governs tribal equilibrium through a tri-state
flow model (Laminar -> Stagnant -> Turbulent), a collateralized treasury, an
interrupt-priority executive, real-time timing enforcement, and a
corporate-siphon accounting kernel.

## Parameters

| # | Parameter | Symbol / Key | Value | Component |
|---|-----------|-------------|-------|-----------|
| 1 | Architect's Constant | `ARCHITECT_CONSTANT` | 0.01 | QUIBIDT / Aethel Grid |
| 2 | Love Invariant | `LOVE_INVARIANT` | 0.07 | QUIBIDT -- laminar entry |
| 3 | Laminar Exit | `LAMINAR_EXIT` | 0.04 | QUIBIDT -- graceful fall |
| 4 | Turbulent Enter | `TURBULENT_ENTER` | -0.05 | QUIBIDT -- turbulent entry |
| 5 | Collateral Target | `COLLATERAL_TARGET` | 1.1 | 1440 Treasury |
| 6 | Collateral Minimum | `COLLATERAL_MIN` | 1.0 | 1440 Treasury |
| 7 | Hashing Method | `HASH_METHOD` | blake3 | 1440 Audit Trail |
| 8 | BIO_PRESENCE Interrupt | `BIO_PRESENCE_INTERRUPT` | 0 | Apollo Executive |
| 9 | THERMAL_CRITICAL | `THERMAL_CRITICAL` | 1 | Apollo Executive |
| 10 | RTO Target | `RTO_TARGET_NS` | 3 700 000 ns | Heartbeat |
| 11 | Prime Grapple | `PRIME_GRAPPLE_NS` | 106.5 ns | Colony Safety |
| 12 | Power of Seven | `POWER_OF_SEVEN` | 343 | Aethel Grid sync |
| 13 | Vault Security | `VAULT_SECURITY_CLASS` | 5 | Node-001 |
| 14 | Busbar Thermal Halt | `BUSBAR_THERMAL_HALT_C` | 45 C | Node-002 |
| 15 | Corporate Siphon | `CORPORATE_SIPHON_RATE` | 0.15 | MANNA Colony |

## Components

### QUIBIDT State Machine (`state_machine.py`)
Tri-state flow model with hysteresis. Transitions governed by Love Invariant
(>= 0.07 -> LAMINAR), Laminar Exit (> 0.04 -> STAGNANT from LAMINAR), and
Turbulent Enter (>= -0.05 -> TURBULENT).

### 1440 Treasury (`treasury.py`)
Gold + digital reserves backing outstanding obligations. Disbursement halts
if collateral ratio falls below 1.0:1 minimum. Target ratio is 1.1:1.

### Apollo Executive (`apollo.py`)
Five-level interrupt priority (BIO_PRESENCE=0 highest through BACKGROUND=4).
Thermal guard jettisons tasks when busbar temperature >= 45 C.

### Timing Enforcer (`timing.py`)
Heartbeat must complete within 3.7 ms RTO target. Jitter lock engages when
rolling average exceeds the 106.5 ns prime-grapple threshold.

### MANNA Colony (`manna.py`)
Corporate transactions siphoned at 15%. Net proceeds split: 1% to technology
(Architect's Constant), remainder to human share.

### Aethel Grid (`aethel_grid.py`)
Node registry with two canonical nodes: NODE-001 (Bethel Acres Vault, Class 5)
and NODE-002 (48V DC Bus, 45 C halt). Harmonic factor derived from
Power of Seven (343 / 1000 = 0.343).

## Source

All constants defined in `config/quibidt_constants.py`.
Module implementations in `src/quibidt/`.
