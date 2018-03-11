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

strSlogan1 = "PiXtend Python Library (PPL) demo for GPIO usage."
strSlogan2 = "PiXtend Python Library (PPL) demo for GPIO usage finished."

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
                    print("One time configuration: Setting the GPIOs")
                    print("")
                    p.gpio0_direction = p.GPIO_OUTPUT
                    p.gpio1_direction = p.GPIO_OUTPUT
                    p.gpio2_direction = p.GPIO_OUTPUT
                    p.gpio3_direction = p.GPIO_OUTPUT

                    p.gpio0 = p.ON
                    p.gpio1 = p.OFF
                    p.gpio2 = p.ON
                    p.gpio3 = p.OFF

                if toggle_counter >= 10:
                    toggle_counter = 0
                    if p.gpio0 == p.ON:
                        p.gpio0 = p.OFF
                        p.gpio1 = p.ON
                        p.gpio2 = p.OFF
                        p.gpio3 = p.ON
                    else:
                        p.gpio0 = p.ON
                        p.gpio1 = p.OFF
                        p.gpio2 = p.ON
                        p.gpio3 = p.OFF

                toggle_counter += 1

                # Build text with values from the GPIOs
                str_text = "Cycle No.: {0}\n".format(cycle_counter)
                str_text += "GPIO 0: {0}\n".format(p.gpio0)
                str_text += "GPIO 1: {0}\n".format(p.gpio1)
                str_text += "GPIO 2: {0}\n".format(p.gpio2)
                str_text += "GPIO 3: {0}\n".format(p.gpio3)

                # Print text to console
                print(str_text, end="\r")

                # Reset cursor
                for i in range(0, 5, 1):
                    sys.stdout.write("\x1b[A")

            else:
                print("Auto Mode - Communication is not yet up...Please wait...")

            # Wait at minimum 0.1sec or 100ms before getting new values
            time.sleep(0.1)

        except KeyboardInterrupt:
            # Keyboard interrupt caught, Ctrl + C, now clean up and leave program
            p.close()
            p = None
            for i in range(0, 6, 1):
                print("")

            print(strSlogan2)
            break
else:
    # If there was an error when opening the SPI bus interface, leave the program.
    print("")
    print("There was a problem with the PiXtend communication. Quitting.")
    print("")
    print(strSlogan2)
