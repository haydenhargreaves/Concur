"""
Evaluation logger: records a labeled trial from the live broker, then scores it.

Record a trial (press a key whenever the TRUE situation changes, q to finish):
    python examples/evaluate.py run walk_up
    python examples/evaluate.py run walk_up --ignore a    # pretend node A is down
    python examples/evaluate.py run walk_up --ignore b    # pretend node B is down

Keys:  0 = idle   1 = active presence   2 = abnormal disturbance   q = finish

Score trials (default: every CSV in eval_results/):
    python examples/evaluate.py summarize
    python examples/evaluate.py summarize eval_results/walk_up_*.csv

Accuracy counts a node as wrong while it is down or faulted. Latency is measured
from your keypress until the fused state matches it, so it includes your own
reaction time.
"""

import argparse
import csv
import glob
import json
import statistics
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "fusion_dashboard"))

import paho.mqtt.client as mqtt  # noqa: E402
from fusion import fuse  # noqa: E402
from rabbit import DOMAIN, PASSWORD, PORT, USERNAME  # noqa: E402

TOPICS = {"a": "sensors/node_a/state", "b": "sensors/node_b/state"}
RESULTS_DIR = ROOT / "eval_results"
# Keep in sync with fusion_dashboard/app.py.
STALE_AFTER_SECONDS = 5
KEY_TO_STATE = {"0": 0, "1": 1, "2": 2}
STATE_NAMES = {0: "idle", 1: "active", 2: "abnormal"}
FIELDS = ["t", "truth", "node_a", "node_b", "fused", "a_health", "b_health", "a_bytes", "b_bytes"]


def live_reading(reading, now, ignored):
    """Same rule as the dashboard: stale or non-HEALTHY nodes do not count."""
    if ignored or reading is None:
        return None
    if now - reading["received_at"] > STALE_AFTER_SECONDS:
        return None
    if reading.get("health", "HEALTHY") != "HEALTHY":
        return None
    return reading


def read_keys(on_key):
    """Call on_key(char) for every keypress, forever (run in a daemon thread)."""
    try:
        import msvcrt

        while True:
            on_key(msvcrt.getwch())
    except ImportError:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                on_key(sys.stdin.read(1))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def run_trial(name, ignore, interval):
    latest = {"a": None, "b": None}
    byte_count = {"a": 0, "b": 0}
    lock = threading.Lock()
    topic_to_node = {topic: node for node, topic in TOPICS.items()}

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="evaluator",
        transport="tcp",
        protocol=mqtt.MQTTv5,
    )
    client.username_pw_set(USERNAME, PASSWORD)

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            for topic in TOPICS.values():
                c.subscribe(topic)
        else:
            print(f"[MQTT] Connection failed: {reason_code}")

    def on_message(c, userdata, msg):
        node = topic_to_node.get(msg.topic)
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        payload["received_at"] = time.time()
        with lock:
            latest[node] = payload
            byte_count[node] += len(msg.payload)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(DOMAIN, PORT)
    client.loop_start()

    truth = {"value": None}
    stop = threading.Event()

    def on_key(ch):
        if ch.lower() == "q":
            stop.set()
        elif ch in KEY_TO_STATE:
            truth["value"] = KEY_TO_STATE[ch]
            print(f"\n  truth -> {STATE_NAMES[truth['value']]}", flush=True)

    threading.Thread(target=read_keys, args=(on_key,), daemon=True).start()

    RESULTS_DIR.mkdir(exist_ok=True)
    suffix = f"_no-{ignore}" if ignore else ""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"{name}{suffix}_{stamp}.csv"

    print(f"Recording '{name}' to {path}")
    print("Keys: 0=idle  1=active  2=abnormal  q=finish. Nothing is scored until you press a state key.")

    start = time.time()
    try:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            while not stop.is_set():
                now = time.time()
                with lock:
                    a, b = latest["a"], latest["b"]
                    a_bytes, b_bytes = byte_count["a"], byte_count["b"]
                la = live_reading(a, now, ignore == "a")
                lb = live_reading(b, now, ignore == "b")
                fused = fuse(la, lb)["state"]
                row = {
                    "t": round(now - start, 3),
                    "truth": "" if truth["value"] is None else truth["value"],
                    "node_a": "" if la is None else la["state"],
                    "node_b": "" if lb is None else lb["state"],
                    "fused": "" if fused is None else fused,
                    "a_health": "" if a is None else a.get("health", ""),
                    "b_health": "" if b is None else b.get("health", ""),
                    "a_bytes": a_bytes,
                    "b_bytes": b_bytes,
                }
                writer.writerow(row)
                f.flush()
                print(
                    f"\r  t={row['t']:7.1f}s  truth={row['truth']!s:>1}  "
                    f"A={row['node_a']!s:>1}  B={row['node_b']!s:>1}  fused={row['fused']!s:>1}   ",
                    end="",
                    flush=True,
                )
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()

    print(f"\nSaved {path}")


def load_rows(path):
    def num(value):
        return None if value == "" else int(value)

    with open(path, newline="") as f:
        return [
            {
                "t": float(r["t"]),
                "truth": num(r["truth"]),
                "node_a": num(r["node_a"]),
                "node_b": num(r["node_b"]),
                "fused": num(r["fused"]),
                "bytes": int(r["a_bytes"]) + int(r["b_bytes"]),
            }
            for r in csv.DictReader(f)
        ]


def score(rows):
    counts = {
        "n": 0, "a_ok": 0, "b_ok": 0, "f_ok": 0,
        "dis": 0, "dis_a": 0, "dis_b": 0, "dis_f": 0,
        "bytes": rows[-1]["bytes"] if rows else 0,
        "duration": rows[-1]["t"] if rows else 0.0,
        "latencies": [],
    }
    for r in rows:
        truth = r["truth"]
        if truth is None:
            continue
        counts["n"] += 1
        counts["a_ok"] += r["node_a"] == truth
        counts["b_ok"] += r["node_b"] == truth
        counts["f_ok"] += r["fused"] == truth
        if r["node_a"] is not None and r["node_b"] is not None and r["node_a"] != r["node_b"]:
            counts["dis"] += 1
            counts["dis_a"] += r["node_a"] == truth
            counts["dis_b"] += r["node_b"] == truth
            counts["dis_f"] += r["fused"] == truth

    changes = [
        i for i, r in enumerate(rows)
        if r["truth"] is not None and (i == 0 or rows[i - 1]["truth"] != r["truth"])
    ]
    for pos, i in enumerate(changes):
        end = changes[pos + 1] if pos + 1 < len(changes) else len(rows)
        for j in range(i, end):
            if rows[j]["fused"] == rows[i]["truth"]:
                counts["latencies"].append(rows[j]["t"] - rows[i]["t"])
                break
    return counts


def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "n/a"


def table_row(label, c):
    median_latency = f"{statistics.median(c['latencies']):.1f}s" if c["latencies"] else "n/a"
    rate = f"{c['bytes'] / c['duration']:.0f} B/s" if c["duration"] else "n/a"
    return (
        f"| {label} | {c['n']} | {pct(c['a_ok'], c['n'])} | {pct(c['b_ok'], c['n'])} | "
        f"{pct(c['f_ok'], c['n'])} | {c['dis']} | "
        f"{c['dis_f']} / {c['dis']} | {c['dis_a']} / {c['dis_b']} | {rate} | {median_latency} |"
    )


def summarize(paths):
    files = sorted(Path(p) for p in (paths or glob.glob(str(RESULTS_DIR / "*.csv"))))
    if not files:
        print("No trial CSVs found. Record one with: python examples/evaluate.py run <name>")
        return

    lines = [
        "| Trial | Labeled samples | Node A only | Node B only | Fused | Disagreements | "
        "Fused right | A right / B right | Bandwidth | Median latency |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    total = {
        "n": 0, "a_ok": 0, "b_ok": 0, "f_ok": 0, "dis": 0, "dis_a": 0, "dis_b": 0,
        "dis_f": 0, "bytes": 0, "duration": 0.0, "latencies": [],
    }
    for path in files:
        c = score(load_rows(path))
        lines.append(table_row(path.stem, c))
        for key in total:
            if key == "latencies":
                total[key].extend(c[key])
            else:
                total[key] += c[key]
    if len(files) > 1:
        lines.append(table_row("**All**", total))

    output = "\n".join(lines)
    print(output)
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "summary.md").write_text(output + "\n")
    print(f"\nSaved {RESULTS_DIR / 'summary.md'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="record a labeled trial")
    run.add_argument("name")
    run.add_argument("--ignore", choices=["a", "b"], help="treat this node as down")
    run.add_argument("--interval", type=float, default=0.25, help="sampling period in seconds")

    summ = sub.add_parser("summarize", help="score recorded trials")
    summ.add_argument("files", nargs="*")

    args = parser.parse_args()
    if args.command == "run":
        run_trial(args.name, args.ignore, args.interval)
    else:
        summarize(args.files)


if __name__ == "__main__":
    main()
