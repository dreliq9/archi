"""Live validator — orchestrates rule evaluation after graph mutations.

Hooks into BuildingGraph.on_mutate to mark the violation cache as dirty.
On get_violations(), re-evaluates all declarative + computed rules.
"""

from __future__ import annotations

from archi.graph.model import BuildingGraph
from archi.rules.computed.egress import check_egress
from archi.rules.computed.structural import check_structural_spans
from archi.rules.computed.ventilation import check_ventilation
from archi.rules.engine import RuleEngine


class LiveValidator:
    def __init__(self, graph: BuildingGraph, jurisdiction: str = "IRC-2021"):
        self._graph = graph
        self._engine = RuleEngine(jurisdiction)
        self._engine.register_computed_rule(check_egress)
        self._engine.register_computed_rule(check_ventilation)
        self._engine.register_computed_rule(check_structural_spans)
        self._violations: list[dict] = []
        self._dirty = True

        original_callback = graph._on_mutate

        def _on_mutate(event: dict) -> None:
            self._dirty = True
            if original_callback is not None:
                original_callback(event)

        graph._on_mutate = _on_mutate

    def get_violations(self) -> list[dict]:
        if self._dirty:
            self._violations = self._engine.evaluate_all(self._graph)
            self._dirty = False
        return list(self._violations)

    def get_violation_counts(self) -> dict[str, int]:
        violations = self.get_violations()
        counts: dict[str, int] = {}
        for v in violations:
            sev = v.get("severity", "unknown")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def has_errors(self) -> bool:
        return self.get_violation_counts().get("error", 0) > 0
