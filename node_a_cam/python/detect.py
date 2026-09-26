from datetime import datetime, UTC
from json import dumps
from typing import TypedDict, override
from rabbit import send


class DetectionObject(TypedDict):
    """
    The type returned from the camera API
    """

    confidence: float
    bounding_box_xyxy: tuple[int, int, int, int]


# Classes (detections) we want to keep. Everything else is ignored.
include_classes = ["person"]


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


def process_detection(detections: dict[str, list[DetectionObject]], *, conn):
    """
    Handler method to handle a detection
    """
    for class_name, objects in detections.items():
        if class_name not in include_classes:
            continue

        for obj in objects:
            bbox: tuple[int, int, int, int] = obj.get("bounding_box_xyxy")
            confidence: float = obj.get("confidence")

            # This is probably reachable anyway
            if not bbox:
                continue

            detection: Detection = Detection(bbox, confidence)

            entry = {
                "class": class_name,
                "detection": str(detection),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Print the bounding box data directly to the console
            print(entry)
            send(conn, "sensors/node_a/state", dumps(entry))
