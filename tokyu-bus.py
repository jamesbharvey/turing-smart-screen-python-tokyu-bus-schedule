#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen-python - a Python system monitor and library for USB-C displays like Turing Smart Screen or XuanFang
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from time import sleep

from dotenv import load_dotenv

from library.pythoncheck import check_python_version

# This file is a simple Python test program using the library code to display custom content on screen (see README)
check_python_version()

import signal
import time
import datetime
import os
import sys


# Import only the modules for LCD communication
from library.lcd.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd.lcd_comm_rev_b import LcdCommRevB
from library.lcd.lcd_comm_rev_c import LcdCommRevC
from library.lcd.lcd_comm_rev_d import LcdCommRevD
from library.lcd.lcd_comm_weact_a import LcdCommWeActA
from library.lcd.lcd_comm_weact_b import LcdCommWeActB
from library.lcd.lcd_simulated import LcdSimulated
from library.log import logger

from odpt_tokyu_bus import (
    build_timetables,
    current_calendar,
    direction_label,
    upcoming_departures,
)

load_dotenv()
CONSUMER_KEY = os.environ.get("ODPT_CONSUMER_KEY")
if not CONSUMER_KEY:
    sys.exit("Error: ODPT_CONSUMER_KEY not set in environment or .env file")

STOP_NAME = "Tamagawaonshitsumura"

timetables = build_timetables(CONSUMER_KEY, STOP_NAME)

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux, etc. or "AUTO" for auto-discovery
# COM_PORT = "/dev/ttyACM0"
# COM_PORT = "COM5"
COM_PORT = "AUTO"

# Display revision:
# - A      for Turing 3.5" and UsbPCMonitor 3.5"/5"
# - B      for Xuanfang 3.5" (inc. flagship)
# - C      for Turing 5"
# - D      for Kipye Qiye Smart Display 3.5"
# - SIMU   for simulated display (image written in screencap.png)
# To identify your smart screen: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions
REVISION = "A"

# Display width & height in pixels for portrait orientation
# /!\ Do not switch width/height here for landscape, use lcd_comm.SetOrientation below
# 320x480 for 3.5" models
# 480x480 for 2.1" models
# 480x800 for 5" models
# 480x1920 for 8.8" models
WIDTH, HEIGHT = 320, 480

assert WIDTH <= HEIGHT, "Indicate display width/height for PORTRAIT orientation: width <= height"

stop = False

if __name__ == "__main__":

    def sighandler(signum, frame):
        global stop
        stop = True


    # Set the signal handlers, to send a complete frame to the LCD before exit
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    is_posix = os.name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, sighandler)

    # Build your LcdComm object based on the HW revision
    lcd_comm = None
    if REVISION == "A":
        logger.info("Selected Hardware Revision A (Turing Smart Screen 3.5\" & UsbPCMonitor 3.5\"/5\")")
        # NOTE: If you have UsbPCMonitor 5" you need to change the width/height to 480x800 below
        lcd_comm = LcdCommRevA(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "B":
        logger.info("Selected Hardware Revision B (XuanFang screen 3.5\" version B / flagship)")
        lcd_comm = LcdCommRevB(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "C":
        logger.info("Selected Hardware Revision C (Turing Smart Screen 5\")")
        lcd_comm = LcdCommRevC(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "D":
        logger.info("Selected Hardware Revision D (Kipye Qiye Smart Display 3.5\")")
        lcd_comm = LcdCommRevD(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "WEACT_A":
        logger.info("Selected Hardware WeAct Studio Display FS V1 3.5\"")
        lcd_comm = LcdCommWeActA(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "WEACT_B":
        logger.info("Selected Hardware WeAct Studio Display FS V1 0.96\"")
        lcd_comm = LcdCommWeActB(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)
    elif REVISION == "SIMU":
        logger.info("Selected Simulated LCD")
        lcd_comm = LcdSimulated(display_width=WIDTH, display_height=HEIGHT)
    else:
        logger.error("Unknown revision")
        try:
            sys.exit(1)
        except:
            os._exit(1)

    # Reset screen in case it was in an unstable state (screen is also cleared)
    lcd_comm.Reset()

    # Send initialization commands
    lcd_comm.InitializeComm()

    # Set brightness in % (warning: revision A display can get hot at high brightness! Keep value at 50% max for rev. A)
    lcd_comm.SetBrightness(level=10)

    # Set backplate RGB LED color (for supported HW only)
    lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))

    # Set orientation (screen starts in Portrait)
    lcd_comm.SetOrientation(orientation=Orientation.PORTRAIT)

    # Define background picture
    background = f"res/backgrounds/example_{lcd_comm.get_width()}x{lcd_comm.get_height()}.png"

    # Display sample picture
    logger.debug("setting background picture")
    start = time.perf_counter()
    lcd_comm.DisplayBitmap(background)
    end = time.perf_counter()
    logger.debug(f"background picture set (took {end - start:.3f} s)")

    # Display the current time and some progress bars as fast as possible
    bar_value = 0
    while not stop:
        start = time.perf_counter()
        lcd_comm.DisplayText(str(datetime.datetime.now().time().strftime("%H:%M")), 240, 2,
                             font="res/fonts/roboto/Roboto-Bold.ttf",
                             font_size=30,
                             font_color=(255, 255, 0),
                             align="right",
                             background_image=background)



        for timetable in timetables.values():
            now = datetime.datetime.now()
            dest = ""
            calendar = timetable.get("odpt:calendar", "")
            if calendar != current_calendar():
                continue
            direction = direction_label(timetable.get("odpt:busDirection", []))
            pole = timetable.get("odpt:busstopPole", "").split(".")[-1]
            route = ", ".join(timetable.get("odpt:busroute", []))
            note = timetable.get("odpt:note", "")
            departures = timetable.get("odpt:busstopPoleTimetableObject", [])
            upcoming = upcoming_departures(departures, now, 60 * 12)
            if pole == "b":
                dest = "二子玉川"
                y = 85
            elif pole == "a":
                dest = "多摩川"
                y = 230
            else:
                continue
            try:
                tsugi = upcoming[0][1]['odpt:departureTime']
                tsuginotsugi = upcoming[1][1]['odpt:departureTime']
            except IndexError:
                sleep(30)
                continue
            text = f"{dest}\n{tsugi} {tsuginotsugi}"
            print(text)

            lcd_comm.DisplayText(text, 5, y,
                             font="res/fonts/ZenOldMincho/ZenOldMincho-Medium.ttf",
                             font_size=50,
                             font_color=(255, 255, 255),
                             background_image=background
                             )

        end = time.perf_counter()
        logger.debug(f"refresh done (took {end - start:.3f} s)")
        sleep(10)

    # Close serial connection at exit
    lcd_comm.closeSerial()
