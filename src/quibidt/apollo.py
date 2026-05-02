"""Apollo Executive -- interrupt priority and thermal guard."""

from __future__ import annotations

import enum
from typing import List

from config.quibidt_constants import (
    BIO_PRESENCE_INTERRUPT,
    THERMAL_CRITICAL,
    BUSBAR_THERMAL_HALT_C,
)


class InterruptPriority(enum.IntEnum):
    """Interrupt levels, lower is higher priority."""

    BIO_PRESENCE = 0
    THERMAL = 1
    SYSTEM = 2
    APPLICATION = 3
    BACKGROUND = 4


class ApolloExecutive:
    """Manages task jettison by interrupt priority."""

    def __init__(self) -> None:
        self.active_tasks: List[str] = []
        self.thermal_c: float = 25.0

    def jettison_below(self, priority: InterruptPriority) -> List[str]:
        """Drop all tasks below *priority* and return them."""
        prefix = f"P{priority.value}"
        cut = [t for t in self.active_tasks if not t.startswith(prefix)]
        self.active_tasks = [t for t in self.active_tasks if t.startswith(prefix)]
        return cut

    def check_thermal(self, temp_c: float) -> bool:
        """Return True and jettison if *temp_c* >= busbar halt."""
        self.thermal_c = temp_c
        if temp_c >= BUSBAR_THERMAL_HALT_C:
            self.jettison_below(InterruptPriority.THERMAL)
            return True
        return False
