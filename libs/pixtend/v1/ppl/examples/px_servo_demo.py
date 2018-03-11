#!/usr/bin/env python
# coding=utf-8

# This file is part of the PiXtend(R) Project.
#
# For more information about PiXtend(R) and this program,
# see <https://www.pixtend.de> or <https://www.pixtend.com>
#
# Copyright (C) 2018 Robin Turner
# Qube Solutions UG (haftungsbeschränkt), Arbachtalstr. 6
# 72800 Eningen, Germany
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
# Import Pixtend class
from pixtendlib import Pixtend
import time
import sys

strSlogan1 = "PiXtend Python Library (PPL) demo for Servo usage."
strSlogan2 = "PiXtend Python Library (PPL) demo for Servo usage finished."

# -----------------------------------------------------------------
# Print Art and Slogan
# -----------------------------------------------------------------
print("")
print("    ____     _    _  __   __                      __")
print("   / __ \\   (_)  | |/ /  / /_  ___    ____   ____/ /")
print("  / /_/ /  / /   |   /  / __/ / _ \\  / __ \\ / __  / ")
print(" / ____/  / /   /   |  / /_  /  __/ / / / // /_/ /  ")
print("/_/      /_/   /_/|_|  \\__/  \\___/ /_/ /_/ \\__,_/   ")
print("")
print(strSlogan1)
print("")

# -----------------------------------------------------------------
# Create instance
# -----------------------------------------------------------------
p = Pixtend()

# Open SPI bus for communication
try:
    p.open()
except IOError as io_err:
    # On error, print an error text and delete the Pixtend instance.
    print("Error opening the SPI bus! Error is: ", io_err)
    p.close()
    p = None

# -----------------------------------------------------
# Main Program
# -----------------------------------------------------
if p is not None:
    print("Running Main Program - Hit Ctrl + C to exit")
    # Set some variables needed in the main loop
    is_config = False
    cycle_counter = 0
    servo_mode = True
    pwm_init = False
    servo0_value = 0
    servo1_value = 0
    inc_value_s0 = 10
    inc_value_s1 = 10

    while True:
        try:
            # Using Auto Mode for optimal SPI bus usage
            if p.auto_mode() == 0:
                cycle_counter += 1

                if not is_config:
                    is_config = True
                    print("One time configuration: Setting the PWM configuration to Servo Mode")
                    print("")
                    p.pwm_ctrl_mode = p.SERVO_MODE
                    # Set some base values to play with
                    p.servo0 = 0
                    p.servo1 = 250

                # Servo Mode: Write values to the PWMs in Servo Mode
                servo0_value = servo0_value + inc_value_s0
                if servo0_value >= 250:
                    servo0_value = 0
                p.servo0 = servo0_value

                servo1_value = servo1_value - inc_value_s1
                if servo1_value <= 0:
                    servo1_value = 250
                p.servo1 = servo1_value

                # Clear text from before
                str_text = "Cycle No.: {0}\n".format(cycle_counter)
                str_text += "Servo 0:    \n"
                str_text += "Servo 1:    \n"

                # Print text to console
                print(str_text, end="\r")

                # Reset cursor
                for i in range(0, 3, 1):
                    sys.stdout.write("\x1b[A")

                # Build text with values from both PWMs in Servo Mode
                str_text = "Cycle No.: {0}\n".format(cycle_counter)
                str_text += "Servo 0: {0}\n".format(servo0_value)
                str_text += "Servo 1: {0}\n".format(servo1_value)

                # Print text to console
                print(str_text, end="\r")

                # Reset cursor
                for i in range(0, 3, 1):
                    sys.stdout.write("\x1b[A")

            else:
                print("Auto Mode - Communication is not yet up...Please wait...")

            # Wait at minimum 0.1sec, for the Servos 1 second might be better
            time.sleep(1)

        except KeyboardInterrupt:
            # Keyboard interrupt caught, Ctrl + C, now clean up and leave program
            p.close()
            p = None
            for i in range(0, 4, 1):
                print("")

            print(strSlogan2)
            break
else:
    # If there was an error when opening the SPI bus interface, leave the program.
    print("")
    print("There was a problem with the PiXtend communication. Quitting.")
    print("")
    print(strSlogan2)
