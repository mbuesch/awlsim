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

strSlogan1 = "PiXtend Python Library (PPL) demo for digital outputs including relays."
strSlogan2 = "PiXtend Python Library (PPL) demo for digital outputs including relays finished."

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
    toggle_counter = 0

    while True:
        try:
            # Using Auto Mode for optimal SPI bus usage
            if p.auto_mode() == 0:
                cycle_counter += 1

                if not is_config:
                    is_config = True
                    print("One time configuration: Setting the relays and digital outputs in an alternating pattern")
                    print("The value 0 = OFF and the value 1 = ON")
                    print("")
                    # Setting the relays and digital outputs with a pattern which can be toggled later.
                    # Side effect the LEDs on the PiXtend board alternate nicely back and forth.
                    p.relay0 = p.ON
                    p.relay1 = p.OFF
                    p.relay2 = p.ON
                    p.relay3 = p.OFF
                    p.digital_output0 = p.ON
                    p.digital_output1 = p.OFF
                    p.digital_output2 = p.ON
                    p.digital_output3 = p.OFF
                    p.digital_output4 = p.ON
                    p.digital_output5 = p.OFF

                # Build text with values from all digital outputs und relays
                str_text = "Cycle No.: {0}\n".format(cycle_counter)
                str_text += "Digital Output 0: {0}\n".format(p.digital_output0)
                str_text += "Digital Output 1: {0}\n".format(p.digital_output1)
                str_text += "Digital Output 2: {0}\n".format(p.digital_output2)
                str_text += "Digital Output 3: {0}\n".format(p.digital_output3)
                str_text += "Digital Output 4: {0}\n".format(p.digital_output4)
                str_text += "Digital Output 5: {0}\n".format(p.digital_output5)
                str_text += "Relay 0:          {0}\n".format(p.relay0)
                str_text += "Relay 1:          {0}\n".format(p.relay1)
                str_text += "Relay 2:          {0}\n".format(p.relay2)
                str_text += "Relay 3:          {0}\n".format(p.relay3)

                # Print text to console
                print(str_text, end="\r")

                # Reset cursor
                for i in range(0, 11, 1):
                    sys.stdout.write("\x1b[A")

                if toggle_counter >= 25:
                    # Toggle the relays and digital outputs on and off
                    p.relay0 = p.relay0 ^ 1
                    p.relay1 = p.relay1 ^ 1
                    p.relay2 = p.relay2 ^ 1
                    p.relay3 = p.relay3 ^ 1
                    p.digital_output0 = p.digital_output0 ^ 1
                    p.digital_output1 = p.digital_output1 ^ 1
                    p.digital_output2 = p.digital_output2 ^ 1
                    p.digital_output3 = p.digital_output3 ^ 1
                    p.digital_output4 = p.digital_output4 ^ 1
                    p.digital_output5 = p.digital_output5 ^ 1
                    toggle_counter = 0
                else:
                    toggle_counter += 1

            else:
                print("Auto Mode - Communication is not yet up...Please wait...")

            # Wait at minimum 0.1sec or 100ms before getting new values
            time.sleep(0.1)

        except KeyboardInterrupt:
            # Keyboard interrupt caught, Ctrl + C, now clean up and leave program
            p.close()
            p = None
            for i in range(0, 12, 1):
                print("")

            print(strSlogan2)
            break
else:
    # If there was an error when opening the SPI bus interface, leave the program.
    print("")
    print("There was a problem with the PiXtend communication. Quitting.")
    print("")
    print(strSlogan2)
