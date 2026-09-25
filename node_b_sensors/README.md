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
├── python/
│   ├── main.py
│   ├── classifier.py
│   ├── mqtt_publisher.py  # Publishes classification results to the broker
│   ├── .env.example       # Copy to .env and fill in the real broker credentials
│   └── requirements.txt
└── sketch/
    ├── sketch.ino
    └── sketch.yaml      # required Arduino libraries (fqbn left blank;
                          # arduino-app-cli resolves it from the board
                          # it's running on)
```

## Broker credentials

`mqtt_publisher.py` reads `MQTT_USERNAME`/`MQTT_PASSWORD` from a `.env` file
next to it (via `python-dotenv`) instead of hardcoding them. Before running
or deploying:

```
cp python/.env.example python/.env
# then fill in the real broker username/password in python/.env
```

`.env` is gitignored - it never gets committed, but `deploy.sh`/`scp` still
copies it to the board since that's a plain filesystem copy.

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
2. First deploy only, copy this folder to the board:
   ```
   scp -r node_b_sensors arduino@<BOARD_IP>:~/ArduinoApps/node_b_sensors
   ```
3. Start, watch, and stop the app:
   ```
   ssh arduino@<BOARD_IP>
   arduino-app-cli app start ~/ArduinoApps/node_b_sensors
   arduino-app-cli app logs ~/ArduinoApps/node_b_sensors
   arduino-app-cli app stop ~/ArduinoApps/node_b_sensors
   ```

### Redeploying after changes

`scp -r` into a remote directory that already exists nests the folder
inside itself (`~/ArduinoApps/node_b_sensors/node_b_sensors/...`) instead
of overwriting it, so the app keeps running stale files. Use `deploy.sh`
instead of repeating step 2 by hand - it stops the app, wipes the old
copy, re-copies, and restarts it in one go:

```
./deploy.sh <BOARD_IP>
```

Note: Python output does not print live to your SSH session when run this
way — `print()` calls go to the app's log file, so use `app logs` to see
them.


