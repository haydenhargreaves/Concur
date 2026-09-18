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
│   └── requirements.txt
└── sketch/
    ├── sketch.ino
    └── sketch.yaml      # required Arduino libraries (fqbn left blank;
                          # arduino-app-cli resolves it from the board
                          # it's running on)
```

## Deploying and running from VS Code / CLI

1. Find the board's IP (via `ip addr show` over an initial SSH/serial
   session, or the App Lab connection screen).
2. Copy this folder to the board:
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

Note: Python output does not print live to your SSH session when run this
way — `print()` calls go to the app's log file, so use `app logs` to see
them.


