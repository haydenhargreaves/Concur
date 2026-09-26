import time
import json

from arduino.app_utils import App, Bridge

from classifier import classify_node_b
from rabbit import connect, send

READ_INTERVAL = 0.5
TOPIC = "sensors/node_b/state"

mqtt_client = connect("node_b_sensors")

# =====================================================
# Read sensors from Arduino MCU
# =====================================================

def read_sensor_data():

    try:
        raw_data = Bridge.call("read_sensors")
        data = json.loads(raw_data)
        return data

    except Exception as e:
        print(f"[ERROR] Bridge communication failed: {e}")
        return None


# =====================================================
# Print sensor data
# =====================================================

def print_sensor_data(data):

    if data is None:
        return

    print("----------------------------------------")

    print("RAW SENSOR DATA")

    # Distance
    print(
        f"Distance : {data['distance_mm']:7.1f} mm"
    )

    # Accelerometer
    print(
        f"Accel    : "
        f"X={data['accel_x']:6.3f}  "
        f"Y={data['accel_y']:6.3f}  "
        f"Z={data['accel_z']:6.3f}"
    )

    # Gyroscope
    print(
        f"Gyro     : "
        f"X={data['gyro_x']:6.3f}  "
        f"Y={data['gyro_y']:6.3f}  "
        f"Z={data['gyro_z']:6.3f}"
    )

    # Light
    print(
        f"Light    : "
        f"{data['light_lux']:6d} lux"
    )

    # Raw light
    print(
        f"Light raw: "
        f"{data['light_raw']:6d}"
    )

    # IR
    print(
        f"Light IR : "
        f"{data['light_ir']:6d}"
    )

    # Sensor status
    print(
        f"Status   : "
        f"Distance={data['distance_ok']} | "
        f"Movement={data['movement_ok']} | "
        f"Light={data['light_ok']}"
    )


# =====================================================
# Main Loop
# =====================================================

def loop():

    while True:

        # ---------------------------------------------
        # 1. Read sensors
        # ---------------------------------------------

        data = read_sensor_data()

        if data is None:
            time.sleep(READ_INTERVAL)
            continue

        # ---------------------------------------------
        # 2. Print raw sensor data
        # ---------------------------------------------

        print_sensor_data(data)

        # ---------------------------------------------
        # 3. Local classification
        # ---------------------------------------------

        state, confidence = classify_node_b(data)

        # ---------------------------------------------
        # 4. Print classification result
        # ---------------------------------------------

        print()
        print("LOCAL CLASSIFICATION")

        print(f"State      : {state}")
        print(f"Confidence : {confidence:.2f}")

        print("----------------------------------------")

        # ---------------------------------------------
        # 5. Publish to MQTT for the fusion dashboard
        # ---------------------------------------------

        payload = json.dumps(
            {
                "state": state,
                "confidence": confidence,
                "raw": data,
                "timestamp": time.time(),
            }
        )
        send(mqtt_client, TOPIC, payload)

        time.sleep(READ_INTERVAL)


# =====================================================
# Start App
# =====================================================

App.run(user_loop=loop)