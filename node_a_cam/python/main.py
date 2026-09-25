# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

from arduino.app_utils import App
from arduino.app_bricks.video_objectdetection import VideoObjectDetection

from detect import process_detection
from rabbit import connect

conn = connect("node_a")


def on_detection(detections):
    process_detection(detections, conn=conn)


detection_stream = VideoObjectDetection(confidence=0.5, debounce_sec=0.0)
detection_stream.on_detect_all(on_detection)


App.run()
