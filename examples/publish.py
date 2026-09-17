"""
Example: Connect to RabbitMQ broker and publish messages
"""

import time
from datetime import datetime
from json import dumps
import paho.mqtt.client as mqtt

DOMAIN: str = "ddns.gophernest.net"
PORT: int = 3100
PASSWORD: str = ""
USERNAME: str = ""
CLIENT: str = "python_connection_example"
TOPIC: str = "examples/publish"


def on_connect(client, userdata, flags, reason_code, properties):
    """
    Connection handler
    """
    _, _, _, _ = client, userdata, flags, properties
    if reason_code == 0:
        print("✅ Connected to RabbitMQ via TCP!")
    else:
        print(f"❌ Connection failed with code: {reason_code}")


# Set the transport to websockets
conn = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT,
    transport="tcp",
    protocol=mqtt.MQTTv5,
)

# Configure connection
conn.username_pw_set(USERNAME, PASSWORD)
conn.on_connect = on_connect

conn.connect(DOMAIN, PORT)

# Start the loop in the background so your threading logic isn't blocked
conn.loop_start()

# Simple keep alive for this example
try:
    while True:
        if conn.is_connected():
            data = {
                "client_id": CLIENT,
                "message": f"The current time is {datetime.now()}",
            }
            payload = dumps(data)

            # Send the message
            result = conn.publish(TOPIC, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Published payload: {payload}")

        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
    conn.loop_stop()
