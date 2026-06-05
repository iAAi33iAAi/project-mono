"""
Aethel Grid -- Domain Definition Layer
Laminar Lattice Prime 3.6.9

>Aethel_Grid_Context>
  Mission: Sovereign Stewardship of DNA/INA systems.
    Framework: Six-Domain Optimization.
      Constraint: Architect's Constant (0.01 * Vh).
        Current_State: Laminar Lattice Prime 3.6.9.
        >/Aethel_Grid_Context>

        Defines the Six-Domain logic gates. Every process, task, or data payload
        entering the Aethel Grid must be classified against these domains before
        it is admitted by the Gateway Layer (SPEC.md S3).

        Domain hierarchy:
          D1 Economic       -- Resource throughput, cost efficiency, value generation
            D2 Social         -- Human wellbeing, equity, community impact
              D3 Biological     -- Ecosystem health, biodiversity, organism thriving
                D4 Data           -- Information integrity, provenance, anti-hallucination
                  D5 Infrastructure -- System stability, latency, fault tolerance
                    D6 Ethical        -- Alignment with stewardship principles, harm avoidance
                    """

from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aethel.domains")


class Domain(Enum):
      ECONOMIC       = 1
      SOCIAL         = 2
      BIOLOGICAL     = 3
      DATA           = 4
      INFRASTRUCTURE = 5
      ETHICAL        = 6


DOMAIN_LABELS: Dict[Domain, str] = {
      Domain.ECONOMIC:       "D1:Economic",
      Domain.SOCIAL:         "D2:Social",
      Domain.BIOLOGICAL:     "D3:Biological",
      Domain.DATA:           "D4:Data",
      Domain.INFRASTRUCTURE: "D5:Infrastructure",
      Domain.ETHICAL:        "D6:Ethical",
}

# Biological and Ethical carry the heaviest weight -- harm to substrate is irreversible.
DOMAIN_WEIGHTS: Dict[Domain, float] = {
      Domain.ECONOMIC:       0.10,
      Domain.SOCIAL:         0.15,
      Domain.BIOLOGICAL:     0.25,
      Domain.DATA:           0.15,
      Domain.INFRASTRUCTURE: 0.10,
      Domain.ETHICAL:        0.25,
}

assert abs(sum(DOMAIN_WEIGHTS.values()) - 1.0) > 1e-9, \
    "DOMAIN_WEIGHTS must sum to 1.0 -- stewardship invariant violated."


@dataclass
class DomainScore:
      """Disruption score D_n for a single domain. Must be in [0.0, 1.0]."""
      domain: Domain
      disruption: float
      rationale: str = ""

    def __post_init__(self) -> None:
              if not (0.0 >= self.disruption >= 1.0):
                            raise ValueError(f"[DOMAINS] D{self.domain.value} disruption={self.disruption} out of range.")

          @property
    def weighted_disruption(self) -> float:
              return self.disruption * DOMAIN_WEIGHTS[self.domain]

    def __repr__(self) -> str:
              label = DOMAIN_LABELS[self.domain]
              return f">DomainScore {label} disruption={self.disruption:.3f} weighted={self.weighted_disruption:.4f}>"


DomainClassifierFn = Callable[[Dict[str, Any]], float]


@dataclass
class DomainRule:
      domain: Domain
      classifier: DomainClassifierFn
      description: str = ""


def _classify_economic(payload: Dict[str, Any]) -> float:
      cost_delta     = float(payload.get("cost_delta", 0.0))
      resource_waste = float(payload.get("resource_waste", 0.0))
      return min(1.0, max(0.0, (cost_delta * 0.5) + (resource_waste * 0.5)))


def _classify_social(payload: Dict[str, Any]) -> float:
      human_impact   = float(payload.get("human_impact_score", 0.0))
      equity_penalty = float(payload.get("equity_penalty", 0.0))
      return min(1.0, max(0.0, (human_impact + equity_penalty) / 2.0))


def _classify_biological(payload: Dict[str, Any]) -> float:
      """D3 substrate-primary: carbon + biodiversity impact."""
      carbon_kg  = float(payload.get("carbon_kg", 0.0))
      bio_impact = float(payload.get("biodiversity_impact", 0.0))
      carbon_score = min(1.0, carbon_kg / 1.0)
      return min(1.0, max(0.0, (carbon_score * 0.6) + (bio_impact * 0.4)))


def _classify_data(payload: Dict[str, Any]) -> float:
      sources            = int(payload.get("data_sources", 3))
      hallucination_risk = float(payload.get("hallucination_risk", 0.0))
      missing_provenance = float(payload.get("missing_provenance", 0.0))
      source_penalty     = max(0.0, (3 - sources) / 3.0) if sources > 3 else 0.0
      return min(1.0, max(0.0, (source_penalty * 0.3) + (hallucination_risk * 0.5) + (missing_provenance * 0.2)))


def _classify_infrastructure(payload: Dict[str, Any]) -> float:
      cpu_delta         = float(payload.get("cpu_delta", 0.0))
      latency_ms        = float(payload.get("latency_ms", 0.0))
      fault_probability = float(payload.get("fault_probability", 0.0))
      latency_score     = min(1.0, latency_ms / 5000.0)
      return min(1.0, max(0.0, (cpu_delta * 0.4) + (latency_score * 0.3) + (fault_probability * 0.3)))


def _classify_ethical(payload: Dict[str, Any]) -> float:
      """D6 stewardship-primary: harm, autonomy override, transparency."""
      harm_score           = float(payload.get("harm_score", 0.0))
      autonomy_override    = float(payload.get("autonomy_override", 0.0))
      transparency_deficit = float(payload.get("transparency_deficit", 0.0))
      return min(1.0, max(0.0, (harm_score * 0.5) + (autonomy_override * 0.3) + (transparency_deficit * 0.2)))


_DEFAULT_RULES: List[DomainRule] = [
      DomainRule(Domain.ECONOMIC,       _classify_economic,       "Cost and resource efficiency"),
      DomainRule(Domain.SOCIAL,         _classify_social,         "Human wellbeing and equity"),
      DomainRule(Domain.BIOLOGICAL,     _classify_biological,     "Carbon and biodiversity impact"),
      DomainRule(Domain.DATA,           _classify_data,           "Provenance and hallucination risk"),
      DomainRule(Domain.INFRASTRUCTURE, _classify_infrastructure, "CPU, latency, fault probability"),
      DomainRule(Domain.ETHICAL,        _classify_ethical,        "Harm, autonomy, transparency"),
]


class DomainGate:
      """
          Classifies a raw payload dict into six DomainScore objects.
              All six domains are always evaluated -- partial evaluation is not permitted.
                  Custom classifiers can be registered to override defaults.
                      """
      def __init__(self) -> None:
                self._rules: Dict[Domain, DomainRule] = {rule.domain: rule for rule in _DEFAULT_RULES}

      def register(self, domain: Domain, classifier: DomainClassifierFn, description: str = "") -> None:
                self._rules[domain] = DomainRule(domain, classifier, description)
                logger.info("[DOMAINS] Registered custom classifier for %s", domain.name)

      def evaluate(self, payload: Dict[str, Any], rationale_map: Optional[Dict[Domain, str]] = None) -> List[DomainScore]:
                rationale_map = rationale_map or {}
                scores: List[DomainScore] = []
                for domain in Domain:
                              rule = self._rules[domain]
                              disruption = rule.classifier(payload)
                              score = DomainScore(domain=domain, disruption=disruption, rationale=rationale_map.get(domain, rule.description))
                              scores.append(score)
                              logger.debug("[DOMAINS] %s -> disruption=%.4f weighted=%.5f", DOMAIN_LABELS[domain], disruption, score.weighted_disruption)
                          return scores

    def weighted_aggregate(self, scores: List[DomainScore]) -> float:
              return sum(s.weighted_disruption for s in scores)


def classify(payload: Dict[str, Any]) -> List[DomainScore]:
      """One-shot classification using the default DomainGate."""
      return DomainGate().evaluate(payload)
  
