"""
Example: Connect to RabbitMQ broker
"""

import time
import paho.mqtt.client as mqtt

DOMAIN: str = "concur.gophernest.net"
PORT: int = 443  # Default HTTPS port
PASSWORD: str = ""
USERNAME: str = ""
CLIENT: str = "python_connection_example"


def on_connect(client, userdata, flags, reason_code, properties):
    """
    Connection handler
    """
    _, _, _, _ = client, userdata, flags, properties
    if reason_code == 0:
        print("✅ Connected to RabbitMQ via WebSockets!")
    else:
        print(f"❌ Connection failed with code: {reason_code}")


# Set the transport to websockets
conn = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT,
    transport="websockets",
    protocol=mqtt.MQTTv5,
)

# Configure connection
conn.username_pw_set(USERNAME, PASSWORD)
conn.on_connect = on_connect

conn.ws_set_options(path="/ws")
conn.tls_set()
conn.connect(DOMAIN, PORT)

# Start the loop in the background so your threading logic isn't blocked
conn.loop_start()

# Simple keep alive for this example
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
    conn.loop_stop()
