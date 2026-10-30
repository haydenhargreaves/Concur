
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
FUSED_COLOR = "#37e6ff"
# Node A pulses every 0.5s; Node B's cadence is unknown, so keep some slack.
STALE_AFTER_SECONDS = 5

DIRECTION_LABELS = {
    0: "Approaching",
    1: "Moving away",
    # Node B can use any direction value appropriate to its own classifier.
    2: "N/A",
}

st.set_page_config(page_title="Concur - Sensor Fusion Dashboard", layout="wide")

# Streamlit sizes most text in rem, so raising the root size scales the whole UI.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@300;400;500;700&display=swap');
    html { font-size: 112.5%; }
    html, body, [class*="st-"], .stApp { font-family: 'Space Grotesk', system-ui, sans-serif; }
    /* Keep Streamlit's icon font; the override above would turn icons into plain letters. */
    [data-testid="stIconMaterial"], [data-testid="stIconMaterial"] *,
    span[class*="material-symbols"], span[class*="material-icons"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important; text-transform: none; letter-spacing: normal;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 50% 0%, rgba(55,230,255,.10), transparent 60%),
            radial-gradient(ellipse at 100% 100%, rgba(139,107,255,.08), transparent 55%),
            #05070d;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: rgba(10,15,28,.85); border-right: 1px solid rgba(55,230,255,.16); }
    h1, h2, h3 { font-weight: 500; letter-spacing: -.02em; }
    h2, h3, [data-testid="stMetricLabel"], .stCaption, [data-testid="stSidebar"] h2 {
        font-family: 'JetBrains Mono', monospace;
    }
    h3 { font-size: .85rem !important; letter-spacing: .2em; text-transform: uppercase; color: #37e6ff; }
    [data-testid="stMetricValue"] { font-weight: 300; letter-spacing: -.03em; }
    [data-testid="stColumn"] > div > [data-testid="stVerticalBlock"] {
        background: rgba(14,22,40,.62); border: 1px solid rgba(55,230,255,.16);
        border-radius: 16px; padding: 1.1rem 1.3rem; backdrop-filter: blur(14px);
    }
    [data-testid="stAlert"] { border-radius: 12px; }
    .stButton > button {
        font-family: 'JetBrains Mono', monospace; letter-spacing: .12em; text-transform: uppercase;
        border-radius: 999px; border: 1px solid #37e6ff; color: #37e6ff; background: transparent;
    }
    .stButton > button:hover { background: #37e6ff; color: #05070d; border-color: #37e6ff; box-shadow: 0 0 24px rgba(55,230,255,.45); }
    hr { border-color: rgba(55,230,255,.16) !important; }
    .block-container { padding-top: 2rem; }
    .block-container h1 { padding-top: 0; }
    [data-testid="stSidebarHeader"] {
        height: 2.75rem; min-height: 0;
        padding: 0.75rem 1.25rem 0 0;
        display: flex; justify-content: flex-end; align-items: center;
    }
    [data-testid="stSidebarUserContent"] { padding-top: 1rem; }
    [data-testid="stSidebar"] h2 { padding-top: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

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


def is_stale(reading_, now):
    received_at = reading_.get("received_at") if reading_ else None
    return received_at is not None and now - received_at > STALE_AFTER_SECONDS


def is_faulted(reading_):
    return reading_ is not None and reading_.get("health", "HEALTHY") != "HEALTHY"


def is_down(reading_, now):
    return is_stale(reading_, now) or is_faulted(reading_)


def render_node_panel(container, title, reading_, now):
    container.subheader(title)
    if reading_ is None:
        container.info("No data yet.")
        return

    if is_stale(reading_, now):
        container.error(
            f"OFFLINE - no packets for {now - reading_['received_at']:.0f}s", icon="🔌"
        )
        container.caption(
            f"Last packet at {time.strftime('%H:%M:%S', time.localtime(reading_['received_at']))}"
        )
        return

    if is_faulted(reading_):
        container.error(f"FAULT - {reading_['health']}", icon="⚠️")
        container.caption(
            f"Last updated: {time.strftime('%H:%M:%S', time.localtime(reading_['timestamp']))}"
        )
        return

    render_state_badge(container, reading_["state"])
    container.metric("Confidence", f"{reading_['confidence']:.0%}")
    container.progress(reading_["confidence"])

    direction = reading_.get("direction")
    direction_label = DIRECTION_LABELS.get(direction, direction if direction is not None else "N/A")
    container.caption(f"Direction: {direction_label}")
    container.caption(f"Health: {reading_.get('health', 'UNKNOWN')}")

    with container.expander("Packet data"):
        st.json(reading_)

    container.caption(
        f"Last updated: {time.strftime('%H:%M:%S', time.localtime(reading_['timestamp']))}"
    )


def render_dashboard_body(source):
    # -------------------------------------------------------------------
    # Pull the latest reading
    # -------------------------------------------------------------------

    reading = source.get_latest() if source is not None else {"node_a": None, "node_b": None}
    node_a, node_b = reading.get("node_a"), reading.get("node_b")

    now = time.time()
    live_a = None if is_down(node_a, now) else node_a
    live_b = None if is_down(node_b, now) else node_b
    fused = fuse(live_a, live_b)

    st.session_state.history.append(
        {
            "time": pd.to_datetime(now, unit="s"),
            "Node A": live_a["confidence"] if live_a else None,
            "Node B": live_b["confidence"] if live_b else None,
            "Fused": fused["confidence"],
        }
    )
    st.session_state.history = st.session_state.history[-HISTORY_LIMIT:]

    if fused["state"] is not None and fused["state"] != st.session_state.last_fused_state:
        st.session_state.events.append(
            {
                "time": pd.to_datetime(now, unit="s").strftime("%H:%M:%S"),
                "Fused state": STATE_LABELS[fused["state"]],
            }
        )
        st.session_state.events = st.session_state.events[-20:]
    st.session_state.last_fused_state = fused["state"]

    # -------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------

    st.markdown(
        f'# <span style="color:{FUSED_COLOR};letter-spacing:.3em">CONCUR</span> <span style="font-weight:300">&middot; Sensor Fusion</span>',
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------
    # Node A / Node B / Fused panels
    # -------------------------------------------------------------------

    col_a, col_b, col_fused = st.columns(3)

    render_node_panel(col_a, "Node A", node_a, now)
    render_node_panel(col_b, "Node B", node_b, now)

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
    st.line_chart(
        history_df,
        height=420,
        color=["#ffd166", "#3dff9a", FUSED_COLOR],  # Node A, Node B, Fused
    )

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
username = st.sidebar.text_input("Username", "")
password = st.sidebar.text_input("Password", "", type="password")

if st.sidebar.button("Connect"):
    if st.session_state.mqtt_source is not None:
        st.session_state.mqtt_source.close()
    st.session_state.mqtt_source = MqttDataSource(
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        username=username,
        password=password,
        topic_node_a=DEFAULT_TOPIC_NODE_A,
        topic_node_b=DEFAULT_TOPIC_NODE_B,
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
refresh_interval = st.sidebar.slider("Refresh interval (s)", 1, 10, 1)
st.sidebar.button("Refresh now")


@st.fragment(run_every=refresh_interval if auto_refresh else None)
def render_dashboard(source):
    render_dashboard_body(source)


render_dashboard(source)
