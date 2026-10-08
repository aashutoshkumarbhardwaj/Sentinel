from __future__ import annotations

from typing import Any

from sim.simulator import (
    IncidentSim,
    ToolError,
    ToolTimeout,
    ApprovalRequired,
)


class SimulatorClient:

    def __init__(self, sim: IncidentSim):
        self.sim = sim

    def call(
        self,
        tool: str,
        **kwargs: Any,
    ) -> Any:
        return self.sim.call(
            tool,
            **kwargs,
        )

    @property
    def audit_log(self):
        return self.sim.audit_log

    @property
    def actions_taken(self):
        return self.sim.actions_taken

    @property
    def fixed(self):
        return self.sim.fixed