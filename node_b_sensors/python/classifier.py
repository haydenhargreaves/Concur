import math

IDLE = 0
ACTIVE_PRESENCE = 1
ABNORMAL_DISTURBANCE = 2

# An object/person near the sensor also shadows the co-located light
# sensor, so low lux corroborates a distance-based ACTIVE_PRESENCE read.
# Placeholder threshold - calibrate against real readings once available.
LIGHT_PRESENCE_LUX_THRESHOLD = 50
LIGHT_PRESENCE_CONFIDENCE_BOOST = 0.05

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

        light_ok = data.get("light_ok", False)
        light_lux = data.get("light_lux", -1)
        if light_ok and 0 <= light_lux < LIGHT_PRESENCE_LUX_THRESHOLD:
            confidence = min(0.99, confidence + LIGHT_PRESENCE_CONFIDENCE_BOOST)

        return ACTIVE_PRESENCE, round(confidence, 2)

    # -------------------------------------------------
    # STATE 0: IDLE
    # -------------------------------------------------

    return IDLE, 0.90