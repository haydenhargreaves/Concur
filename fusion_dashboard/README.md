# Fusion Dashboard

Streamlit dashboard that combines Node A and Node B's classifications into
one fused reading, over live MQTT data from the broker.

## Running it

```
pip install -r requirements.txt
python -m streamlit run fusion_dashboard/app.py
```

In the sidebar, fill in the broker host, port, credentials, and the two
topic names, then click **Connect**. Node B publishes to `sensors/node_b/state`
via the shared `lib/rabbit.py` (see `node_b_sensors/python/main.py`).

Node A publishes this JSON packet shape. Node B should publish the same
top-level fields so the dashboard can display both nodes consistently:

```json
{
  "version": 1,
  "node": "node_a",
  "state": 0,
  "direction": 2,
  "confidence": 0.92,
  "timestamp": 1732000000,
  "health": "HEALTHY"
}
```

where `state` is `0` (Idle) / `1` (Active Presence) / `2` (Abnormal
Disturbance). Node A uses `direction` values `0` (Approaching), `1` (Moving
away), and `2` (N/A); Node B may use a direction value appropriate to its
classifier.

`fusion.py` only requires `state` and `confidence`. If Node B needs a
different transport payload temporarily, translate it in
`MqttDataSource._on_message` in `data_source.py`.


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
