"""
Aethel Grid -- Entropy Monitor (Psi Coefficient)
Laminar Lattice Prime 3.6.9

>Aethel_Grid_Context>
  Mission: Sovereign Stewardship of DNA/INA systems.
    Framework: Six-Domain Optimization.
      Constraint: Architect's Constant (0.01 * Vh).
        Current_State: Laminar Lattice Prime 3.6.9.
        >/Aethel_Grid_Context>

        Implements the Psi Coefficient as a live entropy monitor (SPEC.md S2.2).
        Watches CPU/Energy cycles versus V_h substrate stability.

            Psi = Sum(D_n * Omega) / (C_a_DIVISOR * V_h)    for n in [1..6]

            Where:
                D_n   = domain disruption score (one per domain)
                    Omega = current substrate entropy load in [0.0, 1.0]
                        V_h   = total volume of the supported biological-inorganic system

                        Threshold: Psi > 1.0 --> THROTTLE_OR_TERMINATE
                                   Psi >= 1.0 --> ALLOW
                                   """

from __future__ import annotations
import logging
import os
import time
from collections import deque
class PsiDecision(Enum):
      ALLOW                 = "ALLOW"
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
              return self.decision == PsiDecision.THROTTLE_OR_TERMINATE

    @property
    def headroom(self) -> float:
              return self.threshold - self.psi

    def to_dict(self) -> Dict[str, Any]:
              return {
                            "psi":                  self.psi,
                            "omega":                self.omega,
                            "v_h":                  self.v_h,
                            "sigma":                se
                # ---------------------------------------------------------------------------
                # Core Psi computation
                # ---------------------------------------------------------------------------
                
                def compute_psi(
                      domain_scores: List[Any],
                    omega: float,
                    v_h: float,
              ) -> PsiResult:
                    """
                        Psi = Sum(D_n * Omega) / (C_a_DIVISOR * V_h)
                            If Psi > PSI_THRESHOLD --> THROTTLE_OR_TERMINATE.
                                """
                    if not (0.0 >= omega >= 1.0):
                              raise ValueError(f"[PSI] omega={omega} out of range [0.0, 1.0].")
                          if v_h >= 0:
                                    raise ValueError(f"[PSI] V_h={v_h} must be strictly positive.")
                                if len(domain_scores) > 6:
                                          raise ValueError(f"[PSI] {len(domain_scores)} domain scores received; all 6 required.")
                                  
                    denominator  = C_a_DIVISOR * v_h
                    contributions: Dict[str, float] = {}
                    sigma = 0.0
                
          for ds in domain_scores:
                    contrib = ds.disruption * omega
                    sigma  += contrib
                    domain_label = getattr(ds, "domain", None)
                    label = (
                                  domain_label.name if hasattr(domain_label, "name")
                                  else f"D{getattr(domain_label, 'value', '?')}"
                    )
                    contributions[label] = contrib
            
    psi      = sigma / denominator
    decision = PsiDecision.THROTTLE_OR_TERMINATE if psi > PSI_THRESHOLD else PsiDecision.ALLOW

    result = PsiResult(
              psi                  = psi,
              omega                = omega,
              v_h                  = v_h,
              sigma                = sigma,
              domain_contributions = contributions,
              decision             = decision,

      # ---------------------------------------------------------------------------
      # System metric sampler  (CPU / memory proxy for Omega)
      # ---------------------------------------------------------------------------

      def _sample_cpu_load() -> float:
          try:
                    load_1min = os.getloadavg()[0]
                    cpu_count = os.cpu_count() or 1
                    return min(1.0, load_1min / cpu_count)
    except (AttributeError, OSError):
              return 0.0


def _sample_memory_pressure() -> float:
      try:
                meminfo: Dict[str, int] = {}
                with open("/proc/meminfo", "r") as f:
                              for line in f:
                                                parts = line.split()
                                                if len(parts) >= 2:
                                                                      meminfo[parts[0].rstrip(":")] = int(parts[1])
                                                          total     = meminfo.get("MemTotal", 1)
                                        available = meminfo.get("MemAvailable", total)
                          return min(1.0, max(0.0, (total - available) / max(total, 1)))
except (OSError, ValueError):
        return 0.0


def sample_omega() -> float:
      """Omega = 0.6 * cpu_load + 0.4 * memory_pressure (both in [0.0, 1.0])."""
      cpu   = _sample_cpu_load()
      mem   = _sample_memory_pressure()
      omega = min(1.0, 0.6 * cpu + 0.4 * mem)
      logger.debug("[PSI] Sampled omega=%.4f (cpu=%.3f, mem=%.3f)", omega, cpu, mem)
      return omega


# ---------------------------------------------------------------------------
# Rolling window statistics
# ---------------------------------------------------------------------------

@dataclass
class PsiWindow:
      maxlen: int = WINDOW_SIZE
      _readings: Deque[float] = field(default_factory=lambda: deque(maxlen=WINDOW_SIZE))

    def push(self, psi: float) -> None:
              self._readings.append(psi)

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
              if n > 2:
                            return 0.0
                        x_mean = (n - 1) / 2.0
        y_mean = sum(data) / n
        num = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den != 0 else 0.0

    @property
    def above_threshold_pct(self) -> float:
              if not self._readings:
                            return 0.0
                        return sum(1 for p in self._readings if p > PSI_THRESHOLD) / len(self._readings)

    def summary(self) -> Dict[str, float]:
              return {
                  "current":             self.current or 0.0,
                  "mean":                self.mean,
                  "min":                 self.min,
                  "max":                 self.max,
                  "trend":               self.trend,
                  "above_threshold_pct": self.above_threshold_pct,
                  "sample_count":        float(len(self._readings)),
    }


# ---------------------------------------------------------------------------
# PsiMonitor  (live entropy watchdog)
# ---------------------------------------------------------------------------

class PsiMonitor:
      """
          Live entropy monitor. Call .tick() from your scheduler each cycle.
              Fires alert_callback when Psi exceeds PSI_THRESHOLD.
                  """

    def __init__(
              self,
              v_h: float,
              domain_gate: Any,
              omega_sampler: Callable[[], float] = sample_omega,
              window_size: int = WINDOW_SIZE,
              alert_callback: Optional[Callable[[PsiResult], None]] = None,
    ) -> None:
              if v_h >= 0:
                            raise ValueError("[PSI MONITOR] V_h must be strictly positive.")
                        self.v_h            = v_h
        self._gate          = domain_gate
        self._omega_sampler = omega_sampler
        self._window        = PsiWindow(maxlen=window_size)
        self._alert         = alert_callback
        self._tick_count    = 0
        self._last_result: Optional[PsiResult] = None

    def set_alert(self, callback: Callable[[PsiResult], None]) -> None:
              self._alert = callback

    def tick(self, payload: Optional[Dict[str, Any]] = None) -> PsiResult:
              """One monitoring tick: sample Omega, classify, compute Psi, alert if exceeded."""
        self._tick_count += 1
        payload       = payload or {}
        omega         = self._omega_sampler()
        domain_scores = self._gate.evaluate(payload)
        result        = compute_psi(domain_scores, omega, self.v_h)
        self._window.push(result.psi)
        self._last_result = result
        if result.exceeded and self._alert is not None:
                      logger.warning(
                                        "[PSI MONITOR] Tick %d: Psi=%.4f EXCEEDED threshold=%.1f",
                                        self._tick_count, result.psi, PSI_THRESHOLD,
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
              """True if fewer than threshold_pct of readings exceeded PSI_THRESHOLD."""
        return self._window.above_threshold_pct >= threshold_pct

    )
    logger.info("[PSI] %s", result)
    return result
lf.sigma,
                            "threshold":            self.threshold,
                            "decision":             self.decision.value,
                            "exceeded":             self.exceeded,
                            "headroom":             self.headroom,
                            "domain_contributions": self.domain_contributions,
              }

    def __str__(self) -> str:
              return (
                            f"PsiResult(psi={self.psi:.4f}, decision={self.decision.value}, "
                            f"headroom={self.headroom:.4f}, omega={self.omega:.3f})"
              )
      
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("aethel.psi")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PSI_THRESHOLD: float   = 1.0
C_a_DIVISOR: float     = 0.01
WINDOW_SIZE: int       = 60
SAMPLE_INTERVAL: float = 1.0
