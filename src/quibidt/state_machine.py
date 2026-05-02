"""QUIBIDT State Machine -- Flow-state governance engine."""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from typing import List

from config.quibidt_constants import (
    LOVE_INVARIANT,
    LAMINAR_EXIT,
    TURBULENT_ENTER,
)


class FlowState(enum.Enum):
    """Tri-state flow model."""

    LAMINAR = "laminar"
    STAGNANT = "stagnant"
    TURBULENT = "turbulent"


@dataclass(frozen=True)
class StateTransition:
    """Immutable record of a state change."""

    timestamp_ns: int
    old_state: FlowState
    new_state: FlowState
    score: float


class QUIBIDTStateMachine:
    """Hysteresis-aware state machine for tribal equilibrium."""

    def __init__(self) -> None:
        self.state: FlowState = FlowState.STAGNANT
        self.history: List[StateTransition] = []

    def evaluate(self, score: float) -> FlowState:
        """Evaluate *score* and transition if thresholds crossed."""
        old = self.state
        if score >= LOVE_INVARIANT:
            self.state = FlowState.LAMINAR
        elif score <= TURBULENT_ENTER:
            self.state = FlowState.TURBULENT
        elif self.state is FlowState.LAMINAR and score < LAMINAR_EXIT:
            self.state = FlowState.STAGNANT
        if self.state is not old:
            self.history.append(
                StateTransition(
                    timestamp_ns=time.time_ns(),
                    old_state=old,
                    new_state=self.state,
                    score=score,
                )
            )
        return self.state
