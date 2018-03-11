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
import paho.mqtt.client as mqtt
import time, os, urlparse, sys

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    client.subscribe("/pixtend/rel0")
    client.subscribe("/pixtend/rel1")
    client.subscribe("/pixtend/rel2")
    client.subscribe("/pixtend/rel3")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    if ((len(msg.topic) == 13) and (msg.topic[:len(msg.topic)-1] == "/pixtend/rel")):
        try:
            relnum = int(msg.topic[-1:])
            try:
                value = int(msg.payload)
                if (value == 0 or value == 1):
                    if (relnum == 0):
                            p.relay0 = value
                    elif (relnum == 1):
                            p.relay1 = value
                    elif (relnum == 2):
                            p.relay2 = value
                    elif (relnum == 3):
                            p.relay3 = value
            except ValueError:
                value = 0
        except ValueError:
            relnum = 0

strSlogan1 = "PiXtend Python Library (PPL) demo for MQTT."
strSlogan2 = "PiXtend Python Library (PPL) demo for MQTT finished."

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
    
    
# Setup MQTT Client for publish and subcribe
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.username_pw_set(USERNAME_HERE, PASSWORD_HERE)
client.connect(SERVER_HERE, PORT_HERE, 60)

# Non-Blocking call that processes network traffic, dispatches callbacks
client.loop_start()
 
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
                    print("One time configuration")
                    print("The value 0 = OFF and the value 1 = ON")
                    print("")
                    # Setting the relays and digital outputs with a pattern which can be toggled later.
                    # Side effect the LEDs on the PiXtend board alternate nicely back and forth.
                    p.relay0 = p.OFF
                    p.relay1 = p.OFF
                    p.relay2 = p.OFF
                    p.relay3 = p.OFF

                # Build text with values from all digital outputs und relays
                str_text = "Cycle No.: {0}\n".format(cycle_counter)
                str_text += "Digital Input 0: {0}\n".format(p.digital_input0)
                str_text += "Digital Input 1: {0}\n".format(p.digital_input1)
                str_text += "Digital Input 2: {0}\n".format(p.digital_input2)
                str_text += "Digital Input 3: {0}\n".format(p.digital_input3)
                str_text += "Digital Input 4: {0}\n".format(p.digital_input4)
                str_text += "Digital Input 5: {0}\n".format(p.digital_input5)
                str_text += "Digital Input 6: {0}\n".format(p.digital_input6)
                str_text += "Digital Input 7: {0}\n".format(p.digital_input7)
                str_text += "Relay 0:         {0}\n".format(p.relay0)
                str_text += "Relay 1:         {0}\n".format(p.relay1)
                str_text += "Relay 2:         {0}\n".format(p.relay2)
                str_text += "Relay 3:         {0}\n".format(p.relay3)

                # Print text to console
                print(str_text, end="\r")

                # Reset cursor
                for i in range(0, 13, 1):
                    sys.stdout.write("\x1b[A")

                # MQTT processing...
                if toggle_counter >= 50:
                    client.publish("/pixtend/digin0", p.digital_input0)
                    client.publish("/pixtend/digin1", p.digital_input1)
                    client.publish("/pixtend/digin2", p.digital_input2)
                    client.publish("/pixtend/digin3", p.digital_input3)
                    client.publish("/pixtend/digin4", p.digital_input4)
                    client.publish("/pixtend/digin5", p.digital_input5)
                    client.publish("/pixtend/digin6", p.digital_input6)
                    client.publish("/pixtend/digin7", p.digital_input7)
                    toggle_counter = 0
                else:
                    toggle_counter += 1
            else:
                print("Auto Mode - Communication is not yet up...Please wait...")

            # Wait at minimum 0.1sec or 100ms before getting new values
            time.sleep(0.1)

        except KeyboardInterrupt:
            # Keyboard interrupt caught, Ctrl + C, now clean up and leave program
            client.loop_stop()
            client.disconnect()
            client = None
            p.close()
            p = None
            for i in range(0, 14, 1):
                print("")
            print(strSlogan2)
            break
else:
    # Close any possible MQTT connection
    client.loop_stop()
    client.disconnect()
    client = None
    p = None
    # If there was an error when opening the SPI bus interface, leave the program.
    print("")
    print("There was a problem with the PiXtend communication. Quitting.")
    print("")
    print(strSlogan2)
