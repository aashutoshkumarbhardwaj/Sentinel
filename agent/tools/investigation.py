from __future__ import annotations
from agent.reliability.retry import call_with_retry
from typing import Any

from agent.tools.simulator import SimulatorClient


READ_TOOLS = {
    "list_services",
    "get_alert",
    "search_logs",
    "get_metrics",
    "get_deploys",
    "get_config",
    "check_health",
}


def call_read_tool(
    client: SimulatorClient,
    tool: str,
    **kwargs: Any,
) -> Any:
    if tool not in READ_TOOLS:
        raise ValueError(f"Tool is not a read tool: {tool}")

    return call_with_retry(
        client.call,
        tool,
        **kwargs,
    )


def get_alert(client: SimulatorClient) -> Any:
    return call_read_tool(client, "get_alert")


def list_services(client: SimulatorClient) -> Any:
    return call_read_tool(client, "list_services")


def search_logs(
    client: SimulatorClient,
    service: str | None = None,
    level: str | None = None,
    query: str | None = None,
) -> Any:
    kwargs = {}

    if service is not None:
        kwargs["service"] = service

    if level is not None:
        kwargs["level"] = level

    if query is not None:
        kwargs["query"] = query

    return call_read_tool(client, "search_logs", **kwargs)


def get_metrics(
    client: SimulatorClient,
    service: str,
    metric: str,
) -> Any:
    return call_read_tool(
        client,
        "get_metrics",
        service=service,
        metric=metric,
    )


def get_deploys(
    client: SimulatorClient,
    service: str | None = None,
) -> Any:
    kwargs = {}

    if service is not None:
        kwargs["service"] = service

    return call_read_tool(client, "get_deploys", **kwargs)


def get_config(
    client: SimulatorClient,
    service: str,
) -> Any:
    return call_read_tool(
        client,
        "get_config",
        service=service,
    )


def check_health(
    client: SimulatorClient,
    service: str,
) -> Any:
    return call_read_tool(
        client,
        "check_health",
        service=service,
    )