import json
import os
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DOMAIN: str = "ddns.gophernest.net"
PORT: int = 3100
USERNAME: str = os.environ.get("MQTT_USERNAME", "")
PASSWORD: str = os.environ.get("MQTT_PASSWORD", "")
TOPIC: str = "sensors/node_b/state"
CLIENT_ID: str = "node_b_sensors"


def connect():
    def on_connect(client, userdata, flags, reason_code, properties):
        _, _, _, _ = client, userdata, flags, properties
        if reason_code == 0:
            print(f"[MQTT] Connected to {DOMAIN}:{PORT} as '{CLIENT_ID}'")
        else:
            print(f"[MQTT] Connection failed: {reason_code}")

    def on_disconnect(client, userdata, flags, reason_code, properties):
        _, _, _, _ = client, userdata, flags, properties
        print(f"[MQTT] Disconnected: {reason_code}")

    def on_publish(client, userdata, mid, reason_code, properties):
        _, _, _, _ = client, userdata, reason_code, properties
        print(f"[MQTT] Broker acknowledged message id={mid}")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        transport="tcp",
        protocol=mqtt.MQTTv5,
    )
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    client.connect(DOMAIN, PORT)
    client.loop_start()

    return client


def publish_state(client, state, confidence, raw, timestamp):
    """
    Publishes one reading in the shape fusion_dashboard/data_source.py's
    MqttDataSource expects: {state, confidence, raw, timestamp}.
    """

    payload = json.dumps(
        {
            "state": state,
            "confidence": confidence,
            "raw": raw,
            "timestamp": timestamp,
        }
    )

    if not client.is_connected():
        print(f"[MQTT] Not connected, skipping publish to '{TOPIC}': {payload}")
        return

    print(f"[MQTT] Publishing to '{TOPIC}': {payload}")
    result = client.publish(TOPIC, payload, qos=1)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"[MQTT] Publish call failed: rc={result.rc} ({mqtt.error_string(result.rc)})")
