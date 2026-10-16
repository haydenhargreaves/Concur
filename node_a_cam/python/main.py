# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

from threading import Event, Thread

from arduino.app_utils import App, Leds
from arduino.app_bricks.video_objectdetection import VideoObjectDetection

from detect import process_detection, publish_heartbeat
from rabbit import connect

HEARTBEAT_INTERVAL_SECONDS = 0.5

conn = connect("node_a")

Leds.set_led1_color(0, 0, 0)


def on_detection(detections):
    process_detection(detections, conn=conn)


def heartbeat_loop(stop_event: Event) -> None:
    while not stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
        publish_heartbeat(conn)


detection_stream = VideoObjectDetection(confidence=0.5, debounce_sec=0.0)
detection_stream.on_detect_all(on_detection)

heartbeat_stop = Event()
heartbeat_thread = Thread(
    target=heartbeat_loop,
    args=(heartbeat_stop,),
    name="node-a-heartbeat",
    daemon=True,
)
heartbeat_thread.start()

try:
    App.run()
finally:
    heartbeat_stop.set()
    heartbeat_thread.join(timeout=HEARTBEAT_INTERVAL_SECONDS + 0.1)
