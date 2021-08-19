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

# -----------------------------------------------------------------
# Create instance - SPI communication starts automatically
# -----------------------------------------------------------------
# PiXtend V2 -L- with DAC, Analog Output active, default/factory setting
p = PiXtendV2L()

# PiXtend V2 -L- with CAN-Bus active, physical jumper set from AO to CAN,
# the DAC device in the PPLv2 has to be disabled. Comment out the above line
# and comment in the line below to be able to use the CAN-Bus along side or
# from within Python. This requires PPLv2 Version 0.1.4 or later.
#p = PiXtendV2L(disable_dac=True)

if p is not None:
    is_config = False
    # Set some variables needed in the main loop
    cycle_counter = 0
    p.pwm1a = 0
    
    while True:
        try:
            # Check if SPI communication is running and the received data is correct
            if p.crc_header_in_error is False and p.crc_data_in_error is False:
                cycle_counter += 1
                print ("cycle_counter: %s" % (cycle_counter))
                
                #If this is the first run, configure the PWM 1 channel A
                if not is_config:
                    is_config = True
                    # Mode: Duty-Cycle, Freq: 2 kHz, Dyte-Cycle 50% - 100%, Chan: A = On
                    # Bit 0 - Mode0      = 1
                    # Bit 1 - Mode1      = 0
                    # Bit 2 - Reserved   = 0
                    # Bit 3 - EnableA    = 1
                    # Bit 4 - EnableB    = 0
                    # Bit 5 - Prescaler0 = 1
                    # Bit 6 - Prescaler1 = 0
                    # Bit 7 - Prescaler2 = 0
                    # => 41                    
                    p.pwm1_ctrl0 = 41
                    # 16.000.000 / 2 / 1 / 4000 = 2000 Hz
                    # 4000 Steps
                    p.pwm1_ctrl1 = 4000
                
                if cycle_counter <= 1:
                    p.pwm1a = 2000
                    print("2000 - 50%")
                if cycle_counter == 6:
                    p.pwm1a = 3000
                    print("3000 - 75%")                
                if cycle_counter == 16:
                    p.pwm1a = 4000
                    print("4000 - 100%")
                if cycle_counter >= 18 and cycle_counter < 20:
                    p.pwm1a = 0
                    print("0")
                if cycle_counter >= 20:
                    cycle_counter = 0
                    
            # Wait some time for the next loop
            time.sleep(5)
        except KeyboardInterrupt:
            # Leaving the program, turn off the PWM
            p.pwm1_ctrl0 = 0
            # Set PWM value to 0
            p.pwm1a = 0        
            # Wait
            time.sleep(0.25)
            p.close()
            p = None
            break
