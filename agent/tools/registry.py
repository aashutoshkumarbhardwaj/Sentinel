from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    category: str
    risk: str
    required_args: tuple[str, ...] = ()
    optional_args: tuple[str, ...] = ()
    retryable: bool = True
    read_only: bool = True


TOOL_SPECS: dict[str, ToolSpec] = {
    'get_alert': ToolSpec(
        name='get_alert',
        description='Retrieve the active incident alert.',
        category='investigation',
        risk='low',
    ),

    'list_services': ToolSpec(
        name='list_services',
        description='List services available in the environment.',
        category='investigation',
        risk='low',
    ),

    'search_logs': ToolSpec(
        name='search_logs',
        description='Search service logs for errors and relevant events.',
        category='investigation',
        risk='low',
        required_args=('service',),
        optional_args=('level',),
    ),

    'get_metrics': ToolSpec(
        name='get_metrics',
        description='Retrieve service metrics.',
        category='investigation',
        risk='low',
        required_args=('service',),
        optional_args=('metric',),
    ),

    'get_deploys': ToolSpec(
        name='get_deploys',
        description='Retrieve recent deployments for a service.',
        category='investigation',
        risk='low',
        required_args=('service',),
    ),

    'get_config': ToolSpec(
        name='get_config',
        description='Retrieve configuration for a service.',
        category='investigation',
        risk='low',
        required_args=('service',),
    ),

    'check_health': ToolSpec(
        name='check_health',
        description='Check current service health.',
        category='verification',
        risk='low',
        required_args=('service',),
    ),

    'execute_action': ToolSpec(
        name='execute_action',
        description='Execute a production remediation action.',
        category='remediation',
        risk='high',
        required_args=('action', 'target'),
        optional_args=('params', 'approved_by'),
        retryable=False,
        read_only=False,
    ),
}


class ToolValidationError(Exception):
    pass


class ToolRegistry:

    def __init__(
        self,
        specs: dict[str, ToolSpec] | None = None,
    ):
        self.specs = specs or TOOL_SPECS

    def get(self, name: str) -> ToolSpec:
        try:
            return self.specs[name]
        except KeyError as exc:
            raise ToolValidationError(
                f'Unknown tool: {name}'
            ) from exc

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                'name': spec.name,
                'description': spec.description,
                'category': spec.category,
                'risk': spec.risk,
                'required_args': list(spec.required_args),
                'optional_args': list(spec.optional_args),
                'read_only': spec.read_only,
            }
            for spec in self.specs.values()
        ]

    def validate(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> ToolSpec:

        spec = self.get(name)

        missing = [
            arg
            for arg in spec.required_args
            if arg not in arguments
        ]

        if missing:
            raise ToolValidationError(
                f'Missing required arguments for {name}: {missing}'
            )

        allowed = set(spec.required_args) | set(
            spec.optional_args
        )

        unexpected = set(arguments) - allowed

        if unexpected:
            raise ToolValidationError(
                f'Unexpected arguments for {name}: {unexpected}'
            )

        return spec

    def is_write(self, name: str) -> bool:
        return not self.get(name).read_only

    def risk(self, name: str) -> str:
        return self.get(name).risk