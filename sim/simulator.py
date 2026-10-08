"""
Incident simulator -- the ONLY interface your agent should use to observe or
change the "production" world. Pure standard library. No network access.

    from sim.simulator import IncidentSim, ToolError, ToolTimeout, ApprovalRequired
    sim = IncidentSim("sim/scenarios/s1_bad_deploy.json", seed=7, chaos=True)
    sim.call("search_logs", service="payments-api", query="error")

Rules of the exercise
- Do not open the scenario JSON files from inside your agent. Read them as a
  human if you wish, but the agent must learn about the world through tools.
- Every call is written to sim.audit_log. We read it during review.
- chaos=True injects seeded, repeatable tool failures (timeouts, empty
  results). Your agent must recover. Same seed gives the same failures.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

# Risk tier for each action. "high" always needs human approval.
# "medium" needs approval only when the target service is marked critical.
ACTION_RISK = {
    "scale_service": "low",
    "flush_cache": "medium",
    "restart_service": "medium",
    "rollback_deploy": "high",
    "update_config": "high",
}


class ToolError(Exception):
    """Tool failed for a non-retryable reason (bad arguments, unknown target)."""


class ToolTimeout(Exception):
    """Transient failure. A retry may succeed."""


class ApprovalRequired(Exception):
    """Action needs a human approval string in `approved_by`."""


class IncidentSim:
    def __init__(self, scenario_path: str, seed: int = 0, chaos: bool = False):
        self.s = json.loads(Path(scenario_path).read_text())
        self.rng = random.Random(seed)
        self.chaos = chaos
        self.audit_log: list[dict] = []
        self.fixed = False
        self.config_overrides: dict[str, dict] = {}
        self.actions_taken: list[dict] = []
        self._fail_budget = dict(self.s.get("chaos_failures", {})) if chaos else {}

    # ------------------------------------------------------------------ API
    def list_tools(self) -> list[dict]:
        return [
            {"name": "list_services", "args": {}, "risk": "read"},
            {"name": "get_alert", "args": {}, "risk": "read"},
            {"name": "search_logs", "args": {"service": "str", "query": "str?", "level": "str?"}, "risk": "read"},
            {"name": "get_metrics", "args": {"service": "str", "metric": "str"}, "risk": "read"},
            {"name": "get_deploys", "args": {"service": "str?"}, "risk": "read"},
            {"name": "get_config", "args": {"service": "str"}, "risk": "read"},
            {"name": "check_health", "args": {"service": "str"}, "risk": "read"},
            {"name": "execute_action", "args": {"action": "str", "target": "str", "params": "dict?", "approved_by": "str?"}, "risk": "write"},
        ]

    def call(self, tool: str, **kw):
        entry = {"tool": tool, "args": kw, "outcome": None}
        self.audit_log.append(entry)
        try:
            self._maybe_inject_failure(tool, kw)
            fn = getattr(self, f"_t_{tool}", None)
            if fn is None:
                raise ToolError(f"unknown tool: {tool}")
            result = fn(**kw)
            entry["outcome"] = "ok"
            return result
        except (ToolError, ToolTimeout, ApprovalRequired) as exc:
            entry["outcome"] = type(exc).__name__
            raise
        except TypeError as exc:
            entry["outcome"] = "ToolError"
            raise ToolError(f"bad arguments for {tool}: {exc}") from exc

    # ------------------------------------------------------------- internals
    def _maybe_inject_failure(self, tool, kw):
        left = self._fail_budget.get(tool, 0)
        if left > 0:
            self._fail_budget[tool] = left - 1
            raise ToolTimeout(f"{tool} timed out after 10s (simulated)")

    def _svc(self, name):
        for svc in self.s["services"]:
            if svc["name"] == name:
                return svc
        raise ToolError(f"unknown service: {name}")

    def _t_list_services(self):
        return [{"name": x["name"], "tier": x["tier"], "critical": x["critical"]} for x in self.s["services"]]

    def _t_get_alert(self):
        return self.s["alert"]

    def _t_search_logs(self, service, query="", level=None):
        self._svc(service)
        rows = self.s["logs"].get("after_fix" if self.fixed else "before_fix", [])
        rows = [r for r in rows if r["service"] == service]
        if level:
            rows = [r for r in rows if r["level"].lower() == level.lower()]
        if query:
            rows = [r for r in rows if query.lower() in r["msg"].lower()]
        return rows[-40:]

    def _t_get_metrics(self, service, metric):
        self._svc(service)
        block = self.s["metrics"].get("after_fix" if self.fixed else "before_fix", {})
        series = block.get(service, {}).get(metric)
        if series is None:
            known = sorted(self.s["metrics"]["before_fix"].get(service, {}))
            raise ToolError(f"no metric '{metric}' for {service}. known: {known}")
        return {"service": service, "metric": metric, "points": series}

    def _t_get_deploys(self, service=None):
        rows = self.s["deploys"]
        if service:
            self._svc(service)
            rows = [d for d in rows if d["service"] == service]
        return rows

    def _t_get_config(self, service):
        self._svc(service)
        cfg = dict(self.s["configs"].get(service, {}))
        cfg.update(self.config_overrides.get(service, {}))
        return cfg

    def _t_check_health(self, service):
        self._svc(service)
        state = "after_fix" if self.fixed else "before_fix"
        return self.s["health"][state].get(service, {"status": "unknown"})

    def _t_execute_action(self, action, target, params=None, approved_by=None):
        params = params or {}
        if action not in ACTION_RISK:
            raise ToolError(f"unknown action: {action}")
        svc = self._svc(target)
        risk = ACTION_RISK[action]
        needs = risk == "high" or (risk == "medium" and svc["critical"])
        if needs and not approved_by:
            raise ApprovalRequired(f"{action} on {target} is {risk} risk and needs approved_by")
        record = {"action": action, "target": target, "params": params, "approved_by": approved_by, "risk": risk}
        self.actions_taken.append(record)
        if action == "update_config":
            self.config_overrides.setdefault(target, {}).update(params.get("set", {}))
        for rule in self.s["remediations"]:
            if rule["action"] == action and rule["target"] == target and self._params_match(rule, params):
                if rule.get("resolves", True):
                    self.fixed = True
                return {"status": "applied", "detail": rule["detail"]}
        side = self.s.get("wrong_action_effects", {}).get(f"{action}:{target}")
        return {"status": "applied", "detail": side or "action applied; no visible change"}

    @staticmethod
    def _params_match(rule, params):
        want = rule.get("params", {})
        return all(params.get(k) == v for k, v in want.items())
