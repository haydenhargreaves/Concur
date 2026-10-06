import math
import time
from collections import deque

IDLE = 0
ACTIVE_PRESENCE = 1
ABNORMAL_DISTURBANCE = 2

DIRECTION_APPROACHING = 0
DIRECTION_MOVING_AWAY = 1
DIRECTION_NA = 2

LIGHT_PRESENCE_LUX_THRESHOLD = 50
LIGHT_PRESENCE_CONFIDENCE_BOOST = 0.05


DIRECTION_WINDOW_SECONDS = 2.0
DIRECTION_MIN_SAMPLES = 3
# Minimum rate of change (mm/s) to call it a trend rather than sensor noise.
DIRECTION_RATE_MM_PER_SEC = 40.0


class DistanceDirectionTracker:
    """Infers approach/away direction from the trend in distance_mm over time."""

    def __init__(self):
        self._samples = deque()

    def update(self, distance_mm, distance_ok, now=None):
        now = time.time() if now is None else now

        if not distance_ok or distance_mm is None or distance_mm <= 0:
            self._samples.clear()
            return DIRECTION_NA

        self._samples.append((now, distance_mm))
        while now - self._samples[0][0] > DIRECTION_WINDOW_SECONDS:
            self._samples.popleft()

        if len(self._samples) < DIRECTION_MIN_SAMPLES:
            return DIRECTION_NA

        duration = self._samples[-1][0] - self._samples[0][0]
        if duration <= 0:
            return DIRECTION_NA

        rate = (self._samples[-1][1] - self._samples[0][1]) / duration

        if rate < -DIRECTION_RATE_MM_PER_SEC:
            return DIRECTION_APPROACHING
        if rate > DIRECTION_RATE_MM_PER_SEC:
            return DIRECTION_MOVING_AWAY
        return DIRECTION_NA


_direction_tracker = DistanceDirectionTracker()


def classify_node_b(data):

    if not data:
        return IDLE, 0.0, DIRECTION_NA

    # -------------------------------------------------
    # Get sensor values
    # -------------------------------------------------

    distance = data.get("distance_mm", -1)
    direction = _direction_tracker.update(distance, data.get("distance_ok", False))

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
        return ABNORMAL_DISTURBANCE, 0.95, direction

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

        return ACTIVE_PRESENCE, round(confidence, 2), direction

    # -------------------------------------------------
    # STATE 0: IDLE
    # -------------------------------------------------

    return IDLE, 0.90, direction