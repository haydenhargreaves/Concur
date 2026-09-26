from collections import deque
from json import dumps
from math import hypot, log
from statistics import median
from time import monotonic, time
from typing import TypedDict, override
from rabbit import send


class DetectionObject(TypedDict):
    """
    The type returned from the camera API
    """

    confidence: float
    bounding_box_xyxy: tuple[int, int, int, int]


# Classes (detections) to process. All other model outputs are ignored.
include_classes = ["person"]


class MotionDecision(TypedDict):
    state: int
    direction: int
    confidence: float


class NodeAPacket(MotionDecision):
    """The complete packet schema published by node A."""

    version: int
    node: str
    timestamp: int
    health: str


class MotionClassifier:
    """Classifies the apparent movement of the one person in the camera view."""

    WINDOW_SECONDS = 1.50
    MIN_WINDOW_SECONDS = 0.05
    MIN_SAMPLES = 2
    ENDPOINT_SAMPLES = 3
    IDLE_CENTER_SPEED = 0.12
    IDLE_SCALE_RATE = 0.10
    SCALE_DIRECTION_RATE = 0.03
    FULL_DIRECTION_RATE = 0.10
    FULL_OBSERVATION_SECONDS = 0.5
    CONSISTENCY_SAMPLES = 5

    def __init__(self) -> None:
        self._samples: deque[tuple[float, float, float, float, float]] = deque()
        self._recent_candidates: deque[str] = deque(maxlen=self.CONSISTENCY_SAMPLES)

    def observe(self, detection: "Detection", now: float) -> MotionDecision | None:
        if detection.w <= 0 or detection.h <= 0:
            return None

        center_x = (detection.x_min + detection.x_max) / 2
        center_y = (detection.y_min + detection.y_max) / 2
        scale = (detection.w * detection.h) ** 0.5
        self._samples.append((now, center_x, center_y, scale, detection.confidence))

        # Preserve two samples even when detector callbacks are slower than the window.
        while (
            len(self._samples) > self.MIN_SAMPLES
            and now - self._samples[0][0] > self.WINDOW_SECONDS
        ):
            self._samples.popleft()

        if (
            len(self._samples) < self.MIN_SAMPLES
            or now - self._samples[0][0] < self.MIN_WINDOW_SECONDS
        ):
            return None

        samples = list(self._samples)
        endpoint_count = min(self.ENDPOINT_SAMPLES, len(samples) // 2)
        start = samples[:endpoint_count]
        end = samples[-endpoint_count:]
        duration = median(sample[0] for sample in end) - median(
            sample[0] for sample in start
        )
        if duration <= 0:
            return None

        start_x = median(sample[1] for sample in start)
        start_y = median(sample[2] for sample in start)
        end_x = median(sample[1] for sample in end)
        end_y = median(sample[2] for sample in end)
        start_scale = median(sample[3] for sample in start)
        end_scale = median(sample[3] for sample in end)
        average_scale = median(sample[3] for sample in samples)

        # Normalize image motion by the person's size so near and far subjects compare fairly.
        center_speed = (
            hypot(end_x - start_x, end_y - start_y) / average_scale / duration
        )
        scale_rate = log(end_scale / start_scale) / duration

        if scale_rate > self.SCALE_DIRECTION_RATE:
            candidate = "approaching"
        elif scale_rate < -self.SCALE_DIRECTION_RATE:
            candidate = "moving_away"
        elif (
            center_speed < self.IDLE_CENTER_SPEED
            and abs(scale_rate) < self.IDLE_SCALE_RATE
        ):
            candidate = "idle"
        else:
            candidate = "abnormal"

        self._recent_candidates.append(candidate)
        consistency = self._recent_candidates.count(candidate) / len(
            self._recent_candidates
        )
        observation_quality = min(duration / self.FULL_OBSERVATION_SECONDS, 1.0)

        if candidate in ("approaching", "moving_away"):
            signal_strength = min(
                (abs(scale_rate) - self.SCALE_DIRECTION_RATE)
                / (self.FULL_DIRECTION_RATE - self.SCALE_DIRECTION_RATE),
                1.0,
            )
        elif candidate == "idle":
            signal_strength = 1.0 - max(
                center_speed / self.IDLE_CENTER_SPEED,
                abs(scale_rate) / self.SCALE_DIRECTION_RATE,
            )
        else:
            motion_strength = min(
                (center_speed - self.IDLE_CENTER_SPEED) / self.IDLE_CENTER_SPEED,
                1.0,
            )
            direction_ambiguity = 1.0 - min(
                abs(scale_rate) / self.SCALE_DIRECTION_RATE,
                1.0,
            )
            signal_strength = motion_strength * direction_ambiguity

        # Blend evidence instead of multiplying it so several partial signals do not
        # collapse an otherwise correct classification to an unrealistically low score.
        motion_confidence = (
            0.50 * max(signal_strength, 0.0)
            + 0.25 * observation_quality
            + 0.25 * consistency
        )
        detector_confidence = sorted(sample[4] for sample in samples)[
            (len(samples) - 1) // 4
        ]
        final_confidence = round(
            0.40 * detector_confidence + 0.60 * motion_confidence,
            2,
        )

        if candidate == "idle":
            state, direction = 0, 2
        elif candidate == "approaching":
            state, direction = 1, 0
        elif candidate == "moving_away":
            state, direction = 1, 1
        else:
            state, direction = 2, 2

        return {
            "state": state,
            "direction": direction,
            "confidence": final_confidence,
        }


class Detection:
    """
    A single detection from the camera; basically a 'box' around the person
    """

    x_min: int
    x_max: int
    y_min: int
    y_max: int
    h: int
    w: int
    area: int
    confidence: float

    def __init__(self, bbox: tuple[int, int, int, int], confidence: float) -> None:
        self.x_min, self.y_min, self.x_max, self.y_max = bbox
        self.h = self.y_max - self.y_min
        self.w = self.x_max - self.x_min
        self.area = self.h * self.w
        self.confidence = round(confidence, 2)

    @override
    def __str__(self) -> str:
        return (
            f"x_min: {self.x_min} y_min: {self.y_min} x_max: {self.x_max} "
            f"y_max: {self.y_max} w: {self.w} h: {self.h} area: {self.area} "
            f"confidence: {self.confidence}"
        )


motion_classifier = MotionClassifier()


def process_detection(
    detections: dict[str, list[DetectionObject]], *, conn
) -> NodeAPacket | None:
    """
    Handler method to handle a detection
    """
    objects = [
        obj
        for class_name, class_objects in detections.items()
        if class_name in include_classes
        for obj in class_objects
    ]
    if not objects:
        return None

    # The application assumes one person; use the strongest box if the detector emits duplicates.
    obj = max(objects, key=lambda item: item["confidence"])
    bbox = obj["bounding_box_xyxy"]
    model_confidence = obj["confidence"]

    decision = motion_classifier.observe(Detection(bbox, model_confidence), monotonic())
    if decision is None:
        return None

    packet: NodeAPacket = {
        "version": 1,
        "node": "node_a",
        "timestamp": int(time()),
        **decision,
        "health": "HEALTHY",
    }

    print(dumps(packet))
    send(conn, "sensors/node_a/state", dumps(packet))
    return packet
