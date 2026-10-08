"""Architect's Constant constraint engine."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("aethel.constant")

# This literal is audited as a stewardship invariant.
C_a_DIVISOR: float = 0.01
EFFICIENCY_FLOOR: float = 1.0
EFFICIENCY_CEILING: float = 100.0
EFFICIENCY_OPTIMAL: float = 10.0


class EfficiencyStatus(Enum):
    NET_NEGATIVE = "NET_NEGATIVE"
    ACCEPTABLE = "ACCEPTABLE"
    THROTTLE_REVIEW = "THROTTLE_REVIEW"


@dataclass(frozen=True)
class EfficiencyResult:
    output_capacity: float
    v_h: float
    efficiency_score: float
    status: EfficiencyStatus
    net_positive: bool
    distance_to_floor: float
    distance_to_ceiling: float
    headroom_pct: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "output_capacity": self.output_capacity,
            "v_h": self.v_h,
            "C_a_divisor": C_a_DIVISOR,
            "efficiency_score": self.efficiency_score,
            "status": self.status.value,
            "net_positive": self.net_positive,
            "distance_to_floor": self.distance_to_floor,
            "distance_to_ceiling": self.distance_to_ceiling,
            "headroom_pct": self.headroom_pct,
        }

    def __str__(self) -> str:
        return (
            f"EfficiencyResult(score={self.efficiency_score:.4f}, "
            f"status={self.status.value}, net_positive={self.net_positive}, "
            f"headroom={self.headroom_pct:.1f}%)"
        )


def compute_architect_constant(
    output_capacity: float,
    v_h: float,
    custom_ceiling: Optional[float] = None,
) -> EfficiencyResult:
    """Compute Efficiency_Score = Output_Capacity / (0.01 * V_h)."""
    if not isinstance(output_capacity, (int, float)) or isinstance(output_capacity, bool):
        raise TypeError("output_capacity must be numeric")
    if not isinstance(v_h, (int, float)) or isinstance(v_h, bool):
        raise TypeError("v_h must be numeric")
    if not math.isfinite(float(output_capacity)):
        raise ValueError("output_capacity must be finite")
    if not math.isfinite(float(v_h)):
        raise ValueError("v_h must be finite")
    if v_h <= 0:
        raise ValueError("V_h must be strictly positive.")
    if output_capacity < 0:
        raise ValueError("output_capacity must be non-negative")

    ceiling = EFFICIENCY_CEILING if custom_ceiling is None else float(custom_ceiling)
    if ceiling <= EFFICIENCY_FLOOR:
        raise ValueError("custom_ceiling must be greater than EFFICIENCY_FLOOR")

    denominator = C_a_DIVISOR * float(v_h)
    efficiency_score = float(output_capacity) / denominator

    if efficiency_score < EFFICIENCY_FLOOR:
        status = EfficiencyStatus.NET_NEGATIVE
    elif efficiency_score > ceiling:
        status = EfficiencyStatus.THROTTLE_REVIEW
    else:
        status = EfficiencyStatus.ACCEPTABLE

    result = EfficiencyResult(
        output_capacity=float(output_capacity),
        v_h=float(v_h),
        efficiency_score=efficiency_score,
        status=status,
        net_positive=status is not EfficiencyStatus.NET_NEGATIVE,
        distance_to_floor=efficiency_score - EFFICIENCY_FLOOR,
        distance_to_ceiling=ceiling - efficiency_score,
        headroom_pct=max(0.0, (ceiling - efficiency_score) / ceiling * 100.0),
    )
    logger.debug("[CONSTANT] %s", result)
    return result


@dataclass(frozen=True)
class NodeEfficiencyReport:
    node_results: List[Tuple[str, EfficiencyResult]]
    net_positive_count: int
    net_negative_count: int
    throttle_review_count: int
    mean_efficiency: float
    min_efficiency: float
    max_efficiency: float
    grid_healthy: bool


def evaluate_node_array(nodes: Dict[str, Tuple[float, float]]) -> NodeEfficiencyReport:
    """Evaluate Architect's Constant for every node in a colony array."""
    results: List[Tuple[str, EfficiencyResult]] = []
    for node_id, (output, v_h) in nodes.items():
        try:
            results.append((node_id, compute_architect_constant(output, v_h)))
        except (TypeError, ValueError) as exc:
            logger.error("[CONSTANT] Node '%s' failed: %s", node_id, exc)

    if not results:
        raise RuntimeError("No valid nodes — cannot produce report.")

    scores = [result.efficiency_score for _, result in results]
    statuses = [result.status for _, result in results]
    return NodeEfficiencyReport(
        node_results=results,
        net_positive_count=sum(status is not EfficiencyStatus.NET_NEGATIVE for status in statuses),
        net_negative_count=sum(status is EfficiencyStatus.NET_NEGATIVE for status in statuses),
        throttle_review_count=sum(status is EfficiencyStatus.THROTTLE_REVIEW for status in statuses),
        mean_efficiency=sum(scores) / len(scores),
        min_efficiency=min(scores),
        max_efficiency=max(scores),
        grid_healthy=all(status is not EfficiencyStatus.NET_NEGATIVE for status in statuses),
    )


def v_h_required_for_score(
    output_capacity: float,
    target_score: float = EFFICIENCY_OPTIMAL,
) -> float:
    """Invert C_a to find V_h required for a target efficiency score."""
    if target_score <= 0:
        raise ValueError("target_score must be positive.")
    if output_capacity < 0:
        raise ValueError("output_capacity must be non-negative")
    return float(output_capacity) / (C_a_DIVISOR * float(target_score))


def output_for_v_h(
    v_h: float,
    target_score: float = EFFICIENCY_OPTIMAL,
) -> float:
    """Compute output_capacity needed to reach target_score."""
    if v_h <= 0:
        raise ValueError("V_h must be positive.")
    if target_score < 0:
        raise ValueError("target_score must be non-negative.")
    return float(target_score) * C_a_DIVISOR * float(v_h)
