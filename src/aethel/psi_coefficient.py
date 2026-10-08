"""Psi entropy monitor for the Aethel stewardship layer."""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

C_a_DIVISOR: float = 0.01
PSI_THRESHOLD: float = 1.0
WINDOW_SIZE: int = 60
SAMPLE_INTERVAL: float = 1.0

logger = logging.getLogger("aethel.psi")


class PsiDecision(Enum):
    ALLOW = "ALLOW"
    THROTTLE_OR_TERMINATE = "THROTTLE_OR_TERMINATE"


@dataclass(frozen=True)
class PsiResult:
    psi: float
    omega: float
    v_h: float
    sigma: float
    domain_contributions: Dict[str, float]
    decision: PsiDecision
    threshold: float = PSI_THRESHOLD

    @property
    def exceeded(self) -> bool:
        return self.decision is PsiDecision.THROTTLE_OR_TERMINATE

    @property
    def headroom(self) -> float:
        return self.threshold - self.psi

    def to_dict(self) -> Dict[str, Any]:
        return {
            "psi": self.psi,
            "omega": self.omega,
            "v_h": self.v_h,
            "sigma": self.sigma,
            "threshold": self.threshold,
            "decision": self.decision.value,
            "exceeded": self.exceeded,
            "headroom": self.headroom,
            "domain_contributions": self.domain_contributions,
        }

    def __str__(self) -> str:
        return (
            f"PsiResult(psi={self.psi:.4f}, decision={self.decision.value}, "
            f"headroom={self.headroom:.4f}, omega={self.omega:.3f})"
        )


def compute_psi(
    domain_scores: List[Any],
    omega: float,
    v_h: float,
) -> PsiResult:
    """Compute Psi = Sum(D_n * Omega) / (0.01 * V_h)."""
    if not 0.0 <= omega <= 1.0:
        raise ValueError(f"[PSI] omega={omega} out of range [0.0, 1.0].")
    if v_h <= 0:
        raise ValueError("[PSI] V_h must be strictly positive.")
    if len(domain_scores) > 6:
        raise ValueError("[PSI] at most six domain scores are permitted.")

    denominator = C_a_DIVISOR * v_h
    contributions: Dict[str, float] = {}
    sigma = 0.0

    for score in domain_scores:
        disruption = float(score.disruption)
        if not 0.0 <= disruption <= 1.0:
            raise ValueError("[PSI] domain disruption must be in [0.0, 1.0].")
        value = disruption * omega
        sigma += value
        domain = getattr(score, "domain", None)
        label = (
            domain.name
            if hasattr(domain, "name")
            else f"D{getattr(domain, 'value', '?')}"
        )
        contributions[label] = value

    psi = sigma / denominator
    decision = (
        PsiDecision.THROTTLE_OR_TERMINATE
        if psi > PSI_THRESHOLD
        else PsiDecision.ALLOW
    )
    result = PsiResult(
        psi=psi,
        omega=omega,
        v_h=v_h,
        sigma=sigma,
        domain_contributions=contributions,
        decision=decision,
    )
    logger.debug("[PSI] %s", result)
    return result


def _sample_cpu_load() -> float:
    try:
        load_1min = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 1
        return min(1.0, max(0.0, load_1min / cpu_count))
    except (AttributeError, OSError):
        return 0.0


def _sample_memory_pressure() -> float:
    try:
        meminfo: Dict[str, int] = {}
        with open("/proc/meminfo", encoding="utf-8") as file:
            for line in file:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = int(parts[1])
        total = meminfo.get("MemTotal", 1)
        available = meminfo.get("MemAvailable", total)
        return min(1.0, max(0.0, (total - available) / max(total, 1)))
    except (OSError, ValueError):
        return 0.0


def sample_omega() -> float:
    """Omega = 0.6 * CPU load + 0.4 * memory pressure."""
    cpu = _sample_cpu_load()
    memory = _sample_memory_pressure()
    omega = min(1.0, max(0.0, 0.6 * cpu + 0.4 * memory))
    logger.debug("[PSI] omega=%.4f cpu=%.3f memory=%.3f", omega, cpu, memory)
    return omega


@dataclass
class PsiWindow:
    maxlen: int = WINDOW_SIZE
    _readings: Deque[float] = field(init=False)

    def __post_init__(self) -> None:
        if self.maxlen <= 0:
            raise ValueError("maxlen must be positive")
        self._readings = deque(maxlen=self.maxlen)

    def push(self, psi: float) -> None:
        self._readings.append(float(psi))

    @property
    def current(self) -> Optional[float]:
        return self._readings[-1] if self._readings else None

    @property
    def mean(self) -> float:
        return sum(self._readings) / len(self._readings) if self._readings else 0.0

    @property
    def max(self) -> float:
        return max(self._readings) if self._readings else 0.0

    @property
    def min(self) -> float:
        return min(self._readings) if self._readings else 0.0

    @property
    def trend(self) -> float:
        data = list(self._readings)
        n = len(data)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(data) / n
        numerator = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator else 0.0

    @property
    def above_threshold_pct(self) -> float:
        if not self._readings:
            return 0.0
        return sum(psi > PSI_THRESHOLD for psi in self._readings) / len(self._readings)

    def summary(self) -> Dict[str, float]:
        return {
            "current": self.current or 0.0,
            "mean": self.mean,
            "min": self.min,
            "max": self.max,
            "trend": self.trend,
            "above_threshold_pct": self.above_threshold_pct,
            "sample_count": float(len(self._readings)),
        }


class PsiMonitor:
    """Live entropy watchdog."""

    def __init__(
        self,
        v_h: float,
        domain_gate: Any,
        omega_sampler: Callable[[], float] = sample_omega,
        window_size: int = WINDOW_SIZE,
        alert_callback: Optional[Callable[[PsiResult], None]] = None,
    ) -> None:
        if v_h <= 0:
            raise ValueError("[PSI MONITOR] V_h must be strictly positive.")
        self.v_h = v_h
        self._gate = domain_gate
        self._omega_sampler = omega_sampler
        self._window = PsiWindow(window_size)
        self._alert = alert_callback
        self._tick_count = 0
        self._last_result: Optional[PsiResult] = None

    def set_alert(self, callback: Callable[[PsiResult], None]) -> None:
        self._alert = callback

    def tick(self, payload: Optional[Dict[str, Any]] = None) -> PsiResult:
        self._tick_count += 1
        omega = self._omega_sampler()
        domain_scores = self._gate.evaluate(payload or {})
        result = compute_psi(domain_scores, omega, self.v_h)
        self._window.push(result.psi)
        self._last_result = result

        if result.exceeded and self._alert is not None:
            logger.warning(
                "[PSI MONITOR] Tick %d: Psi=%.4f exceeded threshold=%.1f",
                self._tick_count,
                result.psi,
                PSI_THRESHOLD,
            )
            self._alert(result)
        return result

    @property
    def window_summary(self) -> Dict[str, float]:
        return self._window.summary()

    @property
    def last_result(self) -> Optional[PsiResult]:
        return self._last_result

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def is_stable(self, threshold_pct: float = 0.05) -> bool:
        if not 0.0 <= threshold_pct <= 1.0:
            raise ValueError("threshold_pct must be in [0.0, 1.0].")
        return self._window.above_threshold_pct < threshold_pct
