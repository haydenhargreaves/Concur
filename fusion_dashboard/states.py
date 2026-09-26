"""
Display labels for the classification states. The state ids themselves come
from node_b_sensors/python/classifier.py via node_b_bridge - not redefined
here - so there's one source of truth for what each id means.
"""

from node_b_bridge import STATE_ABNORMAL_DISTURBANCE, STATE_ACTIVE_PRESENCE, STATE_IDLE

STATE_LABELS = {
    STATE_IDLE: "Idle",
    STATE_ACTIVE_PRESENCE: "Active Presence",
    STATE_ABNORMAL_DISTURBANCE: "Abnormal Disturbance",
}
