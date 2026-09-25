# Fusion Dashboard

Streamlit dashboard that combines Node A and Node B's classifications into
one fused reading, over live MQTT data from the broker.

## Running it

```
pip install -r requirements.txt
python -m streamlit run fusion_dashboard/app.py
```

In the sidebar, fill in the broker host, port, credentials, and the two
topic names, then click **Connect**. Node B publishes to `sensors/node_b/state` (see
`node_b_sensors/python/mqtt_publisher.py`)

Each node's published JSON payload is expected to look like:

```json
{
  "state": 0,
  "confidence": 0.92,
  "raw": { "...": "whatever sensor fields the node reports" },
  "timestamp": 1732000000.0
}
```

where `state` is `0` (Idle) / `1` (Active Presence) / `2` (Abnormal
Disturbance) 

If the real payloads end up shaped differently, translate them in
`MqttDataSource._on_message` in `data_source.py` rather than changing
`app.py` or `fusion.py` - both only depend on the dict shape above.


## Layout

```
fusion_dashboard/
├── app.py             # Streamlit UI: panels, fused view, history chart, sidebar
├── data_source.py     # MqttDataSource - subscribes to both nodes' topics
├── fusion.py           # Placeholder fusion rule: agree -> average, disagree -> escalate
├── states.py           # Display labels for the state ids (ids come from node_b_bridge)
├── node_b_bridge.py     # Imports the real state ids + classify_node_b from
│                        # ../node_b_sensors/python/classifier.py - single
│                        # source of truth, not redefined here
└── requirements.txt
```

<!-- ## Fusion logic

`fusion.fuse()` is intentionally simple as a placeholder: if both nodes
report the same state, it averages their confidence; if they disagree, it
escalates to whichever node reports the more severe state. Swap this out for
whatever fusion rule the project actually wants - the rest of the dashboard
only depends on `fuse()`'s return shape (`state`, `confidence`, `agree`,
`note`). -->
