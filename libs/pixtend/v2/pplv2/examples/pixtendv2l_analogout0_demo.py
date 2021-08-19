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
# Import PiXtend V2 class
from pixtendv2l import PiXtendV2L
import time
import sys

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOTE: This example will not work if the CAN-Bus is active!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Setup: Connect a measuring device to Analog Output 0, a Multimeter for
#        example. Connect the AO0 lead and the GND lead to the meter.
#        Set the meter to Volts DC, then run this program. Watch the
#        screen of the meter and how it changes over time.

# -----------------------------------------------------------------
# Create instance - SPI communication starts automatically
# -----------------------------------------------------------------
# PiXtend V2 -L- with DAC, Analog Output active, default/factory setting
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

                # Initial setting, analog output 0 is set to 0
                if not is_config:
                    is_config = True
                    p.analog_out0 = 0
                   
                # Set AO0 to 100 units, about 1 volt
                if 0 <= cycle_counter <= 10:
                    p.analog_out0 = 100
                # Set AO0 to 255 units, around 2.5 volts
                elif 11 <= cycle_counter <= 20:
                    p.analog_out0 = 255
                # Set AO0 to 411 units, around 5 volts
                elif 21 <= cycle_counter <= 30:
                    p.analog_out0 = 511
                # Set AO0 to 888 units, around 8 volts
                elif 31 <= cycle_counter <= 40:
                    p.analog_out0 = 888
                # Set AO0 to 1023 units, 10 volts
                elif 41 <= cycle_counter <= 50:
                    p.analog_out0 = 1023
                else:
                    # If the counter goes over 60 seconds, reset counter to 0
                    if cycle_counter > 60:
                        cycle_counter = 0

            else:
                # On error we leave the program
                time.sleep(0.25)
                # Close SPI bus
                p.close()
                # Delete instance from memory
                del p
                p = None
                break
                
            # Wait some time, SPI communication will continue in the background
            time.sleep(1)

        # Catch errors and if an error is caught, leave the program
        except IOError as e:
            # Print out the caught error and leave program
            print ("I/O error({0}): {1}".format(e.errno, e.strerror))
            # Set AO0 to 0
            p.analog_out0 = 0
            # Wait
            time.sleep(0.25)
            # Close SPI bus
            p.close()
            # Delete instance from memory
            del p
            p = None
            break
            
        except ValueError as ve:
            # Print out the caught error and leave program
            print ("Value error({0}): {1}".format(ve.errno, ve.strerror))
            # Set AO0 to 0
            p.analog_out0 = 0
            # Wait
            time.sleep(0.25)
            # Close SPI bus
            p.close()
            # Delete instance from memory
            del p
            p = None
            break

        except RuntimeError as re:
            # Print out the caught error and leave program
            print ("Runtime error({0}): {1}".format(re.errno, re.strerror))
            # Set AO0 to 0
            p.analog_out0 = 0
            # Wait
            time.sleep(0.25)
            # Close SPI bus
            p.close()
            # Delete instance from memory
            del p
            p = None
            break           

        except KeyboardInterrupt:
            # Keyboard interrupt caught, Ctrl + C, now clean up and leave program
            # Set AO0 to 0
            p.analog_out0 = 0
            # Wait
            time.sleep(0.25)
            # Close SPI bus
            p.close()
            # Delete instance from memory
            del p
            p = None
            break
