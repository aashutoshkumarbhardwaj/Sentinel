from __future__ import annotations

from agent.graph.state import IncidentState
from agent.tools.executor import ToolExecutor


def execute_remediation(
    state: IncidentState,
    client,
) -> dict:

    proposed = state.get('proposed_action')

    if not proposed:
        return {
            'status': 'escalated',
        }

    approved_by = state.get(
        'approved_by'
    )

    if (
        proposed.get('risk')
        in {'high', 'critical'}
        and not approved_by
    ):
        return {
            'status': 'denied',
            'errors': [
                *state.get('errors', []),
                {
                    'tool': 'execute_action',
                    'error_type': 'ApprovalMissing',
                    'message': (
                        'Attempted remediation without approval.'
                    ),
                },
            ],
        }

    executor = ToolExecutor(client)

    try:

        result = executor.execute_approved_action(
            action=proposed['action'],
            target=proposed['target'],
            params=proposed.get('params', {}),
            approved_by=approved_by or 'system',
        )

        return {
            'action_result': {
                'success': True,
                'result': result,
            },
            'status': 'verifying',
            'timeline': [
                *state.get('timeline', []),
                {
                    'event': 'remediation_executed',
                    'action': proposed['action'],
                    'target': proposed['target'],
                },
            ],
        }

    except Exception as exc:

        return {
            'action_result': {
                'success': False,
                'error': str(exc),
            },
            'status': 'remediation_failed',
            'errors': [
                *state.get('errors', []),
                {
                    'tool': 'execute_action',
                    'error_type': type(exc).__name__,
                    'message': str(exc),
                },
            ],
        }