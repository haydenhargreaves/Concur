# Node B Sensors

Reads the Modulino distance/movement/light sensors on the Arduino UNO Q's
microcontroller side and runs local classification on the Linux side. See
`python/main.py`, `python/classifier.py`, and `sketch/sketch.ino`.

This app runs through `arduino-app-cli` instead of the Arduino App Lab GUI.

## One-time board setup

App Lab (or the equivalent `arduino-cli`/`arduino-app-cli` setup flow) is
still needed once, to:
- flash the UNO Q system firmware,
- configure Wi-Fi, and
- enable SSH access.

After that, the App Lab GUI is optional for day-to-day development.

## Layout

```
node_b_sensors/
├── app.yaml            # App Lab/CLI app manifest (Linux side)
├── deploy.sh           # Deploys/redeploys to the board (see below)
├── python/
│   ├── main.py
│   ├── classifier.py
│   └── requirements.txt
└── sketch/
    ├── sketch.ino
    └── sketch.yaml      # required Arduino libraries (fqbn left blank;
                          # arduino-app-cli resolves it from the board
                          # it's running on)
```

`main.py` publishes over MQTT via `lib/rabbit.py` (shared with `node_a_cam` -
see the repo root `lib/`), which `deploy.sh` copies onto the board alongside
this folder.

## Broker credentials

`lib/rabbit.py` reads `MQTT_USERNAME`/`MQTT_PASSWORD` from `lib/.env` (via
`python-dotenv`) instead of hardcoding them. Before running or deploying
either node:

```
cp lib/.env.example lib/.env
# then fill in the real broker username/password in lib/.env
```

`lib/.env` is gitignored - it never gets committed, but `deploy.sh`/`scp`
still copies it onto the board since that's a plain filesystem copy.

## Publishing to the fusion dashboard

`main.py` publishes each classification result to the `sensors/node_b/state`
MQTT topic, in the shape `fusion_dashboard` expects:

```json
{ "state": 0, "confidence": 0.9, "raw": { "...": "sensor fields" }, "timestamp": 1732000000.0 }
```

To see it in the dashboard, run `python -m streamlit run fusion_dashboard/app.py`,
fill in the same broker host/credentials/topic in the sidebar, and click
**Connect** while this app is running on the board.

## Deploying and running from VS Code / CLI

1. Find the board's IP (via `ip addr show` over an initial SSH/serial
   session, or the App Lab connection screen).
2. Deploy (works for both the first deploy and any later redeploy):
   ```
   ./deploy.sh <BOARD_IP>
   ```
   Plain `scp -r` into a remote directory that already exists nests the
   source folder inside itself instead of overwriting it, so a second
   manual `scp` would leave the app running stale files - `deploy.sh` stops
   the app, wipes any old copy, copies this folder plus the shared `lib/`
   (flattened into `python/`, same as `scripts/node_a/deploy.sh`), and
   restarts it.
3. Watch or stop the app:
   ```
   ssh arduino@<BOARD_IP>
   arduino-app-cli app logs ~/ArduinoApps/node_b_sensors
   arduino-app-cli app stop ~/ArduinoApps/node_b_sensors
   ```

Note: Python output does not print live to your SSH session when run this
way — `print()` calls go to the app's log file, so use `app logs` to see
them.
