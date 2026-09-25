"""
Library used to connect and communication with the queue backend
"""

import os
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DOMAIN: str = "ddns.gophernest.net"
PORT: int = 3100
USERNAME: str = os.environ.get("MQTT_USERNAME", "")
PASSWORD: str = os.environ.get("MQTT_PASSWORD", "")


def connect(client: str):
    def on_connect(client, userdata, flags, reason_code, properties):
        _, _, _, _ = client, userdata, flags, properties
        if reason_code == 0:
            print(f"[MQTT] Connected to {DOMAIN}:{PORT} as '{client_id}'")
        else:
            print(f"[MQTT] Connection failed: {reason_code}")

    def on_disconnect(client, userdata, flags, reason_code, properties):
        _, _, _, _ = client, userdata, flags, properties
        print(f"[MQTT] Disconnected: {reason_code}")

    def on_publish(client, userdata, mid, reason_code, properties):
        _, _, _, _ = client, userdata, reason_code, properties
        print(f"[MQTT] Broker acknowledged message id={mid}")

    client_id = client
    conn = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        transport="tcp",
        protocol=mqtt.MQTTv5,
    )
    conn.username_pw_set(USERNAME, PASSWORD)
    conn.on_connect = on_connect
    conn.on_disconnect = on_disconnect
    conn.on_publish = on_publish

    conn.connect(DOMAIN, PORT)
    conn.loop_start()

    return conn


def send(conn: mqtt.Client, topic: str, payload: str):
    if not conn.is_connected():
        print(f"[MQTT] Not connected, skipping publish to '{topic}': {payload}")
        return

    print(f"[MQTT] Publishing to '{topic}': {payload}")
    result = conn.publish(topic, payload, qos=1)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"[MQTT] Publish call failed: rc={result.rc} ({mqtt.error_string(result.rc)})")


def close(conn: mqtt.Client):
    if conn.is_connected():
        conn.loop_stop()
