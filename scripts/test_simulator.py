from sim.simulator import IncidentSim

from agent.tools.simulator import SimulatorClient


def main():
    sim = IncidentSim(
        "sim/scenarios/s1_bad_deploy.json",
        seed=7,
        chaos=False,
    )

    client = SimulatorClient(sim)

    alert = client.call("get_alert")

    print("Alert:")
    print(alert)

    print("\nAvailable tools:")
    print(client.list_tools())


if __name__ == "__main__":
    main()