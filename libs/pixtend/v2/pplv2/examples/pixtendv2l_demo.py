#!/usr/bin/env python
# coding=utf-8

# This file is part of the PiXtend(R) Project.
#
# For more information about PiXtend(R) and this program,
# see <https://www.pixtend.de> or <https://www.pixtend.com>
#
# Copyright (C) 2018 Robin Turner
# Qube Solutions GmbH, Arbachtalstr. 6
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
# Import PiXtend V2 class
from pixtendv2l import PiXtendV2L
import time
import sys

strSlogan1 = "PiXtend Python Library v2 (PPLv2) demo."
strSlogan2 = "PiXtend Python Library v2 (PPLv2) demo finished."

# -----------------------------------------------------------------
# Print Art and Slogan
# -----------------------------------------------------------------
print("")
print("    ____  _ _  ____                 __   _    _____          __")
print("   / __ \\(_) |/ / /____  ____  ____/ /  | |  / /__ \\        / /")
print("  / /_/ / /|   / __/ _ \\/ __ \\/ __  /   | | / /__/ / ____  / /")
print(" / ____/ //   / /_/  __/ / / / /_/ /    | |/ // __/ /___/ / /__")
print("/_/   /_//_/|_\\__/\\___/_/ /_/\\__,_/     |___//____/      /____/")
print("")
print(strSlogan1)
print("")

# -----------------------------------------------------------------
# Create instance - SPI communication starts automatically
# -----------------------------------------------------------------
p = PiXtendV2L()

# -----------------------------------------------------
# Main Program
# -----------------------------------------------------
if p is not None:
    print("Running Main Program - Hit Ctrl + C to exit")
    # Set some variables needed in the main loop
    is_config = False
    cycle_counter = 0

    while True:
        try:
            # Check if SPI communication is running and the received data is correct
            if p.crc_header_in_error is False and p.crc_data_in_error is False:
                cycle_counter += 1

                if not is_config:
                    is_config = True
                    print("One time configuration: Setting the relays and digital outputs in an alternating pattern")
                    print("The value False = OFF and the value True = ON")
                    print("")
                    # Setting the relays and digital outputs to a pattern which can be toggled later.
                    # Side effect: the LEDs on the PiXtend V2 -L- board alternate nicely back and forth.
                    p.relay0 = p.ON
                    p.relay1 = p.OFF
                    p.relay2 = p.ON
                    p.relay3 = p.OFF
                    p.digital_out0 = p.ON
                    p.digital_out1 = p.OFF
                    p.digital_out2 = p.ON
                    p.digital_out3 = p.OFF
                    p.digital_out4 = p.ON
                    p.digital_out5 = p.OFF
                    p.digital_out6 = p.ON
                    p.digital_out7 = p.OFF
                    p.digital_out8 = p.ON
                    p.digital_out9 = p.OFF
                    p.digital_out10 = p.ON
                    p.digital_out11 = p.OFF

                # clear the text on screen
                str_text = "                                               \n"
                for i in range(0, 43, 1):
                    str_text += "                                               \n"
                str_text += " "
                # Print text to console
                print(str_text, end="\r")
                # Reset cursor
                for i in range(0, 44, 1):
                    sys.stdout.write("\x1b[A")  
                    
                # Print the info text to console
                str_text = "Cycle No.: {0}\n".format(cycle_counter)
                str_text += " \n"
                str_text += "PiXtend V2 -L- Info:\n"
                str_text += "Firmware:    {0}\n".format(p.firmware)
                str_text += "Hardware:    {0}\n".format(p.hardware)
                str_text += "Model:       {0}\n".format(chr(p.model_in))
                str_text += " \n"
                str_text += "Digital Inputs:\n"
                str_text += "DigitalIn00:  {0}\n".format(p.digital_in0)
                str_text += "DigitalIn01:  {0}\n".format(p.digital_in1)
                str_text += "DigitalIn02:  {0}\n".format(p.digital_in2)
                str_text += "DigitalIn03:  {0}\n".format(p.digital_in3)
                str_text += "DigitalIn04:  {0}\n".format(p.digital_in4)
                str_text += "DigitalIn05:  {0}\n".format(p.digital_in5)
                str_text += "DigitalIn06:  {0}\n".format(p.digital_in6)
                str_text += "DigitalIn07:  {0}\n".format(p.digital_in7)
                str_text += "DigitalIn08:  {0}\n".format(p.digital_in8)
                str_text += "DigitalIn09:  {0}\n".format(p.digital_in9)
                str_text += "DigitalIn10:  {0}\n".format(p.digital_in10)
                str_text += "DigitalIn11:  {0}\n".format(p.digital_in11)
                str_text += "DigitalIn12:  {0}\n".format(p.digital_in12)
                str_text += "DigitalIn13:  {0}\n".format(p.digital_in13)
                str_text += "DigitalIn14:  {0}\n".format(p.digital_in14)
                str_text += "DigitalIn15:  {0}\n".format(p.digital_in15)
                str_text += " \n"
                str_text += "Digital Outputs:\n"
                str_text += "DigitalOut00: {0}\n".format(p.digital_out0)
                str_text += "DigitalOut01: {0}\n".format(p.digital_out1)
                str_text += "DigitalOut02: {0}\n".format(p.digital_out2)
                str_text += "DigitalOut03: {0}\n".format(p.digital_out3)
                str_text += "DigitalOut04: {0}\n".format(p.digital_out4)
                str_text += "DigitalOut05: {0}\n".format(p.digital_out5)
                str_text += "DigitalOut06: {0}\n".format(p.digital_out6)
                str_text += "DigitalOut07: {0}\n".format(p.digital_out7)
                str_text += "DigitalOut08: {0}\n".format(p.digital_out8)
                str_text += "DigitalOut09: {0}\n".format(p.digital_out9)
                str_text += "DigitalOut10: {0}\n".format(p.digital_out10)
                str_text += "DigitalOut11: {0}\n".format(p.digital_out11)
                str_text += " \n"
                str_text += "Relays:\n"
                str_text += "Relay0:      {0}\n".format(p.relay0)
                str_text += "Relay1:      {0}\n".format(p.relay1)
                str_text += "Relay2:      {0}\n".format(p.relay2)
                str_text += "Relay3:      {0}\n".format(p.relay3)
                str_text += " "

                # Print text to console
                print(str_text, end="\r")

                # Reset cursor
                for i in range(0, 44, 1):
                    sys.stdout.write("\x1b[A")

                # Toggle the relays and digital outputs on and off
                p.relay0 = not p.relay0
                p.relay1 = not p.relay1
                p.relay2 = not p.relay2
                p.relay3 = not p.relay3
                p.digital_out0 = not p.digital_out0
                p.digital_out1 = not p.digital_out1
                p.digital_out2 = not p.digital_out2
                p.digital_out3 = not p.digital_out3
                p.digital_out4 = not p.digital_out4
                p.digital_out5 = not p.digital_out5
                p.digital_out6 = not p.digital_out6
                p.digital_out7 = not p.digital_out7
                p.digital_out8 = not p.digital_out8
                p.digital_out9 = not p.digital_out9
                p.digital_out10 = not p.digital_out10
                p.digital_out11 = not p.digital_out11

            else:
                for i in range(0, 45, 1):
                    print("")
                print("")
                print("Communication error, the data from the microcontroller is not correct!")
                print("Leaving the application. Please check that the Raspberry Pi can communicate")
                print("with the microcontroller on the PiXtend V2 -L- board.")
                print("")
                
                p.digital_out0 = p.OFF
                p.digital_out1 = p.OFF
                p.digital_out2 = p.OFF
                p.digital_out3 = p.OFF
                p.digital_out4 = p.OFF
                p.digital_out5 = p.OFF
                p.digital_out6 = p.OFF
                p.digital_out7 = p.OFF
                p.digital_out8 = p.OFF
                p.digital_out9 = p.OFF
                p.digital_out10 = p.OFF
                p.digital_out11 = p.OFF
                p.relay0 = p.OFF
                p.relay1 = p.OFF
                p.relay2 = p.OFF
                p.relay3 = p.OFF
                p.close()
                del p
                p = None
                break
                
            # Wait some time, SPI communication will continue in the background
            time.sleep(1)

        except KeyboardInterrupt:
            # Keyboard interrupt caught, Ctrl + C, now clean up and leave program
            for i in range(0, 45, 1):
                print("")
            print(strSlogan2)
            
            p.digital_out0 = p.OFF
            p.digital_out1 = p.OFF
            p.digital_out2 = p.OFF
            p.digital_out3 = p.OFF
            p.digital_out4 = p.OFF
            p.digital_out5 = p.OFF
            p.digital_out6 = p.OFF
            p.digital_out7 = p.OFF
            p.digital_out8 = p.OFF
            p.digital_out9 = p.OFF
            p.digital_out10 = p.OFF
            p.digital_out11 = p.OFF
            p.relay0 = p.OFF
            p.relay1 = p.OFF
            p.relay2 = p.OFF
            p.relay3 = p.OFF
            p.close()
            del p
            p = None
            break
