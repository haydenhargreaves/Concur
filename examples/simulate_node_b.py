"""
Simulate node B by publishing packets to sensors/node_b/state.

Usage (from repo root):
    python examples/simulate_node_b.py cycle
    python examples/simulate_node_b.py abnormal --interval 1
    python examples/simulate_node_b.py fault

Scenarios:
    idle         steady idle
    active       steady active presence
    approaching  active presence, approaching
    moving_away  active presence, moving away
    abnormal     steady abnormal disturbance
    cycle        rotate through all states every --cycle-seconds
    fault        publish health=SENSOR_FAULT (dashboard should show a fault)
    silent       connect but publish nothing (dashboard should show OFFLINE)
"""

import argparse
import random
import sys
import time
from json import dumps
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from rabbit import close, connect, send  # noqa: E402

TOPIC = "sensors/node_b/state"
CLIENT_ID = "node_b_simulator"  # distinct from the real node's "node_b_sensors"

IDLE, ACTIVE, ABNORMAL = 0, 1, 2
APPROACHING, MOVING_AWAY, NO_DIRECTION = 0, 1, 2

SCENARIOS = {
    "idle": (IDLE, NO_DIRECTION),
    "active": (ACTIVE, NO_DIRECTION),
    "approaching": (ACTIVE, APPROACHING),
    "moving_away": (ACTIVE, MOVING_AWAY),
    "abnormal": (ABNORMAL, NO_DIRECTION),
}
CYCLE = ["idle", "approaching", "moving_away", "abnormal"]


def build_packet(state: int, direction: int, health: str = "HEALTHY") -> dict:
    confidence = 0.0 if health != "HEALTHY" else round(random.uniform(0.70, 0.98), 2)
    return {
        "version": 1,
        "node": "node_b",
        "timestamp": int(time.time()),
        "state": state,
        "direction": direction,
        "confidence": confidence,
        "health": health,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("scenario", choices=[*SCENARIOS, "cycle", "fault", "silent"])
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between packets")
    parser.add_argument("--cycle-seconds", type=float, default=5.0)
    args = parser.parse_args()

    conn = connect(CLIENT_ID)
    start = time.monotonic()
    try:
        while True:
            if args.scenario == "silent":
                pass
            elif args.scenario == "fault":
                send(conn, TOPIC, dumps(build_packet(IDLE, NO_DIRECTION, "SENSOR_FAULT")))
            else:
                name = args.scenario
                if name == "cycle":
                    step = int((time.monotonic() - start) // args.cycle_seconds)
                    name = CYCLE[step % len(CYCLE)]
                state, direction = SCENARIOS[name]
                send(conn, TOPIC, dumps(build_packet(state, direction)))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        close(conn)


if __name__ == "__main__":
    main()
