#!/usr/bin/env bash

scp -r ./node_a_cam/* concur:/home/arduino/ArduinoApps/concur
scp -r ./lib/* concur:/home/arduino/ArduinoApps/concur/python
scp .env concur:/home/arduino/ArduinoApps/concur/python
