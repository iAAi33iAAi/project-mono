"""Heartbeat and jitter enforcement."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from config.quibidt_constants import (
    RTO_TARGET_NS,
    PRIME_GRAPPLE_NS,
)


@dataclass(frozen=True)
class HeartbeatResult:
    """Single heartbeat measurement."""

    elapsed_ns: int
    ok: bool


@dataclass(frozen=True)
class JitterResult:
    """Rolling jitter analysis."""

    avg_ns: float
    locked: bool


class TimingEnforcer:
    """Enforces RTO heartbeat and prime-grapple jitter lock."""

    def __init__(self, window: int = 64) -> None:
        self.window = window
        self.samples: deque[int] = deque(maxlen=window)

    def heartbeat(self, elapsed_ns: int) -> HeartbeatResult:
        """Return pass/fail against RTO target."""
        return HeartbeatResult(
            elapsed_ns=elapsed_ns,
            ok=elapsed_ns <= RTO_TARGET_NS,
        )

    def record_jitter(self, jitter_ns: int) -> JitterResult:
        """Record sample and check prime-grapple lock."""
        self.samples.append(jitter_ns)
        avg = sum(self.samples) / len(self.samples)
        return JitterResult(avg_ns=avg, locked=avg > PRIME_GRAPPLE_NS)
