"""
Library used to connect and communication with the queue backend
"""

import time
from datetime import datetime
from json import dumps
import paho.mqtt.client as mqtt

DOMAIN: str = "ddns.gophernest.net"
PORT: int = 3100
PASSWORD: str = ""
USERNAME: str = ""


def connect(client: str):
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"Failed to connect to queue: {reason_code}")

    conn = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client,
        transport="tcp",
        protocol=mqtt.MQTTv5,
    )
    conn.username_pw_set(USERNAME, PASSWORD)
    conn.on_connect = on_connect

    conn.connect(DOMAIN, PORT)
    conn.loop_start()

    return conn


def send(conn: mqtt.Client, topic: str, payload: str):
    if not conn.is_connected():
        print("Failed to send message. Connection is not connected.")
        return

    result = conn.publish(topic, payload, qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Payload sent: {payload}")


def close(conn: mqtt.Client):
    if conn.is_connected():
        conn.loop_stop()
