#!/usr/bin/env python
# coding=utf-8

# MIT License
# 
# Copyright (C) 2021 Kontron Electronics GmbH <support@pixtend.de>
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
# 
# For further details see LICENSE.txt.

# -----------------------------------------------------------------------------
# Attention:
# The PiXtend Python Library v2 (PPLv2) was developed as a Python 
# library / module to make use of the inheritance functionality of Python.
# However, since the library must access the hardware based SPI bus on the
# Raspberry Pi only ONE single instance of the PiXtendV2S or PiXtendV2L
# class per PiXtend is allowed! The PPLv2 as well as the SPI bus is not 
# capable of aggregating (multiplexing) multiple instances of either
# PiXtend class. Please keep this in mind when developing your application.
# We suggest building one central program which creates the PiXtend object
# and all other programs, functions, threads use inter-process communication
# with the main program to send data to the PiXtend board to manipulate the
# analog and/or digital outputs or to get information from the inputs.
# -----------------------------------------------------------------------------

from __future__ import print_function
# Import Pixtend V2 -S- class
from pixtendv2s import PiXtendV2S
import paho.mqtt.client as mqtt
import time, os, urlparse, sys, re

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    # We subcribe to the topics /pixtendv2/relX and wait for the user to update
    # the one of the topics with a message containing a 1 to turn on a relay or
    # a 0 to turn a relay off.
    client.subscribe("/pixtendv2/rel0")
    client.subscribe("/pixtendv2/rel1")
    client.subscribe("/pixtendv2/rel2")
    client.subscribe("/pixtendv2/rel3")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    if ((len(msg.topic) == 15) and (msg.topic[:len(msg.topic)-1] == "/pixtendv2/rel")):
        try:
            relnum = int(msg.topic[-1:])
            try:
                value = bool(int(msg.payload))
                if (value is False or value is True):
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

strSlogan1 = "PiXtend V2 -S- Python Library and MQTT Demo."
strSlogan2 = "PiXtend V2 -S- Python Library and MQTT Demo finished."

# -----------------------------------------------------------------
# Print Art and Slogan
# -----------------------------------------------------------------
print("")
print("    ____  _ _  ____                 __   _    _____        _____")
print("   / __ \\(_) |/ / /____  ____  ____/ /  | |  / /__ \\      / ___/")
print("  / /_/ / /|   / __/ _ \\/ __ \\/ __  /   | | / /__/ / ____ \\__ \\ ")
print(" / ____/ //   / /_/  __/ / / / /_/ /    | |/ // __/ /___/__ / / ")
print("/_/   /_//_/|_\\__/\\___/_/ /_/\\__,_/     |___//____/     /____/  ")
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
# Create instance - SPI communication starts automatically
# -----------------------------------------------------------------
p = PiXtendV2S()

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
            # Check if SPI communication is running and the received data is correct
            if p.crc_header_in_error is False and p.crc_data_in_error is False:
                cycle_counter += 1

                if not is_config:
                    is_config = True
                    print("The value False = Off and the value True = On")
                    print("")
                    # Setting the relays to Off (False)
                    p.relay0 = p.OFF
                    p.relay1 = p.OFF
                    p.relay2 = p.OFF
                    p.relay3 = p.OFF

                # Build text with values from all digital outputs und relays
                str_text = "Cycle No.: {0}\n".format(cycle_counter)
                str_text += "Digital Input 0: {0}\n".format(p.digital_in0)
                str_text += "Digital Input 1: {0}\n".format(p.digital_in1)
                str_text += "Digital Input 2: {0}\n".format(p.digital_in2)
                str_text += "Digital Input 3: {0}\n".format(p.digital_in3)
                str_text += "Digital Input 4: {0}\n".format(p.digital_in4)
                str_text += "Digital Input 5: {0}\n".format(p.digital_in5)
                str_text += "Digital Input 6: {0}\n".format(p.digital_in6)
                str_text += "Digital Input 7: {0}\n".format(p.digital_in7)
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
                if toggle_counter >= 10:
                    client.publish("/pixtendv2/digin0", int(p.digital_in0))
                    client.publish("/pixtendv2/digin1", int(p.digital_in1))
                    client.publish("/pixtendv2/digin2", int(p.digital_in2))
                    client.publish("/pixtendv2/digin3", int(p.digital_in3))
                    client.publish("/pixtendv2/digin4", int(p.digital_in4))
                    client.publish("/pixtendv2/digin5", int(p.digital_in5))
                    client.publish("/pixtendv2/digin6", int(p.digital_in6))
                    client.publish("/pixtendv2/digin7", int(p.digital_in7))
                    toggle_counter = 0
                else:
                    toggle_counter += 1

            # Wait 0.5sec or 500ms
            time.sleep(0.5)
            # Overwrite old text on screen
            sys.stdout.write(re.sub(r"[^\s]", " ", str_text))
            # Reset cursor
            for i in range(0, 13, 1):
                sys.stdout.write("\x1b[A")

        # Catch errors and if an error is caught, leave the program
        except IOError as e:
            # Print out the caught error and leave program
            print ("I/O error({0}): {1}".format(e.errno, e.strerror))
            p.close()
            time.sleep(0.25)
            del p
            p = None
            break
            
        except ValueError as ve:
            # Print out the caught error and leave program
            print ("Value error({0}): {1}".format(ve.errno, ve.strerror))
            p.close()
            time.sleep(0.25)
            del p
            p = None
            break

        except RuntimeError as re:
            # Print out the caught error and leave program
            print ("Runtime error({0}): {1}".format(re.errno, re.strerror))
            p.close()
            time.sleep(0.25)
            del p
            p = None
            break 

        except KeyboardInterrupt:
            # Keyboard interrupt caught, Ctrl + C, now clean up and leave program
            client.loop_stop()
            client.disconnect()
            client = None
            for i in range(0, 14, 1):
                print("")
            print(strSlogan2)
            p.digital_out0 = p.OFF
            p.digital_out1 = p.OFF
            p.digital_out2 = p.OFF
            p.digital_out3 = p.OFF
            p.relay0 = p.OFF
            p.relay1 = p.OFF
            p.relay2 = p.OFF
            p.relay3 = p.OFF
            time.sleep(0.25)
            # We must call the close() function to end the communication with the
            # PiXtend V2 -S- microcontroller, this way no error is thrown and we
            # can start this program again right away.
            p.close()
            # We have to wait for the communication to end
            time.sleep(0.25)
            del p
            p = None
            break
else:
    # Close any possible MQTT connection
    client.loop_stop()
    client.disconnect()
    client = None
    p = None
    # If there was an error creating the PiXtend V2 -S- instance, leave the program.
    print("")
    print("There was a problem creating the Pixtend V2 -S- instance. Quitting.")
    print("")
    print(strSlogan2)
