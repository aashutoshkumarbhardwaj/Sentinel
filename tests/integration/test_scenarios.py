import pytest
from sim.simulator import IncidentSim
from agent.main import run_incident


def test_scenario_s3_approved():
    sim = IncidentSim("sim/scenarios/s3_cert_expiry.json", seed=7, chaos=True)
    result = run_incident(sim, thread_id="test-s3-approved", approver=lambda req: "test_approver")

    assert result["status"] == "resolved"
    assert result["confidence"] == 0.95
    assert sim.fixed is True
    assert "certificate" in result["root_cause"].lower()
    assert len(result["actions"]) == 1
    assert result["actions"][0]["target"] == "auth-service"


def test_scenario_s3_denied():
    sim = IncidentSim("sim/scenarios/s3_cert_expiry.json", seed=7, chaos=True)
    result = run_incident(sim, thread_id="test-s3-denied", approver=lambda req: None)

    assert result["status"] == "denied"
    assert sim.fixed is False
    assert len(sim.actions_taken) == 0


def test_scenario_s1_bad_deploy():
    sim = IncidentSim("sim/scenarios/s1_bad_deploy.json", seed=7, chaos=False)
    result = run_incident(sim, thread_id="test-s1", approver=lambda req: "test_approver")

    assert result["status"] == "resolved"
    assert sim.fixed is True


def test_scenario_s2_db_saturation():
    sim = IncidentSim("sim/scenarios/s2_db_saturation.json", seed=7, chaos=False)
    result = run_incident(sim, thread_id="test-s2", approver=lambda req: "test_approver")

    assert result["status"] == "resolved"
    assert sim.fixed is True
