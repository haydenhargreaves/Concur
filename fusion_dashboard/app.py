
import time
import pandas as pd
import streamlit as st
from data_source import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_TOPIC_NODE_A,
    DEFAULT_TOPIC_NODE_B,
    MqttDataSource,
)
from fusion import fuse
from states import STATE_ABNORMAL_DISTURBANCE, STATE_ACTIVE_PRESENCE, STATE_IDLE, STATE_LABELS

HISTORY_LIMIT = 100

st.set_page_config(page_title="Concur - Sensor Fusion Dashboard", layout="wide")

if "history" not in st.session_state:
    st.session_state.history = []
if "events" not in st.session_state:
    st.session_state.events = []
if "last_fused_state" not in st.session_state:
    st.session_state.last_fused_state = None
if "mqtt_source" not in st.session_state:
    st.session_state.mqtt_source = None


def render_state_badge(container, state):
    label = STATE_LABELS[state]
    if state == STATE_IDLE:
        container.success(label, icon="✅")
    elif state == STATE_ACTIVE_PRESENCE:
        container.warning(label, icon="⚠️")
    elif state == STATE_ABNORMAL_DISTURBANCE:
        container.error(label, icon="\U0001f6a8")


def render_node_panel(container, title, reading_):
    container.subheader(title)
    if reading_ is None:
        container.info("No data yet.")
        return

    render_state_badge(container, reading_["state"])
    container.metric("Confidence", f"{reading_['confidence']:.0%}")
    container.progress(reading_["confidence"])

    with container.expander("Raw sensor data"):
        st.json(reading_["raw"])

    container.caption(
        f"Last updated: {time.strftime('%H:%M:%S', time.localtime(reading_['timestamp']))}"
    )


def render_dashboard_body(source):
    # -------------------------------------------------------------------
    # Pull the latest reading
    # -------------------------------------------------------------------

    reading = source.get_latest() if source is not None else {"node_a": None, "node_b": None}
    node_a, node_b = reading.get("node_a"), reading.get("node_b")
    fused = fuse(node_a, node_b)

    now = time.time()
    st.session_state.history.append(
        {
            "time": pd.to_datetime(now, unit="s"),
            "Node A": node_a["confidence"] if node_a else None,
            "Node B": node_b["confidence"] if node_b else None,
            "Fused": fused["confidence"],
        }
    )
    st.session_state.history = st.session_state.history[-HISTORY_LIMIT:]

    if fused["state"] is not None and fused["state"] != st.session_state.last_fused_state:
        st.session_state.events.append(
            {
                "time 23": pd.to_datetime(now, unit="s").strftime("%H:%M:%S"),
                "Fused state": STATE_LABELS[fused["state"]],
            }
        )
        st.session_state.events = st.session_state.events[-20:]
    st.session_state.last_fused_state = fused["state"]

    # -------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------

    st.title("Concur - Sensor Fusion Dashboard")
    st.caption(f"LIVE MQTT — last updated {time.strftime('%H:%M:%S', time.localtime(now))}")

    # -------------------------------------------------------------------
    # Node A / Node B / Fused panels
    # -------------------------------------------------------------------

    col_a, col_b, col_fused = st.columns(3)

    render_node_panel(col_a, "Node A", node_a)
    render_node_panel(col_b, "Node B", node_b)

    col_fused.subheader("Final Decision")
    if fused["state"] is None:
        col_fused.info(fused["note"])
    else:
        render_state_badge(col_fused, fused["state"])
        col_fused.metric("Confidence", f"{fused['confidence']:.0%}")
        col_fused.progress(fused["confidence"])
        if fused["agree"] is True:
            col_fused.caption("✅ " + fused["note"])
        elif fused["agree"] is False:
            col_fused.caption("⚠️ " + fused["note"])
        else:
            col_fused.caption(fused["note"])

    st.divider()

    # -------------------------------------------------------------------
    # Confidence history (single 0-1 scale, one axis, legend from column names)
    # -------------------------------------------------------------------

    st.subheader("Confidence over time")
    history_df = pd.DataFrame(st.session_state.history).set_index("time")
    st.line_chart(history_df, height=280)

    st.subheader("Recent fused state changes")
    if st.session_state.events:
        st.dataframe(
            pd.DataFrame(st.session_state.events).iloc[::-1],
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("No state changes yet.")


# ---------------------------------------------------------------------------
# Sidebar - data source configuration
# ---------------------------------------------------------------------------

st.sidebar.header("Data source")
host = st.sidebar.text_input("Broker host", DEFAULT_HOST)
port = st.sidebar.number_input("Port", value=DEFAULT_PORT, step=1)
username = st.sidebar.text_input("Username", "")
password = st.sidebar.text_input("Password", "", type="password")
topic_a = st.sidebar.text_input("Node A topic", DEFAULT_TOPIC_NODE_A)
topic_b = st.sidebar.text_input("Node B topic", DEFAULT_TOPIC_NODE_B)

if st.sidebar.button("Connect"):
    if st.session_state.mqtt_source is not None:
        st.session_state.mqtt_source.close()
    st.session_state.mqtt_source = MqttDataSource(
        host=host,
        port=int(port),
        username=username,
        password=password,
        topic_node_a=topic_a,
        topic_node_b=topic_b,
    )

source = st.session_state.mqtt_source
if source is None:
    st.sidebar.warning("Not connected yet - click Connect.")
elif source.error:
    st.sidebar.error(f"Connection error: {source.error}")
elif source.connected:
    st.sidebar.success("Connected")
else:
    st.sidebar.info("Connecting...")

st.sidebar.divider()
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (s)", 1, 10, 2)
st.sidebar.button("Refresh now")


@st.fragment(run_every=refresh_interval if auto_refresh else None)
def render_dashboard(source):
    render_dashboard_body(source)


render_dashboard(source)
