import math


# =====================================================
# Local Classification States
# =====================================================

IDLE = 0
ACTIVE_PRESENCE = 1
ABNORMAL_DISTURBANCE = 2


# =====================================================
# Node B Local Classifier
# =====================================================

def classify_node_b(data):

    if not data:
        return IDLE, 0.0

    # -------------------------------------------------
    # Get sensor values
    # -------------------------------------------------

    distance = data.get("distance_mm", -1)

    ax = data.get("accel_x", 0)
    ay = data.get("accel_y", 0)
    az = data.get("accel_z", 0)

    # -------------------------------------------------
    # Calculate acceleration magnitude
    # -------------------------------------------------

    acceleration_magnitude = math.sqrt(
        ax**2 + ay**2 + az**2
    )

    # Assuming accelerometer values are in g
    motion_delta = abs(acceleration_magnitude - 1.0)

    # -------------------------------------------------
    # STATE 2: ABNORMAL DISTURBANCE
    # -------------------------------------------------

    if motion_delta > 0.8:
        return ABNORMAL_DISTURBANCE, 0.95

    # -------------------------------------------------
    # STATE 1: ACTIVE PRESENCE
    # -------------------------------------------------

    if 0 < distance <= 800:

        confidence = max(
            0.5,
            1.0 - (distance / 1600.0)
        )

        return ACTIVE_PRESENCE, round(confidence, 2)

    # -------------------------------------------------
    # STATE 0: IDLE
    # -------------------------------------------------

    return IDLE, 0.90