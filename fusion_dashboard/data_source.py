"""
MQTT-backed data source for the fusion dashboard.

    get_latest() -> {
        "node_a": {"state": int, "confidence": float, "raw": dict, "timestamp": float} | None,
        "node_b": {"state": int, "confidence": float, "raw": dict, "timestamp": float} | None,
    }
"""

import json
import threading

DEFAULT_HOST = "ddns.gophernest.net"
DEFAULT_PORT = 3100
DEFAULT_TOPIC_NODE_A = "sensors/node_a/state"
DEFAULT_TOPIC_NODE_B = "sensors/node_b/state"


class DataSource:
    def get_latest(self):
        raise NotImplementedError


class MqttDataSource(DataSource):

    def __init__(
        self,
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        username="",
        password="",
        topic_node_a=DEFAULT_TOPIC_NODE_A,
        topic_node_b=DEFAULT_TOPIC_NODE_B,
        client_id="fusion_dashboard",
    ):
        import paho.mqtt.client as mqtt

        self._topic_node_a = topic_node_a
        self._topic_node_b = topic_node_b
        self._lock = threading.Lock()
        self._latest = {"node_a": None, "node_b": None}
        self.connected = False
        self.error = None

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            transport="tcp",
            protocol=mqtt.MQTTv5,
        )
        self._client.username_pw_set(username, password)
        self._client.on_connect = self._on_connect
        self._client.on_subscribe = self._on_subscribe
        self._client.on_message = self._on_message

        try:
            self._client.connect(host, port)
            self._client.loop_start()
        except Exception as e:  
            self.error = str(e)
            print(f"[MQTT] Connect failed: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        del userdata, flags, properties
        if reason_code == 0:
            self.connected = True
            print(f"[MQTT] Connected, subscribing to '{self._topic_node_a}' and '{self._topic_node_b}'")
            client.subscribe(self._topic_node_a)
            client.subscribe(self._topic_node_b)
        else:
            self.error = f"Connection failed with code: {reason_code}"
            print(f"[MQTT] {self.error}")

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        del client, userdata, properties
        print(f"[MQTT] Subscribe ack mid={mid}: {reason_code_list}")

    def _on_message(self, client, userdata, msg):
        del client, userdata
        print(f"[MQTT] Received on '{msg.topic}': {msg.payload.decode(errors='replace')}")
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[MQTT] Failed to parse payload on '{msg.topic}': {e}")
            return

        with self._lock:
            if msg.topic == self._topic_node_a:
                self._latest["node_a"] = payload
            elif msg.topic == self._topic_node_b:
                self._latest["node_b"] = payload
            else:
                print(f"[MQTT] Message on unrecognized topic '{msg.topic}', ignoring")

    def get_latest(self):
        with self._lock:
            return dict(self._latest)

    def close(self):
        self._client.loop_stop()
        self._client.disconnect()
