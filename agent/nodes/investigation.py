from __future__ import annotations

from typing import Any

from agent.graph.state import IncidentState
from agent.llm import get_decision_engine
from agent.tools.executor import ToolExecutor


MAX_INVESTIGATION_ROUNDS = 8


def _evidence_id(
    tool: str,
    index: int,
) -> str:
    return f'{tool}:{index}'


def _append_evidence(
    state: IncidentState,
    tool: str,
    data: Any,
) -> list[dict[str, Any]]:

    evidence = list(state.get('evidence', []))

    evidence.append(
        {
            'id': _evidence_id(
                tool,
                len(evidence),
            ),
            'source': tool,
            'data': data,
            'supports': [],
            'contradicts': [],
        }
    )

    return evidence


def _extract_services(
    state: IncidentState,
) -> list[str]:

    services: set[str] = set()

    alert = state.get('alert') or {}

    for key in (
        'service',
        'affected_service',
        'source_service',
    ):
        value = alert.get(key)

        if isinstance(value, str):
            services.add(value)

    for evidence in state.get('evidence', []):

        data = evidence.get('data')

        if not isinstance(data, dict):
            continue

        for key in (
            'service',
            'affected_service',
            'source_service',
        ):
            value = data.get(key)

            if isinstance(value, str):
                services.add(value)

    return sorted(services)


def _prepare_arguments(
    tool: str,
    arguments: dict[str, Any],
    state: IncidentState,
) -> dict[str, Any]:

    args = dict(arguments)

    if tool in {
        'search_logs',
        'get_metrics',
        'get_deploys',
        'get_config',
        'check_health',
    } and 'service' not in args:

        services = _extract_services(state)

        if len(services) == 1:
            args['service'] = services[0]

    return args


def investigate_node(
    state: IncidentState,
    client,
) -> dict[str, Any]:

    executor = ToolExecutor(client)
    engine = get_decision_engine()

    round_number = (
        state.get('investigation_round', 0) + 1
    )

    if round_number > MAX_INVESTIGATION_ROUNDS:

        return {
            'status': 'escalated',
            'investigation_complete': True,
            'last_decision': {
                'phase': 'escalate',
                'reasoning': (
                    'Investigation round limit reached '
                    'without sufficient confidence.'
                ),
            },
        }

    available_tools = executor.available_tools()

    decision = engine.investigate(
        state=dict(state),
        available_tools=available_tools,
    )

    evidence = list(
        state.get('evidence', [])
    )

    errors = list(
        state.get('errors', [])
    )

    timeline = list(
        state.get('timeline', [])
    )

    executed_tools = 0

    for request in decision.tool_requests:

        tool = request.tool

        try:

            arguments = _prepare_arguments(
                tool,
                request.arguments,
                state,
            )

            result = executor.execute(
                tool,
                arguments,
            )

            evidence = _append_evidence(
                {
                    **state,
                    'evidence': evidence,
                },
                tool,
                result,
            )

            executed_tools += 1

            timeline.append(
                {
                    'event': 'tool_success',
                    'tool': tool,
                    'round': round_number,
                    'reason': request.reason,
                }
            )

        except Exception as exc:

            errors.append(
                {
                    'tool': tool,
                    'error_type': type(exc).__name__,
                    'message': str(exc),
                    'round': round_number,
                }
            )

            timeline.append(
                {
                    'event': 'tool_failure',
                    'tool': tool,
                    'round': round_number,
                    'error': str(exc),
                }
            )

    hypothesis_updates = (
        decision.hypothesis_updates
    )

    hypotheses = list(
        state.get('hypotheses', [])
    )

    hypothesis_map = {
        item.get('id'): dict(item)
        for item in hypotheses
        if item.get('id')
    }

    for update in hypothesis_updates:

        hypothesis = hypothesis_map.get(
            update.hypothesis_id,
            {
                'id': update.hypothesis_id,
                'description': update.hypothesis_id,
            },
        )

        hypothesis['confidence'] = (
            update.confidence
        )

        hypothesis['supporting_evidence'] = (
            update.supporting_evidence
        )

        hypothesis['contradicting_evidence'] = (
            update.contradicting_evidence
        )

        hypothesis_map[
            update.hypothesis_id
        ] = hypothesis

        timeline.append(
            {
                'event': 'hypothesis_update',
                'hypothesis': update.hypothesis_id,
                'confidence': update.confidence,
                'reason': (
                    update.confidence_change_reason
                ),
                'supporting_evidence': (
                    update.supporting_evidence
                ),
                'contradicting_evidence': (
                    update.contradicting_evidence
                ),
                'round': round_number,
            }
        )

    hypotheses = list(
        hypothesis_map.values()
    )

    return {
        'evidence': evidence,
        'hypotheses': hypotheses,
        'selected_hypothesis': (
            decision.selected_hypothesis
        ),
        'investigation_round': round_number,
        'investigation_complete': (
            decision.investigation_complete
        ),
        'last_decision': decision.model_dump(),
        'errors': errors,
        'timeline': timeline,
        'status': (
            'investigating'
            if not decision.investigation_complete
            else (
                'root_cause_identified'
                if decision.selected_hypothesis
                else 'escalated'
            )
        ),
    }