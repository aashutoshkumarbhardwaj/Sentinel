from __future__ import annotations

from typing import Any

from sim.simulator import (
    ApprovalRequired,
    IncidentSim,
    ToolError,
    ToolTimeout,
)


class SimulatorClient:
    """
    Client adapter wrapping the environment IncidentSim instance.
    
    Why: Provides a unified call API (`client.call(tool, **kwargs)`) and exposes
    audit log, actions taken, and fixed status.
    """

    def __init__(self, sim: IncidentSim):
        self.sim = sim

    def call(
        self,
        tool: str,
        **kwargs: Any,
    ) -> Any:
        """Forward tool invocation to the environment simulator."""
        return self.sim.call(
            tool,
            **kwargs,
        )

    @property
    def audit_log(self):
        """Return full audit trail of executed tools."""
        return self.sim.audit_log

    @property
    def actions_taken(self):
        """Return list of production actions applied."""
        return self.sim.actions_taken

    @property
    def fixed(self):
        """Check if environment incident has been resolved."""
        return self.sim.fixed