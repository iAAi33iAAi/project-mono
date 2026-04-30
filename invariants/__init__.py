"""
ALGA_FOLD_KERNEL — Invariant framework.

Every invariant is a subclass of ``BaseInvariant`` that implements ``evaluate``.
The loader discovers and instantiates all invariants from this package
automatically so the kernel runner never needs hard-coded references.
"""

from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

__all__ = ["BaseInvariant", "InvariantResult", "load_invariants"]

KERNEL_VERSION = "alga-fold-kernel v0.1.0"


@dataclass(frozen=True)
class InvariantResult:
    """Immutable outcome of a single invariant evaluation."""
    name: str
    status: str
    details: str = ""
    remediation: list[str] = field(default_factory=list)

    def passed(self) -> bool:
        return self.status == "pass"


class BaseInvariant(ABC):
    """Contract every invariant module must satisfy."""
    name: str = "unnamed_invariant"

    @abstractmethod
    def evaluate(self, ctx: dict[str, Any]) -> InvariantResult:
        ...


def load_invariants() -> list[BaseInvariant]:
    """Auto-discover and instantiate every BaseInvariant subclass."""
    package = importlib.import_module(__package__)
    instances: list[BaseInvariant] = []
    for info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        mod = importlib.import_module(info.name)
        for attr_name in dir(mod):
            obj = getattr(mod, attr_name)
            if isinstance(obj, type) and issubclass(obj, BaseInvariant) and obj is not BaseInvariant:
                instances.append(obj())
    instances.sort(key=lambda inv: inv.name)
    return instances
