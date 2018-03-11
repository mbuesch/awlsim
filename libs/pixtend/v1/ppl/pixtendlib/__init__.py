#!/usr/bin/python
# coding=utf-8
import RPi.GPIO as GPIO
import time
import spidev
import ctypes
import subprocess
import shlex

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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Robin Turner"
__version__ = "0.1.1"

# <editor-fold desc="Region: cTypes definitions into short names">

"""
Use the UINT8 cType to create a one (1) byte length variable, short name c_uint8
"""
c_uint8 = ctypes.c_uint8


"""
Use the UINT16 cType to create a two (2) byte length variable, short version c_uint16
"""
c_uint16 = ctypes.c_uint16

"""
Use the FLOAT type from cTypes and make a short version c_float
"""
c_float = ctypes.c_float

# </editor-fold>

# <editor-fold desc="Region: cType style data fields from structures and unions">


class FlagsBits(ctypes.LittleEndianStructure):
    """
    This class has a field with named bits within one single byte, they will be used later to control/change
    individual bits in one single byte.
    
    :type bit0 : c_uint8
    :type bit1 : c_uint8
    :type bit2 : c_uint8
    :type bit3 : c_uint8
    :type bit4 : c_uint8
    :type bit5 : c_uint8
    :type bit6 : c_uint8
    :type bit7 : c_uint8
    """

    def __init__(self, *args, **kwargs):
        super(FlagsBits, self).__init__(*args, **kwargs)
        self.bit0 = 0
        self.bit1 = 0
        self.bit2 = 0
        self.bit3 = 0
        self.bit4 = 0
        self.bit5 = 0
        self.bit6 = 0
        self.bit7 = 0

    _fields_ = [
        ("bit0", c_uint8, 1),  # asByte & 1
        ("bit1", c_uint8, 1),  # asByte & 2
        ("bit2", c_uint8, 1),  # asByte & 4
        ("bit3", c_uint8, 1),  # asByte & 8
        ("bit4", c_uint8, 1),  # asByte & 16
        ("bit5", c_uint8, 1),  # asByte & 32
        ("bit6", c_uint8, 1),  # asByte & 64
        ("bit7", c_uint8, 1)  # asByte & 128
    ]


class FlagsBits16(ctypes.LittleEndianStructure):
    """
    This class has a field with named bits within one 2 bytes structure (c_uint16 type), they will be used later
    to control/change individual bits in two bytes.
    
    :type bit0 : ctypes.c_ushort
    :type bit1 : ctypes.c_ushort
    :type bit2 : ctypes.c_ushort
    :type bit3 : ctypes.c_ushort
    :type bit4 : ctypes.c_ushort
    :type bit5 : ctypes.c_ushort
    :type bit6 : ctypes.c_ushort
    :type bit7 : ctypes.c_ushort
    :type bit8 : ctypes.c_ushort
    :type bit9 : ctypes.c_ushort
    :type bit10 : ctypes.c_ushort
    :type bit11 : ctypes.c_ushort
    :type bit12 : ctypes.c_ushort
    :type bit13 : ctypes.c_ushort
    :type bit14 : ctypes.c_ushort
    :type bit15 : ctypes.c_ushort
    """

    def __init__(self, *args, **kwargs):
        super(FlagsBits16, self).__init__(*args, **kwargs)
        self.bit0 = 0
        self.bit1 = 0
        self.bit2 = 0
        self.bit3 = 0
        self.bit4 = 0
        self.bit5 = 0
        self.bit6 = 0
        self.bit7 = 0
        self.bit8 = 0
        self.bit9 = 0
        self.bit10 = 0
        self.bit11 = 0
        self.bit12 = 0
        self.bit13 = 0
        self.bit14 = 0
        self.bit15 = 0

    _fields_ = [
        ("bit0", c_uint16, 1),  # asByte & 1
        ("bit1", c_uint16, 1),  # asByte & 2
        ("bit2", c_uint16, 1),  # asByte & 4
        ("bit3", c_uint16, 1),  # asByte & 8
        ("bit4", c_uint16, 1),  # asByte & 16
        ("bit5", c_uint16, 1),  # asByte & 32
        ("bit6", c_uint16, 1),  # asByte & 64
        ("bit7", c_uint16, 1),  # asByte & 128
        ("bit8", c_uint16, 1),  # asByte & 256
        ("bit9", c_uint16, 1),  # asByte & 512
        ("bit10", c_uint16, 1),  # asByte & 1024
        ("bit11", c_uint16, 1),  # asByte & 2048
        ("bit12", c_uint16, 1),  # asByte & 4096
        ("bit13", c_uint16, 1),  # asByte & 8192
        ("bit14", c_uint16, 1),  # asByte & 16384
        ("bit15", c_uint16, 1)  # asByte & 32768
    ]


class Flags(ctypes.Union):
    """
    A class using the ctypes Union to combine the 8 bits from the FlagsBits class (field) and one byte (type c_uint8)
    into one memory space overlaying each other. This way each single bit within a byte can be accessed directly by
    its individual name. Using the asBytes field element allows to set all 8 bits at once.   
    
    :type b : FlagsBits
    :type asByte : c_uint8
    """

    def __init__(self, *args, **kwargs):
        super(Flags, self).__init__(*args, **kwargs)
        self.b = FlagsBits()
        self.asByte = 0

    _fields_ = [
        ("b", FlagsBits),
        ("asByte", c_uint8)
    ]


class AnalogValueBytes(ctypes.Structure):
    """
    This is a structure for two (2) single bytes to split up a 16 bit / 2 bytes data type. This class can be used
    in a Union.
    
    :type byte0 : c_uint8
    :type byte1 : c_uint8
    """

    def __init__(self, *args, **kwargs):
        super(AnalogValueBytes, self).__init__(*args, **kwargs)
        self.byte0 = c_uint8(0)
        self.byte1 = c_uint8(0)

    _fields_ = [
        ("byte0", c_uint8),
        ("byte1", c_uint8)
    ]


class AnalogValue(ctypes.Union):
    """
    Union from ctypes to combine the AnalogValueBytes structure with a C_UINT16 type to make a double byte
    memory area. This memory can then be accessed via the C_UINT16 (asUint16) field or via 2 individual named
    bytes from the structure AnalogValueBytes.
    
    :type bytes : AnalogValueBytes
    :type asUint16 : c_uint16
    """

    def __init__(self, *args, **kwargs):
        super(AnalogValue, self).__init__(*args, **kwargs)
        self.bytes = AnalogValueBytes()
        self.asUint16 = c_uint16(0)

    _fields_ = [
        ("bytes", AnalogValueBytes),
        ("asUint16", c_uint16)
    ]


class Flags16(ctypes.Union):
    """
    Union from ctypes to combine a 16 bits structure with a C_UINT16 type to make a two byte memory space
    for the SPI data which will be sent to the DAC via SPI Master 0 and Chip Select 1.

    :type bits : FlagsBits16
    :type asUint16 : c_uint16
    """

    def __init__(self, *args, **kwargs):
        super(Flags16, self).__init__(*args, **kwargs)
        self.bits = FlagsBits16()
        self.asUint16 = c_uint16(0)

    _fields_ = [
        ("bits", FlagsBits16),
        ("asUint16", c_uint16)
    ]


class UcVersionBytes(ctypes.Structure):
    """
    This is a structure for two (2) single bytes to store the firmware version and the board version reported by the
    microcontroller on the PiXtend board.
    
    Example:
    UC_VERSIONH = 13 means board version is 1.3.x
    UC_VERSIONL = 2 means firmware version 2.x is installed on the  microcontroller
    
    :type UC_VERSIONL : c_uint8
    :type UC_VERSIONH : c_uint8
    """

    def __init__(self, *args, **kwargs):
        super(UcVersionBytes, self).__init__(*args, **kwargs)
        self.UC_VERSIONL = c_uint8(0)
        self.UC_VERSIONH = c_uint8(0)

    _fields_ = [
        ("UC_VERSIONL", c_uint8),
        ("UC_VERSIONH", c_uint8)
    ]

# </editor-fold>


class Pixtend(object):
    """
    The PiXtend class derived from Python object can be used to control and manipulate states of inputs and outputs 
    (analog and digital) in the microcontroller on the PiXtend board via the Raspberry Pi's SPI bus.

    Import the pixtend file:           from pixtendlib import Pixtend
    Creating an instance:              p = Pixtend()
    Activate the SPI bus:              p.open()
    Read relay 0 state:                mystate = p.relay0
    Set relay 1 to on:                 p.relay1 = p.ON
    """

    # <editor-fold desc="Global class defines">

    # Global class defines
    PIXTEND_MAX_RELAYS = 4
    PIXTEND_MC_RESET_PIN = 23
    PIXTEND_SPI_ENABLE_PIN = 24
    PIXTEND_SERIAL_PIN = 18
    PIXTEND_SPI_NOT_FOUND = -1
    PIXTEND_SPI_NULL_BYTE = 0b00000000
    PIXTEND_SPI_HANDSHAKE = 0b10101010

    # --------------------------------------
    # 4-Byte Command length
    # --------------------------------------
    PIXTEND_SPI_SET_DOUT = 0b00000001
    PIXTEND_SPI_GET_DIN = 0b00000010
    PIXTEND_SPI_SET_RELAY = 0b00000111
    PIXTEND_SPI_SET_GPIO = 0b00001000
    PIXTEND_SPI_GET_GPIO = 0b00001001
    PIXTEND_SPI_GET_DOUT = 0b00010010
    PIXTEND_SPI_GET_RELAY = 0b00010011
    PIXTEND_SPI_SET_SERVO0 = 0b10000000
    PIXTEND_SPI_SET_SERVO1 = 0b10000001
    PIXTEND_SPI_SET_GPIO_CTRL = 0b10000101
    PIXTEND_SPI_SET_UC_CTRL = 0b10000110
    PIXTEND_SPI_SET_RASPSTAT = 0b10001000
    PIXTEND_SPI_GET_UC_STAT = 0b10001010

    # --------------------------------------
    # 5-Byte Command length
    # --------------------------------------
    PIXTEND_SPI_GET_AIN0 = 0b00000011
    PIXTEND_SPI_GET_AIN1 = 0b00000100
    PIXTEND_SPI_GET_AIN2 = 0b00000101
    PIXTEND_SPI_GET_AIN3 = 0b00000110
    PIXTEND_SPI_GET_TEMP0 = 0b00001010
    PIXTEND_SPI_GET_TEMP1 = 0b00001011
    PIXTEND_SPI_GET_TEMP2 = 0b00001100
    PIXTEND_SPI_GET_TEMP3 = 0b00001101
    PIXTEND_SPI_GET_HUM0 = 0b00001110
    PIXTEND_SPI_GET_HUM1 = 0b00001111
    PIXTEND_SPI_GET_HUM2 = 0b00010000
    PIXTEND_SPI_GET_HUM3 = 0b00010001
    PIXTEND_SPI_SET_PWM0 = 0b10000010
    PIXTEND_SPI_SET_PWM1 = 0b10000011
    PIXTEND_SPI_SET_AI_CTRL = 0b10000111
    PIXTEND_SPI_GET_UC_VER = 0b10001001

    # --------------------------------------
    # 6-Byte Command length
    # --------------------------------------
    PIXTEND_SPI_SET_PWM_CTRL = 0b10000100

    # --------------------------------------
    # Auto Mode - 34 bytes Command length
    # --------------------------------------
    PIXTEND_SPI_AUTO_MODE = 0b11100111

    # --------------------------------------
    # Define types, states and selections
    # --------------------------------------
    ON = 1
    OFF = 0
    RS232 = False
    RS485 = True
    DAC_A = 0
    DAC_B = 1
    SERVO_MODE = 0
    PWM_MODE = 1
    GPIO_OUTPUT = 1
    GPIO_INPUT = 0
    JUMPER_5V = 0
    JUMPER_10V = 1
    BIT_0 = 0
    BIT_1 = 1
    BIT_2 = 2
    BIT_3 = 3
    BIT_4 = 4
    BIT_5 = 5
    BIT_6 = 6
    BIT_7 = 7
    BIT_8 = 8
    BIT_9 = 9
    BIT_10 = 10
    BIT_11 = 11
    BIT_12 = 12
    BIT_13 = 13
    BIT_14 = 14
    BIT_15 = 15

    # </editor-fold>

    def __init__(self):
        """
        Constructor of the Pixtend class.
        Create all objects and variables needed, set defaults for the RPi SPI bus, the GPIOs and activate
        the BCM GPIO layout on the Raspberry Pi. The GPIO 24 needs to be an output and set to 'on' to enable
        the communication with the microcontroller on the PiXtend board via SPI Master 0 and Chip Select 0.
        """

        # Default SPI frequency is 100kHz
        self.__spi_speed = 100000
        # The microcontroller is on the SPI Master 0 with CS 0
        self.__spi_channel = 0
        self.__spi_cs = 0
        self.__spi = None
        self.__spi_dac = None

        # Initialize variables
        self.__use_fahrenheit = False
        self.__is_automatic_mode_active = False
        self.__is_spi_open = False
        self.__is_spi_dac_open = False
        self.__max_relay_bits = self.PIXTEND_MAX_RELAYS
        self.__relays_states = 0
        self.__digital_inputs_states = 0
        self.__digital_outputs_states = 0
        self.__gpio_states_manual = 0
        self.__gpio_states_auto_in = 0
        self.__gpio_states_auto_out = 0
        self.__gpio_ctrl = 0
        self.__servo0_value = c_uint8(0)
        self.__servo1_value = c_uint8(0)
        self.__pwm0_value = AnalogValue()
        self.__pwm1_value = AnalogValue()
        self.__pwm_ctrl0 = Flags()
        self.__pwm_ctrl1 = Flags()
        self.__pwm_ctrl2 = Flags()
        self.__pwm_period = AnalogValue()
        self.__analog_dac_value = Flags16()
        self.__uc_version = UcVersionBytes()
        self.__uc_status = c_uint8(0)
        self.__uc_ctrl = Flags()
        self.__ai_ctrl0 = Flags()
        self.__ai_ctrl1 = Flags()
        self.__pi_status = Flags()
        self.__analog_value = AnalogValue()
        self.__ai0_jumper_setting_10_volts = 0
        self.__ai1_jumper_setting_10_volts = 0
        self.__ai0_raw_value = AnalogValue()
        self.__ai1_raw_value = AnalogValue()
        self.__ai2_raw_value = AnalogValue()
        self.__ai3_raw_value = AnalogValue()
        self.__temp0_raw_value = AnalogValue()
        self.__temp1_raw_value = AnalogValue()
        self.__temp2_raw_value = AnalogValue()
        self.__temp3_raw_value = AnalogValue()
        self.__humid0_raw_value = AnalogValue()
        self.__humid1_raw_value = AnalogValue()
        self.__humid2_raw_value = AnalogValue()
        self.__humid3_raw_value = AnalogValue()
        self.__ai0_value = c_float(0.0)
        self.__ai1_value = c_float(0.0)
        self.__ai2_value = c_float(0.0)
        self.__ai3_value = c_float(0.0)
        self.__temp0_value = c_float(0.0)
        self.__temp1_value = c_float(0.0)
        self.__temp2_value = c_float(0.0)
        self.__temp3_value = c_float(0.0)
        self.__humid0_value = c_float(0.0)
        self.__humid1_value = c_float(0.0)
        self.__humid2_value = c_float(0.0)
        self.__humid3_value = c_float(0.0)
        self.__analog0_dac_value = Flags16()
        self.__analog1_dac_value = Flags16()
        
        # Turn RPi GPIO warnings off in case GPIOs are still/already in use
        GPIO.setwarnings(False)
        # Change layout to BCM
        GPIO.setmode(GPIO.BCM)
        # Set SPI Enable pin to output
        GPIO.setup(self.PIXTEND_SPI_ENABLE_PIN, GPIO.OUT)
        GPIO.setup(self.PIXTEND_MC_RESET_PIN, GPIO.OUT)
        GPIO.setup(self.PIXTEND_SERIAL_PIN, GPIO.OUT)
        # Activate SPI Enable, allow communication
        GPIO.output(self.PIXTEND_SPI_ENABLE_PIN, True)
        # Turn microcontroller reset pin off
        GPIO.output(self.PIXTEND_MC_RESET_PIN, False)
        # Set serial mode to RS232
        GPIO.output(self.PIXTEND_SERIAL_PIN, False)

    @staticmethod
    def __dump(obj):
        for attr in dir(obj):
            if hasattr(obj, attr):
                print("obj.%s = %s" % (attr, getattr(obj, attr)))

    def __del__(self):
        """
        Destructor of the Pixtend class.
        Delete all objects, clean up GPIOs and close the SPI bus when the Pixtend instance is destroyed.
        """

        self.__use_fahrenheit = False
        self.__is_automatic_mode_active = False
        try:
            del self.__relays_states
        except:
            pass
        try:
            del self.__digital_inputs_states
        except:
            pass
        try:
            del self.__digital_outputs_states
        except:
            pass
        try:
            del self.__analog_value
        except:
            pass
        try:
            del self.__gpio_states_manual
        except:
            pass
        try:
            del self.__gpio_states_auto_in
        except:
            pass
        try:
            del self.__gpio_states_auto_out
        except:
            pass
        try:
            del self.__servo0_value
        except:
            pass
        try:
            del self.__servo1_value
        except:
            pass
        try:
            del self.__pwm0_value
        except:
            pass
        try:
            del self.__pwm1_value
        except:
            pass
        try:
            del self.__pwm_ctrl0
        except:
            pass
        try:
            del self.__pwm_ctrl1
        except:
            pass
        try:
            del self.__pwm_ctrl2
        except:
            pass
        try:
            del self.__pwm_period
        except:
            pass
        try:
            del self.__analog_dac_value
        except:
            pass
        try:
            del self.__uc_ctrl
        except:
            pass
        try:
            del self.__ai_ctrl0
        except:
            pass
        try:
            del self.__ai_ctrl1
        except:
            pass
        try:
            del self.__pi_status
        except:
            pass
        try:
            del self.__ai0_jumper_setting_10_volts
        except:
            pass
        try:
            del self.__ai1_jumper_setting_10_volts
        except:
            pass
        try:
            del self.__ai0_raw_value
        except:
            pass
        try:
            del self.__ai1_raw_value
        except:
            pass
        try:
            del self.__ai2_raw_value
        except:
            pass
        try:
            del self.__ai3_raw_value
        except:
            pass
        try:
            del self.__temp0_raw_value
        except:
            pass
        try:
            del self.__temp1_raw_value
        except:
            pass
        try:
            del self.__temp2_raw_value
        except:
            pass
        try:
            del self.__temp3_raw_value
        except:
            pass
        try:
            del self.__humid0_raw_value
        except:
            pass
        try:
            del self.__humid1_raw_value
        except:
            pass
        try:
            del self.__humid2_raw_value
        except:
            pass
        try:
            del self.__humid3_raw_value
        except:
            pass
        try:
            del self.__ai0_value
        except:
            pass
        try:
            del self.__ai1_value
        except:
            pass
        try:
            del self.__ai2_value
        except:
            pass
        try:
            del self.__ai3_value
        except:
            pass
        try:
            del self.__temp0_value
        except:
            pass
        try:
            del self.__temp1_value
        except:
            pass
        try:
            del self.__temp2_value
        except:
            pass
        try:
            del self.__temp3_value
        except:
            pass
        try:
            del self.__humid0_value
        except:
            pass
        try:
            del self.__humid1_value
        except:
            pass
        try:
            del self.__humid2_value
        except:
            pass
        try:
            del self.__humid3_value
        except:
            pass
        try:
            del self.__analog0_dac_value
        except:
            pass
        try:
            del self.__analog1_dac_value
        except:
            pass

        try:
            GPIO.cleanup()
        except:
            pass
        
        if self.__is_spi_open:
            try:
                self.__spi.close()
            except:
                pass
            self.__spi = None
            self.__is_spi_open = False

        if self.__is_spi_dac_open:
            try:
                self.__spi_dac.close()
            except:
                pass
            self.__spi_dac = None
            self.__is_spi_dac_open = False

        try:
            del self.__spi
        except:
            pass
        try:
            del self.__spi_dac
        except:
            pass
        try:
            del self.__is_spi_open
        except:
            pass
        try:
            del self.__is_spi_dac_open
        except:
            pass


    def __transfer_spi_data(self, command, value0=0b00000000, value1=0b00000000, value2=0b00000000, auto_data=None):
        """
        Transfer data to microcontroller all in one block, data needs to be passed
        as byte array, the return value is also a byte array / list of the same byte count as was sent
        to the microcontroller.
        
        :param int command: Command for the microcontroller to execute, must be of one of the PIXTEND_SPI_xxx constants
        :param int value0: First byte value needed for 4 byte commands, optional depending on command
        :param int value1: Second byte value needed for 5 byte commands, optional depending on command
        :param int value2: Third byte value needed for 6 byte commands, optional depending on command 
        :param auto_data: Array of bytes to send to the microcontroller in Auto Mode
        :type auto_data: int[] or None
        :return: Array of bytes received from the microcontroller on the PiXtend board
        :rtype: int[]
        :raises Exception: If command does not have one of the allowed PIXTEND_SPI_xxx constants values
        :raises IOError: If SPI bus was not initialized (opened) before use
        """

        # auto_data is mutable, None is used as default, if no parameter gets passed, it is inited as an array.
        if auto_data is None:
            auto_data = [0]

        # <editor-fold desc="Region: Command length decision --> 4, 5 or 6 bytes to transfer">
        if (command == self.PIXTEND_SPI_SET_DOUT) or (command == self.PIXTEND_SPI_GET_DIN) or (
                    command == self.PIXTEND_SPI_SET_RELAY) or (command == self.PIXTEND_SPI_SET_GPIO) or (
                    command == self.PIXTEND_SPI_GET_GPIO) or (command == self.PIXTEND_SPI_GET_DOUT) or (
                    command == self.PIXTEND_SPI_GET_RELAY) or (command == self.PIXTEND_SPI_SET_SERVO0) or (
                    command == self.PIXTEND_SPI_SET_SERVO1) or (command == self.PIXTEND_SPI_SET_GPIO_CTRL) or (
                    command == self.PIXTEND_SPI_SET_UC_CTRL) or (command == self.PIXTEND_SPI_SET_RASPSTAT) or (
                    command == self.PIXTEND_SPI_GET_UC_STAT):
            to_send = [self.PIXTEND_SPI_HANDSHAKE, command, value0, self.PIXTEND_SPI_HANDSHAKE]
        elif (command == self.PIXTEND_SPI_GET_AIN0) or (command == self.PIXTEND_SPI_GET_AIN1) or (
                    command == self.PIXTEND_SPI_GET_AIN2) or (command == self.PIXTEND_SPI_GET_AIN3) or (
                    command == self.PIXTEND_SPI_GET_TEMP0) or (command == self.PIXTEND_SPI_GET_TEMP1) or (
                    command == self.PIXTEND_SPI_GET_TEMP2) or (command == self.PIXTEND_SPI_GET_TEMP3) or (
                    command == self.PIXTEND_SPI_GET_HUM0) or (command == self.PIXTEND_SPI_GET_HUM1) or (
                    command == self.PIXTEND_SPI_GET_HUM2) or (command == self.PIXTEND_SPI_GET_HUM3) or (
                    command == self.PIXTEND_SPI_SET_PWM0) or (command == self.PIXTEND_SPI_SET_PWM1) or (
                    command == self.PIXTEND_SPI_SET_AI_CTRL) or (command == self.PIXTEND_SPI_GET_UC_VER):
            to_send = [self.PIXTEND_SPI_HANDSHAKE, command, value0, value1, self.PIXTEND_SPI_NULL_BYTE]
        elif command == self.PIXTEND_SPI_SET_PWM_CTRL:
            to_send = [self.PIXTEND_SPI_HANDSHAKE, command, value0, value1, value2, self.PIXTEND_SPI_NULL_BYTE]
        elif command == self.PIXTEND_SPI_AUTO_MODE:
            to_send = auto_data
        else:
            raise Exception("__transfer_spi_data --> PIXTEND SPI command unknown!!!")
        # </editor-fold>

        if self.__is_spi_open:
            resp = self.__spi.xfer2(to_send)  # transfer byte data in one block with cs always active during transfer
        else:
            raise IOError("SPI not initialized!!! Use open method first!", "Method __transfer_spi_data was called!")

        return resp

    def __transfer_spi_dac_data(self, value0=0, value1=0):
        """
        Transfer data to the DAC on the PiXtend board all in one block, the DAC does not return anything.
        The DAC expects 2 bytes in a special format, see MCP4812 manual for more details.
        
        :param int value0: First byte for the DAC
        :param int value1: Second byte for the DAC
        """

        # Build data array to send to the DAC.
        to_send = [value0, value1]

        if self.__is_spi_dac_open:
            # transfer byte data in one block with cs always active during transfer
            resp = self.__spi_dac.xfer2(to_send)
        else:
            raise IOError("SPI for DAC not initialized!!! Use open_dac method first!",
                          "Method __transfer_spi_dac_data was called!")

        return resp

    def __reset_microcontroller(self):
        """
        DO NOT USE DURING NORMAL OPERATION - Internal function to reset the MC for testing
        """

        GPIO.output(self.PIXTEND_MC_RESET_PIN, True)
        time.sleep(1)
        GPIO.output(self.PIXTEND_MC_RESET_PIN, False)
        time.sleep(1)

    def open(self, spi_channel=0, spi_cs=0, spi_speed=100000):
        """
        Open SPI Master 0 with Chip Select 0 on the Raspberry Pi to start the communication with the microcontroller
        on the PiXtend board.
        
        :param int spi_channel: Number of the SPI master, default is 0, optional parameter
        :param int spi_cs:  Chip Select (CS) for the SPI master, default is 0, optional parameter
        :param int spi_speed:  SPI frequency, default 100 kHz, optional parameter
        :raises IOError: If SPI bus has already been opened
        """

        self.__spi_channel = spi_channel
        self.__spi_cs = spi_cs
        self.__spi_speed = spi_speed

        # Open SPI bus
        if not self.__is_spi_open:
            self.__spi = spidev.SpiDev(self.__spi_channel, self.__spi_cs)
            self.__spi.open(self.__spi_channel, self.__spi_cs)
            self.__spi.max_speed_hz = self.__spi_speed
            self.__is_spi_open = True
            # Get the current board and firmware version right away
            self.__uc_version_get()
        else:
            raise IOError("Error: SPI 0 CS 0 already opened!")

    def open_dac(self, spi_channel=0, spi_cs=1, spi_speed=100000):
        """
        Open SPI Master 0 with Chip Select 1 on the Raspberry Pi to start the communication
        with the DAC on the PiXtend board.
        
        :param int spi_channel: Number of the SPI master, default is 0, optional parameter
        :param int spi_cs: Chip Select (CS) for the SPI master for the DAC, default is 1, optional parameter
        :param int spi_speed: SPI frequency, default 100 kHz, optional parameter
        :raises IOError: If SPI bus has already been opened
        """

        self.__spi_channel = spi_channel
        self.__spi_cs = spi_cs
        self.__spi_speed = spi_speed

        # Set the dac gain permanently to 0
        # 0 = 2x (VOUT = 2 * VREF * D/4096),  where internal VREF = 2.048V.
        self.__analog_dac_value.bits.bit1 = 0

        # Set the dac output shutdown control bit permanently to 1
        # 1 = Active mode operation. VOUT is available.
        self.__analog_dac_value.bits.bit2 = 1

        # Open SPI bus
        if not self.__is_spi_dac_open:
            self.__spi_dac = spidev.SpiDev(self.__spi_channel, self.__spi_cs)
            self.__spi_dac.open(self.__spi_channel, self.__spi_cs)
            self.__spi_dac.max_speed_hz = self.__spi_speed
            self.__is_spi_dac_open = True
        else:
            raise IOError("SPI 0 CS 1 already opened!!!")

    def close(self):
        """
        Close SPI device, clean up Raspberry Pi GPIO device and set all variables to None.
        """
        try:
            self.__is_automatic_mode_active = None
            self.__use_fahrenheit = None
            self.__relays_states = None
            self.__digital_inputs_states = None
            self.__digital_outputs_states = None
            self.__analog_value = None
            self.__gpio_states_manual = None
            self.__gpio_states_auto_in = None
            self.__gpio_states_auto_out = None
            self.__servo0_value = None
            self.__servo1_value = None
            self.__pwm0_value = None
            self.__pwm1_value = None
            self.__pwm_ctrl0 = None
            self.__pwm_ctrl1 = None
            self.__pwm_ctrl2 = None
            self.__pwm_period = None
            self.__analog_dac_value = None
            self.__uc_ctrl = None
            self.__ai_ctrl0 = None
            self.__ai_ctrl1 = None
            self.__pi_status = None
            self.__ai0_jumper_setting_10_volts = None
            self.__ai1_jumper_setting_10_volts = None
            self.__ai0_raw_value = None
            self.__ai1_raw_value = None
            self.__ai2_raw_value = None
            self.__ai3_raw_value = None
            self.__temp0_raw_value = None
            self.__temp1_raw_value = None
            self.__temp2_raw_value = None
            self.__temp3_raw_value = None
            self.__humid0_raw_value = None
            self.__humid1_raw_value = None
            self.__humid2_raw_value = None
            self.__humid3_raw_value = None
            self.__ai0_value = None
            self.__ai1_value = None
            self.__ai2_value = None
            self.__ai3_value = None
            self.__temp0_value = None
            self.__temp1_value = None
            self.__temp2_value = None
            self.__temp3_value = None
            self.__humid0_value = None
            self.__humid1_value = None
            self.__humid2_value = None
            self.__humid3_value = None
            self.__analog0_dac_value = None
            self.__analog1_dac_value = None
        except:
            pass

        try:
            GPIO.cleanup()
        except:
            pass
        
        if self.__is_spi_open:
            try:
                self.__spi.close()
            except:
                pass
            self.__spi = None
            self.__is_spi_open = None

        if self.__is_spi_dac_open:
            try:
                self.__spi_dac.close()
            except:
                pass
            self.__spi_dac = None
            self.__is_spi_dac_open = None

    # <editor-fold desc="Region: Microcontroller Control Register, Version and Status">

    # **************************************************************************
    # Microcontroller Control Register, Version and Status
    # **************************************************************************

    def __uc_control_register_set(self, value):
        """
        Write one byte of data to the microcontroller's control register. See PiXtend manuals and AppNotes
        for more information on this topic. http://www.pixtend.de/files/manuals/AppNote_PiXtend_Control_Status_Bytes.pdf
        can be a good start.

        :param c_uint8 value: data to write to the microcontroller's control register
        """

        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_UC_CTRL, value)

    def __uc_status_register_get(self):
        """
        Get the microcontroller's status register via SPI.

        :return: The value received from the microcontroller 
        :rtype: c_uint8
        """

        # If the automatic mode is active, the data transfer is all done in the auto_mode method.
        if not self.__is_automatic_mode_active:
            value = self.__transfer_spi_data(self.PIXTEND_SPI_GET_UC_STAT)
            if len(value) >= 3:
                self.__uc_status = value[3]
            else:
                self.__uc_status = 0

        return self.__uc_status

    def __uc_version_get(self):
        """
        Get the board and firmware version from the microcontroller on the PiXtend board.
        """

        # Only do the transfer if automatic mode is off
        if not self.__is_automatic_mode_active:
            value = self.__transfer_spi_data(self.PIXTEND_SPI_GET_UC_VER)

            if len(value) >= 4:
                self.__uc_version.UC_VERSIONL = value[3]
                self.__uc_version.UC_VERSIONH = value[4]

    @property
    def uc_status(self):
        """
        Get the microcontroller status byte.
        
        :return: Status byte of the microcontroller on the PiXtend board
        :rtype: c_uint8
        """

        return self.__uc_status_register_get()

    @property
    def uc_board_version(self):
        """
        Get the PiXtend board version.
        
        Example:
        A value of 13 means board version 1.3.x

        :return: Board version of the PiXtend board
        :rtype: c_uint8
        """

        # If the automatic mode is off, the board version will be fetched via SPI.
        if not self.__is_automatic_mode_active:
            self.__uc_version_get()
        return self.__uc_version.UC_VERSIONH

    @property
    def uc_fw_version(self):
        """
        Get the microcontroller firmware version on the PiXtend board.
        
        Example:
        A value of 2 means firmware version 2.x is installed on the microcontroller

        :return: Firmware version of the microcontroller on the PiXtend board
        :rtype: c_uint8
        """

        # If the automatic mode is off, the firmware version will be fetched via SPI.
        if not self.__is_automatic_mode_active:
            self.__uc_version_get()
        return self.__uc_version.UC_VERSIONL

    @property
    def uc_control(self):
        """
        Get or Set the microcontroller's control register. If the automatic mode is off, setting
        a new value will have immediate effect.

        :return: Current value of the control byte in the microcontroller
        :rtype: c_uint8
        :raises ValueError: If the passed value is smaller then 0 or larger then 255
        """

        return self.__uc_ctrl.asByte

    @uc_control.setter
    def uc_control(self, value):
        if value >= 0 or value <= 255:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 to 255")
        self.__uc_ctrl.asByte = value
        self.__uc_control_register_set(value)

    # </editor-fold>

    # <editor-fold desc="Region: GPIO Control, GPIO configuration, Settings for DHT11/22 on/off, GPIO value In/Out">

    # **************************************************************************
    # GPIO Control - GPIO In/Out - DHT11/22 Settings
    # **************************************************************************

    def __gpio_ctrl_set(self, value):
        """
        Set the PiXtend GPIO control register to the value of 'value'.
        """

        # If the automatic mode is active, the data transfer is all done in the auto_mode method.
        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_GPIO_CTRL, value)

    def __gpio_ctrl_change_value(self, value, bit_num):
        """
        Change one bit within the INT variable __gpio_ctrl based on value and bit_num.
        If value == 0 the bit at position bit_num is cleared, if value == 1 then the bit at position
        bit_num is set.
        
        :param int value: Value of the bit, 0 = off and 1 = on
        :param int bit_num: Bit to set or to clear, parameter is zero based 
        """

        if value == 0:
            self.__gpio_ctrl = self.__clear_bit(self.__gpio_ctrl, bit_num)
        if value == 1:
            self.__gpio_ctrl = self.__set_bit(self.__gpio_ctrl, bit_num)

        self.__gpio_ctrl_set(self.__gpio_ctrl)

    @property
    def gpio0_direction(self):
        """
        Get or Set the direction of GPIO 0, input or output is possible.
          
        Example:
        p.gpio0_direction = p.GPIO_INPUT
        p.gpio0_direction = p.GPIO_OUTPUT
        
        or
        
        p.gpio0_direction = 0 # Input
        p.gpio0_direction = 1 # Output
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_0)

    @gpio0_direction.setter
    def gpio0_direction(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = Input, 1 = Output")
        self.__gpio_ctrl_change_value(value, self.BIT_0)

    @property
    def gpio1_direction(self):
        """
        Get or Set the direction of GPIO 1, input or output is possible.

        Example:
        p.gpio1_direction = p.GPIO_INPUT
        p.gpio1_direction = p.GPIO_OUTPUT

        or

        p.gpio1_direction = 0 # Input
        p.gpio1_direction = 1 # Output
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_1)

    @gpio1_direction.setter
    def gpio1_direction(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = Input, 1 = Output")
        self.__gpio_ctrl_change_value(value, self.BIT_1)

    @property
    def gpio2_direction(self):
        """
        Get or Set the direction of GPIO 2, input or output is possible.

        Example:
        p.gpio2_direction = p.GPIO_INPUT
        p.gpio2_direction = p.GPIO_OUTPUT

        or

        p.gpio2_direction = 0 # Input
        p.gpio2_direction = 1 # Output
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_2)

    @gpio2_direction.setter
    def gpio2_direction(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = Input, 1 = Output")
        self.__gpio_ctrl_change_value(value, self.BIT_2)

    @property
    def gpio3_direction(self):
        """
        Get or Set the direction of GPIO 3, input or output is possible.

        Example:
        p.gpio3_direction = p.GPIO_INPUT
        p.gpio3_direction = p.GPIO_OUTPUT

        or

        p.gpio3_direction = 0 # Input
        p.gpio3_direction = 1 # Output
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_3)

    @gpio3_direction.setter
    def gpio3_direction(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = Input, 1 = Output")
        self.__gpio_ctrl_change_value(value, self.BIT_3)

    @property
    def dht0(self):
        """
        Get or Set the 1-Wire setting for GPIO 0. Default is 'off' (0), if set to 'on' (1) means 1-wire sensors
        like DHT11, DHT22 and AM2302 can be used at this GPIO. The direction bit (input/output) will be ignored if
        this property is set to 'on' (1).
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_4)

    @dht0.setter
    def dht0(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__gpio_ctrl_change_value(value, self.BIT_4)

    @property
    def dht1(self):
        """
        Get or Set the 1-Wire setting for GPIO 1. Default is 'off' (0), if set to 'on' (1) means 1-wire sensors
        like DHT11, DHT22 and AM2302 can be used at this GPIO. The direction bit (input/output) will be ignored if
        this property is set to 'on' (1).
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_5)

    @dht1.setter
    def dht1(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__gpio_ctrl_change_value(value, self.BIT_5)

    @property
    def dht2(self):
        """
        Get or Set the 1-Wire setting for GPIO 2. Default is 'off' (0), if set to 'on' (1) means 1-wire sensors
        like DHT11, DHT22 and AM2302 can be used at this GPIO. The direction bit (input/output) will be ignored if
        this property is set to 'on' (1).
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_6)

    @dht2.setter
    def dht2(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__gpio_ctrl_change_value(value, self.BIT_6)

    @property
    def dht3(self):
        """
        Get or Set the 1-Wire setting for GPIO 3. Default is 'off' (0), if set to 'on' (1) means 1-wire sensors
        like DHT11, DHT22 and AM2302 can be used at this GPIO. The direction bit (input/output) will be ignored if
        this property is set to 'on' (1).
        """

        return self.__test_bit(self.__gpio_ctrl, self.BIT_7)

    @dht3.setter
    def dht3(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__gpio_ctrl_change_value(value, self.BIT_7)

    def __gpio_states_get(self):
        """
        Get the current GPIO state from the microcontroller on the PiXtend board.
        """

        # Only do SPI data transfer if the Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            value = self.__transfer_spi_data(self.PIXTEND_SPI_GET_GPIO)
            if len(value) >= 3:
                self.__gpio_states_manual = value[3]
            else:
                self.__gpio_states_manual = 0

            self.__gpio_states_auto_in = self.__gpio_states_manual

            return self.__gpio_states_manual
        else:
            return self.__gpio_states_auto_in

    def __gpio_states_set(self, value):
        """
        Set the states of the GPIOs on the PiXtend board.
        """

        resp = self.__transfer_spi_data(self.PIXTEND_SPI_SET_GPIO, value)
        return resp

    def __gpio_states_change_value(self, value, bit_num):
        """
        Change the value of a single bit in the INT variable __gpio_states_manual given by bit_num to the
        value given by value. In Auto Mode the variable __gpio_states_auto_out is used instead.
        
        :param int value: Value of the bit, 0 = off and 1 = on 
        :param int bit_num: Bit to set or to clear, parameter is zero based 
        """

        if not self.__is_automatic_mode_active:
            if value == 0:
                self.__gpio_states_manual = self.__clear_bit(self.__gpio_states_manual, bit_num)
            if value == 1:
                self.__gpio_states_manual = self.__set_bit(self.__gpio_states_manual, bit_num)

            self.__gpio_states_auto_out = self.__gpio_states_manual

            self.__gpio_states_set(self.__gpio_states_manual)
        else:
            if value == 0:
                self.__gpio_states_auto_out = self.__clear_bit(self.__gpio_states_auto_out, bit_num)
            if value == 1:
                self.__gpio_states_auto_out = self.__set_bit(self.__gpio_states_auto_out, bit_num)

    @property
    def gpio0(self):
        """
        Get or Set the state of GPIO 0. The value 0 means 'off' and a value of 1 means 'on'.
        
        Example:
        p.gpio0 = p.ON # Turns the GPIO on
        p.gpio0 = p.OFF # Turns the GPIO off
        or use
        p.gpio0 = 1 # Turns the GPIO on
        p.gpio0 = 0 # Turns the GPIO off
        """

        return self.__test_bit(self.__gpio_states_get(), self.BIT_0)

    @gpio0.setter
    def gpio0(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        bit_num = self.BIT_0
        if self.__test_bit(self.__gpio_ctrl, bit_num) == 1:
            self.__gpio_states_change_value(value, bit_num)
        else:
            raise IOError("IOError: GPIO 0 configured as INPUT! Cannot use as OUTPUT!",
                          "- DirectionBit=" + str(self.__test_bit(self.__gpio_ctrl, bit_num)))

    @property
    def gpio1(self):
        """
        Get or Set the state of GPIO 1. The value 0 means 'off' and a value of 1 means 'on'.
        
        Example:
        p.gpio1 = p.ON # Turns the GPIO on
        p.gpio1 = p.OFF # Turns the GPIO off
        or use
        p.gpio1 = 1 # Turns the GPIO on
        p.gpio1 = 0 # Turns the GPIO off
        """

        return self.__test_bit(self.__gpio_states_get(), self.BIT_1)

    @gpio1.setter
    def gpio1(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        bit_num = self.BIT_1
        if self.__test_bit(self.__gpio_ctrl, bit_num) == 1:
            self.__gpio_states_change_value(value, bit_num)
        else:
            raise IOError("IOError: GPIO 1 configured as INPUT! Cannot use as OUTPUT!",
                          "- DirectionBit=" + str(self.__test_bit(self.__gpio_ctrl, bit_num)))

    @property
    def gpio2(self):
        """
        Get or Set the state of GPIO 2. The value 0 means 'off' and a value of 1 means 'on'.
        
        Example:
        p.gpio2 = p.ON # Turns the GPIO on
        p.gpio2 = p.OFF # Turns the GPIO off
        or use
        p.gpio2 = 1 # Turns the GPIO on
        p.gpio2 = 0 # Turns the GPIO off
        """

        return self.__test_bit(self.__gpio_states_get(), self.BIT_2)

    @gpio2.setter
    def gpio2(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        bit_num = self.BIT_2
        if self.__test_bit(self.__gpio_ctrl, bit_num) == 1:
            self.__gpio_states_change_value(value, bit_num)
        else:
            raise IOError("IOError: GPIO 2 configured as INPUT! Cannot use as OUTPUT!",
                          "- DirectionBit=" + str(self.__test_bit(self.__gpio_ctrl, bit_num)))

    @property
    def gpio3(self):
        """
        Get or Set the state of GPIO 3. The value 0 means 'off' and a value of 1 means 'on'.
        
        Example:
        p.gpio3 = p.ON # Turns the GPIO on
        p.gpio3 = p.OFF # Turns the GPIO off
        or use
        p.gpio3 = 1 # Turns the GPIO on
        p.gpio3 = 0 # Turns the GPIO off
        """

        return self.__test_bit(self.__gpio_states_get(), self.BIT_3)

    @gpio3.setter
    def gpio3(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        bit_num = self.BIT_3
        if self.__test_bit(self.__gpio_ctrl, bit_num) == 1:
            self.__gpio_states_change_value(value, bit_num)
        else:
            raise IOError("IOError: GPIO 3 configured as INPUT! Cannot use as OUTPUT!",
                          "- DirectionBit=" + str(self.__test_bit(self.__gpio_ctrl, bit_num)))

    # </editor-fold>

    # <editor-fold desc="Region: Servo Control ">

    # **************************************************************************
    # Servo Control 
    # **************************************************************************

    @property
    def servo0(self):
        """
        Get or Set the value for PWM 0 in servo mode. Possible values are 0 to 250.
        """

        return self.__servo0_value.value

    @servo0.setter
    def servo0(self, value):
        if 0 <= value <= 250:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 250")
        self.__servo0_value.value = value
        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_SERVO0, self.__servo0_value.value)
        else:
            if self.pwm_ctrl_mode == 0:
                self.__pwm0_value.bytes.byte0 = value
                self.__pwm0_value.bytes.byte1 = 0
            else:
                raise ValueError("Mode error! Servo mode was used, but outputs are set to PWM output.")

    @property
    def servo1(self):
        """
        Get or Set the value for PWM 1 in servo mode. Possible values are 0 to 250.
        """

        return self.__servo1_value.value

    @servo1.setter
    def servo1(self, value):
        if 0 <= value <= 250:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 250")
        self.__servo1_value.value = value
        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_SERVO1, self.__servo1_value.value)
        else:
            if self.pwm_ctrl_mode == 0:
                self.__pwm1_value.bytes.byte0 = value
                self.__pwm1_value.bytes.byte1 = 0
            else:
                raise ValueError("Mode error! Servo mode was used, but outputs are set to PWM output.")

    # </editor-fold>

    # <editor-fold desc="Region: PWM Control">

    # **************************************************************************
    # PWM Control 
    # **************************************************************************
    # Refer to the PiXtend's documentation for the 3 PWM Control registers
    # set_pwm_control: value0 = PWM_CTRL0, value1 = PWM_CTRL1, value2 = PWM_CTRL2

    def __pwm_control_set(self, value0, value1, value2):
        """
        Set the PWM control registers in the microcontroller on the PiXtend board to the values of value0,
        value1 and value2.
        """

        resp = self.__transfer_spi_data(self.PIXTEND_SPI_SET_PWM_CTRL, value0, value1, value2)
        return resp

    def pwm_ctrl_configure(self):
        """
        Configures the PWM control of the microcontroller on the PiXtend board. The data transferred includes
        all PWM settings like the Mode, OD setting and the Clock Select for the PWMs as well as the frequency.
        """

        self.__pwm_ctrl1.asByte = self.__pwm_period.bytes.byte0
        self.__pwm_ctrl2.asByte = self.__pwm_period.bytes.byte1

        if not self.__is_automatic_mode_active:
            self.__pwm_control_set(self.__pwm_ctrl0.asByte, self.__pwm_ctrl1.asByte, self.__pwm_ctrl2.asByte)

    @property
    def pwm_ctrl_mode(self):
        """
        Get or Set the PWM mode. A value of 0 means the PWMs are in servo mode, a value of 1 means both PWMs are
        in PWM mode.
        """

        return self.__pwm_ctrl0.b.bit0

    @pwm_ctrl_mode.setter
    def pwm_ctrl_mode(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = servo or 1 = pwm")
        self.__pwm_ctrl0.b.bit0 = value

    @property
    def pwm_ctrl_od0(self):
        """
        Get or Set the Over Drive (OD) value for PWM 0. A value of 0 means 'off' and 1 means 'on'.
        """

        return self.__pwm_ctrl0.b.bit1

    @pwm_ctrl_od0.setter
    def pwm_ctrl_od0(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 or 1")
        self.__pwm_ctrl0.b.bit1 = value

    @property
    def pwm_ctrl_od1(self):
        """
        Get or Set the Over Drive (OD) value for PWM 1. A value of 0 means 'off' and 1 means 'on'.
        """

        return self.__pwm_ctrl0.b.bit2

    @pwm_ctrl_od1.setter
    def pwm_ctrl_od1(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 or 1")
        self.__pwm_ctrl0.b.bit2 = value

    @property
    def pwm_ctrl_cs0(self):
        """
        Get or Set the Clock Select bit 0 (CS0) for both PWMs. This setting will be ignored if PWMs are in servo mode.
        A value of 1 means this CS is 'on' (selected) and 0 means 'off' (not selected).
        """

        return self.__pwm_ctrl0.b.bit5

    @pwm_ctrl_cs0.setter
    def pwm_ctrl_cs0(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 or 1")
        self.__pwm_ctrl0.b.bit5 = value

    @property
    def pwm_ctrl_cs1(self):
        """
        Get or Set the Clock Select bit 1 (CS1) for both PWMs. This setting will be ignored if PWMs are in servo mode.
        A value of 1 means this CS is 'on' (selected) and 0 means 'off' (not selected).
        """

        return self.__pwm_ctrl0.b.bit6

    @pwm_ctrl_cs1.setter
    def pwm_ctrl_cs1(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 or 1")
        self.__pwm_ctrl0.b.bit6 = value

    @property
    def pwm_ctrl_cs2(self):
        """
        Get or Set the Clock Select bit 2 (CS2) for both PWMs. This setting will be ignored if PWMs are in servo mode.
        A value of 1 means this CS is 'on' (selected) and 0 means 'off' (not selected).
        """

        return self.__pwm_ctrl0.b.bit7

    @pwm_ctrl_cs2.setter
    def pwm_ctrl_cs2(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 or 1")
        self.__pwm_ctrl0.b.bit7 = value

    @property
    def pwm_ctrl_period(self):
        """
        Get or Set the frequency/signal period length of the PWMs. Values from 0 to 65000 are allowed.
        
        Example:
            pwm_ctrl_cs0 = 1, pwm_ctrl_cs1 = 1, pwm_ctrl_cs2 = 0, pwm_ctrl_mode = 1 and pwm_ctrl_period = 1000
            PWM Period length = uMC Freq / Prescaler / PWM_CTRL1..2
            PWM Period length = 16 MHz   /    64     /  1000        = 250 Hz
        """

        return self.__pwm_period.asUint16

    @pwm_ctrl_period.setter
    def pwm_ctrl_period(self, value):
        if 0 <= value <= 65000:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 65000")
        self.__pwm_period.asUint16 = value

    @property
    def pwm0(self):
        """
        Get or Set the PWM 0 duty cycle. This value has to correspond to the PWM freq/signal period configuration.
        The allowed values for PWM 0 are 0 to 65000.
        
        Example:
            pwm_ctrl_cs0 = 1, pwm_ctrl_cs1 = 1, pwm_ctrl_cs2 = 0, pwm_ctrl_mode = 1 and pwm_ctrl_period = 5000
            * If pwm0 is set to 2500 the duty cycle will be 50%
            * If pwm0 > pwm_ctrl_period the PWM channel will be continuously logical 1
            * If pwm0 = 0 the PWM channel will be continuously logical 0
        """

        return self.__pwm0_value.asUint16

    @pwm0.setter
    def pwm0(self, value):
        if 0 <= value <= 65000:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 65000")
        self.__pwm0_value.asUint16 = value
        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_PWM0, self.__pwm0_value.bytes.byte0,
                                     self.__pwm0_value.bytes.byte1)

    @property
    def pwm1(self):
        """
        Get or Set the PWM 1 duty cycle. This value has to correspond to the PWM freq/signal period configuration.
        The allowed values for PWM 1 are 0 to 65000.

        Example:
            pwm_ctrl_cs0 = 1, pwm_ctrl_cs1 = 1, pwm_ctrl_cs2 = 0, pwm_ctrl_mode = 1 and pwm_ctrl_period = 5000
            * If pwm1 is set to 2500 the duty cycle will be 50%.
            * If pwm1 > pwm_ctrl_period the PWM channel will be continuously logical 1
            * If pwm1 = 0 the PWM channel will be continuously logical 0
        """

        return self.__pwm1_value.asUint16

    @pwm1.setter
    def pwm1(self, value):
        if 0 <= value <= 65000:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 65000")
        self.__pwm1_value.asUint16 = value
        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_PWM1, self.__pwm1_value.bytes.byte0,
                                     self.__pwm1_value.bytes.byte1)

    # </editor-fold>

    # <editor-fold desc="Region: Analog Inputs 0 - 3">

    # **************************************************************************
    # Analog Inputs 0 - 3
    # **************************************************************************
    def __analog_input_register_set(self):
        """
        Set the analog control register of the microcontroller on the PiXtend board. 
        """

        self.__transfer_spi_data(self.PIXTEND_SPI_SET_AI_CTRL, self.__ai_ctrl0.asByte, self.__ai_ctrl1.asByte)

    def __analog_input_get(self, command):
        """
        Get the analog value from one of the 4 analog inputs on the PiXtend board.
        
        :param int command: One of the 4 PIXTEND_SPI_GET_AINx constants values specifying AI0-3
        :return: A 16 bit value representing the analog value of the requested AIx
        :rtype: c_uint16
        """

        # Only transfer data is Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            # Wait, this method might have been called before. The microcontroller needs time for processing.
            time.sleep(0.05)
            self.__transfer_spi_data(command)
            # Wait again after the first transfer, the microcontroller now needs time to start and complete its A/D
            # conversion. Then the 'real' data can be requested.
            time.sleep(0.05)
            resp = self.__transfer_spi_data(command)
            # Wait for security in case this or another method with SPI data transfer is called right after this one.
            time.sleep(0.05)

            if len(resp) >= 4:
                self.__analog_value.bytes.byte0 = resp[3]
                self.__analog_value.bytes.byte1 = resp[4]
            else:
                self.__analog_value.asUint16 = 0
        else:
            if command == self.PIXTEND_SPI_GET_AIN0:
                self.__analog_value.asUint16 = self.__ai0_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_AIN1:
                self.__analog_value.asUint16 = self.__ai1_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_AIN2:
                self.__analog_value.asUint16 = self.__ai2_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_AIN3:
                self.__analog_value.asUint16 = self.__ai3_raw_value.asUint16
            else:
                self.__analog_value.asUint16 = 0

        return self.__analog_value.asUint16

    @property
    def analog_input0_raw(self):
        """
        Get the raw value of analog input 0. 
        """

        return self.__analog_input_get(self.PIXTEND_SPI_GET_AIN0)

    @property
    def analog_input1_raw(self):
        """
        Get the raw value of analog input 1. 
        """

        return self.__analog_input_get(self.PIXTEND_SPI_GET_AIN1)

    @property
    def analog_input2_raw(self):
        """
        Get the raw value of analog input 2. 
        """

        return self.__analog_input_get(self.PIXTEND_SPI_GET_AIN2)

    @property
    def analog_input3_raw(self):
        """
        Get the raw value of analog input 3. 
        """

        return self.__analog_input_get(self.PIXTEND_SPI_GET_AIN3)

    @property
    def analog_input0_10volts_jumper(self):
        """
        Get or Set the 10 volts jumper setting, depending if the jumper was physically set on the PiXtend board.
        The library needs to know this setting to perform correct calculations of the raw analog
        values of the analog inputs when they are converted their final float value. Applies only to AI0 and AI1
        as these 2 inputs measure voltage.
        """

        return self.__ai0_jumper_setting_10_volts

    @analog_input0_10volts_jumper.setter
    def analog_input0_10volts_jumper(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use: 0 = 5 volts, 1 = 10 volts")
        self.__ai0_jumper_setting_10_volts = value

    @property
    def analog_input1_10volts_jumper(self):
        """
        Get or Set the 10 volts jumper setting, depending if the jumper was physically set on the PiXtend board.
        The library needs to know this setting to perform correct calculations of the raw analog
        values of the analog inputs when they are converted their final float value. Applies only to AI0 and AI1
        as these 2 inputs measure voltage.
        """

        return self.__ai1_jumper_setting_10_volts

    @analog_input1_10volts_jumper.setter
    def analog_input1_10volts_jumper(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use: 0 = 5 volts, 1 = 10 volts")
        self.__ai1_jumper_setting_10_volts = value

    @property
    def analog_input0_nos(self):
        """
        Get or Set the Number of Samples (NoS) the analog input 0 should take from the incoming analog signal.
        Possible NoS values are 1, 5, 10 (default) and 50. If something is wrong -1 is returned.
        
        :return: Decimal value of the Number of Samples (NoS) 
        :rtype: int
        :raises ValueError: If passed value is not 1, 5, 10, 50
        """

        if self.__ai_ctrl0.b.bit0 == 0 and self.__ai_ctrl0.b.bit1 == 0:
            return 10
        elif self.__ai_ctrl0.b.bit0 == 1 and self.__ai_ctrl0.b.bit1 == 0:
            return 1
        elif self.__ai_ctrl0.b.bit0 == 0 and self.__ai_ctrl0.b.bit1 == 1:
            return 5
        elif self.__ai_ctrl0.b.bit0 == 1 and self.__ai_ctrl0.b.bit1 == 1:
            return 50
        else:
            return -1

    @analog_input0_nos.setter
    def analog_input0_nos(self, value):
        if value == 1 or value == 5 or value == 10 or value == 50:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use: 1, 5, 10 or 50 NoS")

        if value == 1:
            self.__ai_ctrl0.b.bit0 = 1
            self.__ai_ctrl0.b.bit1 = 0
        elif value == 5:
            self.__ai_ctrl0.b.bit0 = 0
            self.__ai_ctrl0.b.bit1 = 1
        elif value == 10:
            self.__ai_ctrl0.b.bit0 = 0
            self.__ai_ctrl0.b.bit1 = 0
        elif value == 50:
            self.__ai_ctrl0.b.bit0 = 1
            self.__ai_ctrl0.b.bit1 = 1
        else:
            self.__ai_ctrl0.b.bit0 = 0
            self.__ai_ctrl0.b.bit1 = 0

        if not self.__is_automatic_mode_active:
            self.__analog_input_register_set()

    @property
    def analog_input1_nos(self):
        """
        Get or Set the Number of Samples (NoS) the analog input 1 should take from the incoming analog signal.
        Possible NoS values are 1, 5, 10 (default) and 50. If something is wrong -1 is returned.

        :return: Decimal value of the Number of Samples (NoS) 
        :rtype: int
        :raises ValueError: If passed value is not 1, 5, 10, 50
        """

        if self.__ai_ctrl0.b.bit2 == 0 and self.__ai_ctrl0.b.bit3 == 0:
            return 10
        elif self.__ai_ctrl0.b.bit2 == 1 and self.__ai_ctrl0.b.bit3 == 0:
            return 1
        elif self.__ai_ctrl0.b.bit2 == 0 and self.__ai_ctrl0.b.bit3 == 1:
            return 5
        elif self.__ai_ctrl0.b.bit2 == 1 and self.__ai_ctrl0.b.bit3 == 1:
            return 50
        else:
            return -1

    @analog_input1_nos.setter
    def analog_input1_nos(self, value):
        if value == 1 or value == 5 or value == 10 or value == 50:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use: 1, 5, 10 or 50 NoS")

        if value == 1:
            self.__ai_ctrl0.b.bit2 = 1
            self.__ai_ctrl0.b.bit3 = 0
        elif value == 5:
            self.__ai_ctrl0.b.bit2 = 0
            self.__ai_ctrl0.b.bit3 = 1
        elif value == 10:
            self.__ai_ctrl0.b.bit2 = 0
            self.__ai_ctrl0.b.bit3 = 0
        elif value == 50:
            self.__ai_ctrl0.b.bit2 = 1
            self.__ai_ctrl0.b.bit3 = 1
        else:
            self.__ai_ctrl0.b.bit2 = 0
            self.__ai_ctrl0.b.bit3 = 0

        if not self.__is_automatic_mode_active:
            self.__analog_input_register_set()

    @property
    def analog_input2_nos(self):
        """
        Get or Set the Number of Samples (NoS) the analog input 2 should take from the incoming analog signal.
        Possible NoS values are 1, 5, 10 (default) and 50. If something is wrong -1 is returned.

        :return: Decimal value of the Number of Samples (NoS) 
        :rtype: int
        :raises ValueError: If passed value is not 1, 5, 10, 50
        """

        if self.__ai_ctrl0.b.bit4 == 0 and self.__ai_ctrl0.b.bit5 == 0:
            return 10
        elif self.__ai_ctrl0.b.bit4 == 1 and self.__ai_ctrl0.b.bit5 == 0:
            return 1
        elif self.__ai_ctrl0.b.bit4 == 0 and self.__ai_ctrl0.b.bit5 == 1:
            return 5
        elif self.__ai_ctrl0.b.bit4 == 1 and self.__ai_ctrl0.b.bit5 == 1:
            return 50
        else:
            return -1

    @analog_input2_nos.setter
    def analog_input2_nos(self, value):
        if value == 1 or value == 5 or value == 10 or value == 50:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use: 1, 5, 10 or 50 NoS")

        if value == 1:
            self.__ai_ctrl0.b.bit4 = 1
            self.__ai_ctrl0.b.bit5 = 0
        elif value == 5:
            self.__ai_ctrl0.b.bit4 = 0
            self.__ai_ctrl0.b.bit5 = 1
        elif value == 10:
            self.__ai_ctrl0.b.bit4 = 0
            self.__ai_ctrl0.b.bit5 = 0
        elif value == 50:
            self.__ai_ctrl0.b.bit4 = 1
            self.__ai_ctrl0.b.bit5 = 1
        else:
            self.__ai_ctrl0.b.bit4 = 0
            self.__ai_ctrl0.b.bit5 = 0

        if not self.__is_automatic_mode_active:
            self.__analog_input_register_set()

    @property
    def analog_input3_nos(self):
        """
        Get or Set the Number of Samples (NoS) the analog input 3 should take from the incoming analog signal.
        Possible NoS values are 1, 5, 10 (default) and 50. If something is wrong -1 is returned.

        :return: Decimal value of the Number of Samples (NoS) 
        :rtype: int
        :raises ValueError: If passed value is not 1, 5, 10, 50
        """

        if self.__ai_ctrl0.b.bit6 == 0 and self.__ai_ctrl0.b.bit7 == 0:
            return 10
        elif self.__ai_ctrl0.b.bit6 == 1 and self.__ai_ctrl0.b.bit7 == 0:
            return 1
        elif self.__ai_ctrl0.b.bit6 == 0 and self.__ai_ctrl0.b.bit7 == 1:
            return 5
        elif self.__ai_ctrl0.b.bit6 == 1 and self.__ai_ctrl0.b.bit7 == 1:
            return 50
        else:
            return -1

    @analog_input3_nos.setter
    def analog_input3_nos(self, value):
        if value == 1 or value == 5 or value == 10 or value == 50:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use: 1, 5, 10 or 50 NoS")

        if value == 1:
            self.__ai_ctrl0.b.bit6 = 1
            self.__ai_ctrl0.b.bit7 = 0
        elif value == 5:
            self.__ai_ctrl0.b.bit6 = 0
            self.__ai_ctrl0.b.bit7 = 1
        elif value == 10:
            self.__ai_ctrl0.b.bit6 = 0
            self.__ai_ctrl0.b.bit7 = 0
        elif value == 50:
            self.__ai_ctrl0.b.bit6 = 1
            self.__ai_ctrl0.b.bit7 = 1
        else:
            self.__ai_ctrl0.b.bit6 = 0
            self.__ai_ctrl0.b.bit7 = 0

        if not self.__is_automatic_mode_active:
            self.__analog_input_register_set()

    @property
    def analog_input_nos_freq(self):
        """
        Get or Set the Clock Select of the A/D converter of the microcontroller on the PiXtend board.
        Possible float values are 0.125, 0.250, 0.500, 1.0, 2.0, 4.0 and 8.0. The unit is Mhz.
        
        :return: Float value of the currently set A/D converter frequency
        :rtype: float
        """

        if self.__ai_ctrl1.b.bit5 == 0 and self.__ai_ctrl1.b.bit6 == 0 and self.__ai_ctrl1.b.bit7 == 0:
            return 0.125
        elif self.__ai_ctrl1.b.bit5 == 0 and self.__ai_ctrl1.b.bit6 == 1 and self.__ai_ctrl1.b.bit7 == 1:
            return 0.250
        elif self.__ai_ctrl1.b.bit5 == 1 and self.__ai_ctrl1.b.bit6 == 0 and self.__ai_ctrl1.b.bit7 == 1:
            return 0.500
        elif self.__ai_ctrl1.b.bit5 == 0 and self.__ai_ctrl1.b.bit6 == 0 and self.__ai_ctrl1.b.bit7 == 1:
            return 1.0
        elif self.__ai_ctrl1.b.bit5 == 1 and self.__ai_ctrl1.b.bit6 == 1 and self.__ai_ctrl1.b.bit7 == 0:
            return 2.0
        elif self.__ai_ctrl1.b.bit5 == 0 and self.__ai_ctrl1.b.bit6 == 1 and self.__ai_ctrl1.b.bit7 == 0:
            return 4.0
        elif self.__ai_ctrl1.b.bit5 == 1 and self.__ai_ctrl1.b.bit6 == 0 and self.__ai_ctrl1.b.bit7 == 0:
            return 8.0
        else:
            return -1.0

    @analog_input_nos_freq.setter
    def analog_input_nos_freq(self, value):
        if value == 0.125 or value == 0.250 or value == 0.500 or value == 1.0 or \
                        value == 2.0 or value == 4.0 or value == 8.0:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) +
                             " not allowed! - Use (MHz): 0.125, 0.250, 0.500, 1.0, 2.0, 4.0 or 8.0")

        if value == 0.125:
            self.__ai_ctrl1.b.bit5 = 0
            self.__ai_ctrl1.b.bit6 = 0
            self.__ai_ctrl1.b.bit7 = 0
        elif value == 0.250:
            self.__ai_ctrl1.b.bit5 = 0
            self.__ai_ctrl1.b.bit6 = 1
            self.__ai_ctrl1.b.bit7 = 1
        elif value == 0.500:
            self.__ai_ctrl1.b.bit5 = 1
            self.__ai_ctrl1.b.bit6 = 0
            self.__ai_ctrl1.b.bit7 = 1
        elif value == 1.0:
            self.__ai_ctrl1.b.bit5 = 0
            self.__ai_ctrl1.b.bit6 = 0
            self.__ai_ctrl1.b.bit7 = 1
        elif value == 2.0:
            self.__ai_ctrl1.b.bit5 = 1
            self.__ai_ctrl1.b.bit6 = 1
            self.__ai_ctrl1.b.bit7 = 0
        elif value == 4.0:
            self.__ai_ctrl1.b.bit5 = 0
            self.__ai_ctrl1.b.bit6 = 1
            self.__ai_ctrl1.b.bit7 = 0
        elif value == 8.0:
            self.__ai_ctrl1.b.bit5 = 1
            self.__ai_ctrl1.b.bit6 = 0
            self.__ai_ctrl1.b.bit7 = 0
        else:
            self.__ai_ctrl1.b.bit5 = 0
            self.__ai_ctrl1.b.bit6 = 0
            self.__ai_ctrl1.b.bit7 = 0

        if not self.__is_automatic_mode_active:
            self.__analog_input_register_set()

    @property
    def analog_input0(self):
        """
        Get analog input 0 value as float in Volts. The returned value is based on the 10 volts jumper setting. 
        """

        # Only get data directly if Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            if self.__ai0_jumper_setting_10_volts == 1:
                self.__ai0_value = c_float(self.analog_input0_raw * (10.0 / 1024))
            else:
                self.__ai0_value = c_float(self.analog_input0_raw * (5.0 / 1024))

        return self.__ai0_value.value

    @property
    def analog_input1(self):
        """
        Get analog input 1 value as float in Volts. The returned value is based on the 10 volts jumper setting. 
        """

        # Only get data directly if Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            if self.__ai1_jumper_setting_10_volts == 1:
                self.__ai1_value = c_float(self.analog_input1_raw * (10.0 / 1024))
            else:
                self.__ai1_value = c_float(self.analog_input1_raw * (5.0 / 1024))

        return self.__ai1_value.value

    @property
    def analog_input2(self):
        """
        Get analog input 2 value as float in Ampere (mA).
        """

        # Only get data directly if Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            self.__ai2_value = c_float(self.analog_input2_raw * 0.024194115990990990990990990991)

        return self.__ai2_value.value

    @property
    def analog_input3(self):
        """
        Get analog input 3 value as float in Ampere (mA).
        """

        # Only get data directly if Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            self.__ai3_value = c_float(self.analog_input3_raw * 0.024194115990990990990990990991)

        return self.__ai3_value.value

    # </editor-fold>

    # <editor-fold desc="Region: Temperature Inputs 0 - 3">

    # **************************************************************************
    # Temperature Inputs 0 - 3
    # **************************************************************************

    def __temperature_get(self, command):
        """
        Get the current temperature from the GPIO specified in 'command'. This is only possible if the corresponding
        GPIO is set to DHT mode.
        
        :param int command: One of 4 possible constant values defined by PIXTEND_SPI_GET_TEMPx
        :return: The 16 bit raw temperature value from the sensor attached to the GPIO
        :rtype: c_uint16
        """

        if not self.__is_automatic_mode_active:
            # Wait, this method might have been called before. The microcontroller needs time for processing.
            time.sleep(0.1)
            self.__transfer_spi_data(command)
            # Wait again after the first transfer/request, the microcontroller now needs time to start and complete
            # its 1-wire communication with the sensor attached to the requested GPIO.
            # Then the 'real' data can be requested.
            time.sleep(0.2)
            resp = self.__transfer_spi_data(command)
            # Wait for security in case this or another method with SPI data transfer is called right after this one.
            time.sleep(0.1)

            if len(resp) >= 4:
                self.__analog_value.bytes.byte0 = resp[3]
                self.__analog_value.bytes.byte1 = resp[4]
            else:
                self.__analog_value.asUint16 = 0
        else:
            if command == self.PIXTEND_SPI_GET_TEMP0:
                self.__analog_value.asUint16 = self.__temp0_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_TEMP1:
                self.__analog_value.asUint16 = self.__temp1_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_TEMP2:
                self.__analog_value.asUint16 = self.__temp2_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_TEMP3:
                self.__analog_value.asUint16 = self.__temp3_raw_value.asUint16
            else:
                self.__analog_value.asUint16 = 0

        return self.__analog_value.asUint16

    @property
    def use_fahrenheit(self):
        """
        Get or Set if the conversion of the temperature raw value should be done in Fahrenheit.
        Default is 'False', meaning by getting the temperature from t0_dht22 to t3_dht22 or from t0_dht11 to t3_dht11
        the value will be in degrees Celsius, if set to 'True' the values will be in Fahrenheit.
        
        :returns: Bool value, 'False' for Celsius and 'True' for Fahrenheit
        :rtype: bool
        """

        return self.__use_fahrenheit

    @use_fahrenheit.setter
    def use_fahrenheit(self, value):
        self.__use_fahrenheit = value

    @property
    def temp_input0_raw(self):
        """
        Get the temperature raw value from temperature input 0. 
        """

        return self.__temperature_get(self.PIXTEND_SPI_GET_TEMP0)

    @property
    def temp_input1_raw(self):
        """
        Get the temperature raw value from temperature input 1. 
        """

        return self.__temperature_get(self.PIXTEND_SPI_GET_TEMP1)

    @property
    def temp_input2_raw(self):
        """
        Get the temperature raw value from temperature input 2. 
        """

        return self.__temperature_get(self.PIXTEND_SPI_GET_TEMP2)

    @property
    def temp_input3_raw(self):
        """
        Get the temperature raw value from temperature input 3. 
        """

        return self.__temperature_get(self.PIXTEND_SPI_GET_TEMP3)

    @property
    def t0_dht22(self):
        """
        Get the converted temperature value from temperature input 0 from a DHT22 sensor. 
        """

        factor = 1.0
        value = self.temp_input0_raw
        if self.__test_bit(value, self.BIT_15) == 1:
            value = self.__clear_bit(value, self.BIT_15)
            factor = -1.0

        if self.__use_fahrenheit:
            return ((float(value) * 1.8) + 32) * factor
        else:
            return (float(value) / 10.0) * factor

    @property
    def t1_dht22(self):
        """
        Get the converted temperature value from temperature input 1 from a DHT22 sensor. 
        """

        factor = 1.0
        value = self.temp_input1_raw
        if self.__test_bit(value, self.BIT_15) == 1:
            value = self.__clear_bit(value, self.BIT_15)
            factor = -1.0

        if self.__use_fahrenheit:
            return ((float(value) * 1.8) + 32) * factor
        else:
            return (float(value) / 10.0) * factor

    @property
    def t2_dht22(self):
        """
        Get the converted temperature value from temperature input 2 from a DHT22 sensor. 
        """

        factor = 1.0
        value = self.temp_input2_raw
        if self.__test_bit(value, self.BIT_15) == 1:
            value = self.__clear_bit(value, self.BIT_15)
            factor = -1.0

        if self.__use_fahrenheit:
            return ((float(value) * 1.8) + 32) * factor
        else:
            return (float(value) / 10.0) * factor

    @property
    def t3_dht22(self):
        """
        Get the converted temperature value from temperature input 3 from a DHT22 sensor. 
        """

        factor = 1.0
        value = self.temp_input3_raw
        if self.__test_bit(value, self.BIT_15) == 1:
            value = self.__clear_bit(value, self.BIT_15)
            factor = -1.0

        if self.__use_fahrenheit:
            return ((float(value) * 1.8) + 32) * factor
        else:
            return (float(value) / 10.0) * factor

    @property
    def t0_dht11(self):
        """
        Get the converted temperature value from temperature input 0 from a DHT11 sensor. 
        """

        if self.__use_fahrenheit:
            return (float(self.temp_input0_raw / 256) * 1.8) + 32
        else:
            return float(self.temp_input0_raw / 256)

    @property
    def t1_dht11(self):
        """
        Get the converted temperature value from temperature input 1 from a DHT11 sensor. 
        """

        if self.__use_fahrenheit:
            return (float(self.temp_input1_raw / 256) * 1.8) + 32
        else:
            return float(self.temp_input1_raw / 256)

    @property
    def t2_dht11(self):
        """
        Get the converted temperature value from temperature input 2 from a DHT11 sensor. 
        """

        if self.__use_fahrenheit:
            return (float(self.temp_input2_raw / 256) * 1.8) + 32
        else:
            return float(self.temp_input2_raw / 256)

    @property
    def t3_dht11(self):
        """
        Get the converted temperature value from temperature input 3 from a DHT11 sensor. 
        """

        if self.__use_fahrenheit:
            return (float(self.temp_input3_raw / 256) * 1.8) + 32
        else:
            return float(self.temp_input3_raw / 256)

    # </editor-fold>

    # <editor-fold desc="Region: Humidity Inputs 0 - 3">

    # **************************************************************************
    # Humidity Inputs 0 - 3
    # **************************************************************************

    def __humidity_get(self, command):
        """
        Get the current humidity from the GPIO specified in 'command'. This is only possible if the corresponding
        GPIO is set to DHT (1-wire) mode.

        :param int command: One of 4 possible constant values defined by PIXTEND_SPI_GET_HUMx
        :return: The 16 bit raw humidity value from the sensor attached to the GPIO
        :rtype: c_uint16
        """

        if not self.__is_automatic_mode_active:
            # Wait, this method might have been called before. The microcontroller needs time for processing.
            time.sleep(0.1)
            self.__transfer_spi_data(command)
            # Wait again after the first transfer/request, the microcontroller now needs time to start and complete
            # its 1-wire communication with the sensor attached to the requested GPIO.
            # Then the 'real' data can be requested.
            time.sleep(0.2)
            value = self.__transfer_spi_data(command)
            # Wait for security in case this or another method with SPI data transfer is called right after this one.
            time.sleep(0.1)

            if len(value) >= 4:
                self.__analog_value.bytes.byte0 = value[3]
                self.__analog_value.bytes.byte1 = value[4]
            else:
                self.__analog_value.asUint16 = 0
        else:
            if command == self.PIXTEND_SPI_GET_HUM0:
                self.__analog_value.asUint16 = self.__humid0_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_HUM1:
                self.__analog_value.asUint16 = self.__humid1_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_HUM2:
                self.__analog_value.asUint16 = self.__humid2_raw_value.asUint16
            elif command == self.PIXTEND_SPI_GET_HUM3:
                self.__analog_value.asUint16 = self.__humid3_raw_value.asUint16
            else:
                self.__analog_value.asUint16 = 0

        return self.__analog_value.asUint16

    @property
    def hum_input0_raw(self):
        """
        Get the humidity raw value from humidity input 0. 
        """

        return self.__humidity_get(self.PIXTEND_SPI_GET_HUM0)

    @property
    def hum_input1_raw(self):
        """
        Get the humidity raw value from humidity input 1. 
        """

        return self.__humidity_get(self.PIXTEND_SPI_GET_HUM1)

    @property
    def hum_input2_raw(self):
        """
        Get the humidity raw value from humidity input 2. 
        """

        return self.__humidity_get(self.PIXTEND_SPI_GET_HUM2)

    @property
    def hum_input3_raw(self):
        """
        Get the humidity raw value from humidity input 3. 
        """

        return self.__humidity_get(self.PIXTEND_SPI_GET_HUM3)

    @property
    def h0_dht22(self):
        """
        Get the converted humidity value from humidity input 0 if a DHT22 sensor is physically attached. 
        """

        return float(self.hum_input0_raw) / 10.0

    @property
    def h1_dht22(self):
        """
        Get the converted humidity value from humidity input 1 if a DHT22 sensor is physically attached. 
        """

        return float(self.hum_input1_raw) / 10.0

    @property
    def h2_dht22(self):
        """
        Get the converted humidity value from humidity input 2 if a DHT22 sensor is physically attached. 
        """

        return float(self.hum_input2_raw) / 10.0

    @property
    def h3_dht22(self):
        """
        Get the converted humidity value from humidity input 3 if a DHT22 sensor is physically attached. 
        """

        return float(self.hum_input3_raw) / 10.0

    @property
    def h0_dht11(self):
        """
        Get the converted humidity value from humidity input 0 if a DHT11 sensor is physically attached.  
        """

        return float(self.hum_input0_raw / 256)

    @property
    def h1_dht11(self):
        """
        Get the converted humidity value from humidity input 1 if a DHT11 sensor is physically attached.  
        """

        return float(self.hum_input1_raw / 256)

    @property
    def h2_dht11(self):
        """
        Get the converted humidity value from humidity input 2 if a DHT11 sensor is physically attached.  
        """

        return float(self.hum_input2_raw / 256)

    @property
    def h3_dht11(self):
        """
        Get the converted humidity value from humidity input 3 if a DHT11 sensor is physically attached. 
        """

        return float(self.hum_input3_raw / 256)

    # </editor-fold>

    # <editor-fold desc="Region: Digital Outputs">

    # **************************************************************************
    # Digital Outputs
    # **************************************************************************

    def __digital_outputs_states_get(self):
        """
        Get the states of the digital outputs. Since PiXtend board version 1.3.x the digital outputs have the
        capability to read back their own state. 
        """

        # Only do an SPI data transfer if Auto Mode is not active and the PiXtend board version is higher
        # then 12, meaning version 1.2.x. Only boards starting from version 1.3.0 can read back their own outputs.
        if not self.__is_automatic_mode_active and self.__uc_version.UC_VERSIONH > 12:
            resp = self.__transfer_spi_data(self.PIXTEND_SPI_GET_DOUT)

            if len(resp) >= 3:
                self.__digital_outputs_states = resp[3]
            else:
                self.__digital_outputs_states = 0

        return self.__digital_outputs_states

    def __digital_outputs_states_set(self, value, bit_num):

        if value == 0:
            self.__digital_outputs_states = self.__clear_bit(self.__digital_outputs_states, bit_num)
        if value == 1:
            self.__digital_outputs_states = self.__set_bit(self.__digital_outputs_states, bit_num)

        # Only do an SPI data transfer if Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_DOUT, self.__digital_outputs_states)

    @property
    def digital_output0(self):
        """
        Get or Set the state of digital output 0. A value 0 means 'off' and a value of 1 means 'on'. 
        """

        return self.__test_bit(self.__digital_outputs_states_get(), self.BIT_0)

    @digital_output0.setter
    def digital_output0(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__digital_outputs_states_set(value, self.BIT_0)

    @property
    def do0(self):
        """
        Get or Set the state of digital output 0. A value 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_output0 <--> do0
        """

        return self.digital_output0

    @do0.setter
    def do0(self, value):
        self.digital_output0 = value

    @property
    def digital_output1(self):
        """
        Get or Set the state of digital output 1. A value 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_outputs_states_get(), self.BIT_1)

    @digital_output1.setter
    def digital_output1(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__digital_outputs_states_set(value, self.BIT_1)

    @property
    def do1(self):
        """
        Get or Set the state of digital output 1. A value 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_output1 <--> do1
        """

        return self.digital_output1

    @do1.setter
    def do1(self, value):
        self.digital_output1 = value

    @property
    def digital_output2(self):
        """
        Get or Set the state of digital output 2. A value 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_outputs_states_get(), self.BIT_2)

    @digital_output2.setter
    def digital_output2(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__digital_outputs_states_set(value, self.BIT_2)

    @property
    def do2(self):
        """
        Get or Set the state of digital output 2. A value 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_output2 <--> do2
        """

        return self.digital_output2

    @do2.setter
    def do2(self, value):
        self.digital_output2 = value

    @property
    def digital_output3(self):
        """
        Get or Set the state of digital output 3. A value 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_outputs_states_get(), self.BIT_3)

    @digital_output3.setter
    def digital_output3(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__digital_outputs_states_set(value, self.BIT_3)

    @property
    def do3(self):
        """
        Get or Set the state of digital output 3. A value 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_output3 <--> do3
        """

        return self.digital_output3

    @do3.setter
    def do3(self, value):
        self.digital_output3 = value

    @property
    def digital_output4(self):
        """
        Get or Set the state of digital output 4. A value 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_outputs_states_get(), self.BIT_4)

    @digital_output4.setter
    def digital_output4(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__digital_outputs_states_set(value, self.BIT_4)

    @property
    def do4(self):
        """
        Get or Set the state of digital output 4. A value 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_output4 <--> do4
        """

        return self.digital_output4

    @do4.setter
    def do4(self, value):
        self.digital_output4 = value

    @property
    def digital_output5(self):
        """
        Get or Set the state of digital output 5. A value 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_outputs_states_get(), self.BIT_5)

    @digital_output5.setter
    def digital_output5(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__digital_outputs_states_set(value, self.BIT_5)

    @property
    def do5(self):
        """
        Get or Set the state of digital output 5. A value 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_output5 <--> do5
        """

        return self.digital_output5

    @do5.setter
    def do5(self, value):
        self.digital_output5 = value

    # </editor-fold>

    # <editor-fold desc="Region: Relay Outputs">

    # **************************************************************************
    # Relay Outputs
    # **************************************************************************

    def __relays_states_get(self):
        """
        Get the current states of the 4 relays on the PiXtend board.
        """

        # Only do an SPI data transfer if Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            resp = self.__transfer_spi_data(self.PIXTEND_SPI_GET_RELAY)
            if len(resp) >= 3:
                self.__relays_states = resp[3]
            else:
                self.__relays_states = 0

        return self.__relays_states

    def __relays_states_set(self, value, bit_num):
        """
        Set the current states of the 4 relays on the PiXtend board.
        
        :param int value: Value the specified bit should have, 0 or 1 
        :param int bit_num: Number of the bit to change 
        """

        if value == 0:
            self.__relays_states = self.__clear_bit(self.__relays_states, bit_num)
        if value == 1:
            self.__relays_states = self.__set_bit(self.__relays_states, bit_num)

        # Only do an SPI data transfer if Auto Mode is not active.
        if not self.__is_automatic_mode_active:
            self.__transfer_spi_data(self.PIXTEND_SPI_SET_RELAY, self.__relays_states)

    @property
    def relay0(self):
        """
        Get or Set the state of relay 0. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__relays_states_get(), self.BIT_0)

    @relay0.setter
    def relay0(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__relays_states_set(value, self.BIT_0)

    @property
    def relay1(self):
        """
        Get or Set the state of relay 1. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__relays_states_get(), self.BIT_1)

    @relay1.setter
    def relay1(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__relays_states_set(value,  self.BIT_1)

    @property
    def relay2(self):
        """
        Get or Set the state of relay 2. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__relays_states_get(), self.BIT_2)

    @relay2.setter
    def relay2(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__relays_states_set(value, self.BIT_2)

    @property
    def relay3(self):
        """
        Get or Set the state of relay 3. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__relays_states_get(), self.BIT_3)

    @relay3.setter
    def relay3(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = off, 1 = on")
        self.__relays_states_set(value, self.BIT_3)

    # </editor-fold>

    # <editor-fold desc="Region: Digital Inputs">

    # **************************************************************************
    # Digital Inputs
    # **************************************************************************

    def __digital_inputs_get(self):
        """
        Get the current states of the 8 digital inputs on the PiXtend board.
        """

        # In manual mode (__is_automatic_mode_active == False), get the current states of the
        # digital inputs directly via SPI request. In Auto Mode, simply return the int with the states.
        if not self.__is_automatic_mode_active:
            value = self.__transfer_spi_data(self.PIXTEND_SPI_GET_DIN)
            if len(value) >= 3:
                self.__digital_inputs_states = value[3]
            else:
                self.__digital_inputs_states = 0

        return self.__digital_inputs_states

    @property
    def digital_input0(self):
        """
        Get the state of digital input 0. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_0)

    @property
    def digital_input1(self):
        """
        Get the state of digital input 1. A value pf 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_1)

    @property
    def digital_input2(self):
        """
        Get the state of digital input 2. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_2)

    @property
    def digital_input3(self):
        """
        Get the state of digital input 3. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_3)

    @property
    def digital_input4(self):
        """
        Get the state of digital input 4. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_4)

    @property
    def digital_input5(self):
        """
        Get the state of digital input 5. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_5)

    @property
    def digital_input6(self):
        """
        Get the state of digital input 6. A value of 0 means 'off' and a value of 1 means 'on'. 
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_6)

    @property
    def digital_input7(self):
        """
        Get the state of digital input 7. A value of 0 means 'off' and a value of 1 means 'on'.
        """

        return self.__test_bit(self.__digital_inputs_get(), self.BIT_7)

    # </editor-fold>

    # <editor-fold desc="Region: Digital Inputs short names for shorter programs">

    # **************************************************************************
    # Digital Inputs short form
    # **************************************************************************

    @property
    def di0(self):
        """
        Get the state of digital input 0. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input0 <--> di0
        """

        return self.digital_input0

    @property
    def di1(self):
        """
        Get the state of digital input 1. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input1 <--> di1
        """

        return self.digital_input1

    @property
    def di2(self):
        """
        Get the state of digital input 2. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input2 <--> di2
        """

        return self.digital_input2

    @property
    def di3(self):
        """
        Get the state of digital input 3. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input3 <--> di3
        """

        return self.digital_input3

    @property
    def di4(self):
        """
        Get the state of digital input 4. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input4 <--> di4
        """

        return self.digital_input4

    @property
    def di5(self):
        """
        Get the state of digital input 5. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input5 <--> di5
        """

        return self.digital_input5

    @property
    def di6(self):
        """
        Get the state of digital input 6. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input6 <--> di6
        """

        return self.digital_input6

    @property
    def di7(self):
        """
        Get the state of digital input 7. A value of 0 means 'off' and a value of 1 means 'on'.
        This property is just a shorter version in terms of wording: digital_input7 <--> di7
        """

        return self.digital_input7

    # </editor-fold>

    # <editor-fold desc="Region: Digital Analog Converter DAC">

    # **************************************************************************
    # Digital Analog Converter DAC
    # **************************************************************************
    @property
    def dac_selection(self):
        """
        Get or Set the DAC selection. There are 2 DAC's on the PiXtend board. DAC A = 0 and DAC B = 1.
        
        :return: selected DAC, 0 = DAC A and 1 = DAC B
        :rtype: int
        """
        return self.__analog_dac_value.bits.bit0

    @dac_selection.setter
    def dac_selection(self, value):
        if value == 0 or value == 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 = DAC A or 1 = DAC B")
        self.__analog_dac_value.bits.bit0 = value

    def set_dac_output(self, value):
        """
        Set the analog output value for the chosen DAC. The active DAC can be chosen with the property 'dac_selection'.
        The value 0 or constant DAC_A selects DAC A and the value 1 or constant DAC_B selects DAC B.
        Example:
        Selecting and setting DAC A:
        p.dac_selection = p.DAC_A
        p.set_dac_output (512)
        
        Selecting and setting DAC B:
        p.dac_selection = p.DAC_B
        p.set_dac_output (256)
        
        :param int value: Output value for the chosen DAC.
        :raises ValueError: If value is smaller then 0 or larger then 1023
        """

        if 0 <= value <= 1023:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 10bit values max. 1023")

        analog_value = Flags16()
        temp_value = Flags16()
        dac_value = AnalogValue()

        analog_value.asUint16 = value

        # Copy the 10 relevant bits from the user var to the DAC MCP4812 data format.
        # The first 2 bits in the DAC 16 bit data format are unused! Therefore we start with bit2.
        # See the DAC manual for more details.
        temp_value.bits.bit2 = analog_value.bits.bit0
        temp_value.bits.bit3 = analog_value.bits.bit1
        temp_value.bits.bit4 = analog_value.bits.bit2
        temp_value.bits.bit5 = analog_value.bits.bit3
        temp_value.bits.bit6 = analog_value.bits.bit4
        temp_value.bits.bit7 = analog_value.bits.bit5
        temp_value.bits.bit8 = analog_value.bits.bit6
        temp_value.bits.bit9 = analog_value.bits.bit7
        temp_value.bits.bit10 = analog_value.bits.bit8
        temp_value.bits.bit11 = analog_value.bits.bit9

        # bit 15 A/B: DAC A or DAC B Selection bit
        temp_value.bits.bit15 = self.__analog_dac_value.bits.bit0
        # bit 14 Don't care
        temp_value.bits.bit14 = 0
        # bit 13 Output Gain Selection bit
        temp_value.bits.bit13 = self.__analog_dac_value.bits.bit1
        # bit 12 Output Shutdown Control bit
        temp_value.bits.bit12 = self.__analog_dac_value.bits.bit2

        # Assign the 16 bit value to another union to get the individual bytes to send via SPI
        dac_value.asUint16 = temp_value.asUint16

        # Send the 2 bytes to the DAC via SPI
        self.__transfer_spi_dac_data(dac_value.bytes.byte1, dac_value.bytes.byte0)

    # </editor-fold>

    # <editor-fold desc="Region: Auto Mode">

    # **************************************************************************
    # Automatic Mode for PiXtend
    # **************************************************************************

    def auto_mode(self):
        """
        Method for the auto(matic) mode data transfer. The settings and values of all applicable
        properties like outputs, GPIO and PWM configuration for the PiXtend board are sent to the microcontroller
        in one block and states and values of all digital and analog inputs and outputs are received as response.
        This is the most efficient way to work with the microcontroller on the PiXtend board.
        
        In the beginning the auto_mode method should be called until the return value is 0 and the microcontroller's
        uc_state is 1, meaning the communication is working and the microcontroller has entered the 'Run' state.
        After that the auto_mode method does not need to be called on a regular basis, but when new values are needed
        or outputs have to be turned on or off.
        
        Example:
        if p.auto_mode() == 0 and p.uc_status == 1:
            p.relay0 = p.ON
        
        :return: 0 means communication is ok and running, -1 means crc error and/or a problem with the received data
        :rtype: int
        """

        # Set internal automatic mode to "on" (True)
        self.__is_automatic_mode_active = True

        # Set the microcontroller's control register to run in automatic mode. This value has to remain on 16 as
        # long as the automatic mode is used.
        self.__uc_ctrl.asByte = 16  # 0b00010000

        # Prepare the 34 bytes array with the data to be sent to the microcontroller
        spi_output = [0] * 34

        spi_output[0] = 128
        spi_output[1] = 255
        spi_output[2] = self.__digital_outputs_states
        spi_output[3] = self.__relays_states
        spi_output[4] = self.__gpio_states_auto_out
        spi_output[5] = self.__pwm0_value.bytes.byte0
        spi_output[6] = self.__pwm0_value.bytes.byte1
        spi_output[7] = self.__pwm1_value.bytes.byte0
        spi_output[8] = self.__pwm1_value.bytes.byte1
        spi_output[9] = self.__pwm_ctrl0.asByte
        spi_output[10] = self.__pwm_ctrl1.asByte
        spi_output[11] = self.__pwm_ctrl2.asByte
        spi_output[12] = self.__gpio_ctrl
        spi_output[13] = self.__uc_ctrl.asByte
        spi_output[14] = self.__ai_ctrl0.asByte
        spi_output[15] = self.__ai_ctrl1.asByte
        spi_output[16] = self.__pi_status.asByte

        # Calculate CRC16 Transmit Checksum
        crc_sum = 0xFFFF

        for i in range(2, 31, 1):
            crc_sum = self.__calc_crc16(crc_sum, spi_output[i])

        spi_output[31] = crc_sum & 0xFF  # CRC Low Byte
        spi_output[32] = (crc_sum >> 8) & 0xFF  # CRC High Byte
        spi_output[33] = 128  # Termination

        # Initialize SPI Data Transfer with spi_output data
        spi_input = self.__transfer_spi_data(self.PIXTEND_SPI_AUTO_MODE, 0, 0, 0, spi_output)

        # ------------------------------------------------------------------------
        # "spi_input" now contains all returned data, assign values to variables
        # ------------------------------------------------------------------------
        # Calculate CRC16 receive checksum
        crc_sum = 0xFFFF
        for i in range(2, 31, 1):
            crc_sum = self.__calc_crc16(crc_sum, spi_input[i])

        crc_sum_rx = (spi_input[32] << 8) + spi_input[31]

        if crc_sum_rx != crc_sum:
            # Error crc of received data and from controller are not the same
            return -1
        else:
            # CRC values received and calculated -> OK
            self.__digital_inputs_states = spi_input[2]
            self.__ai0_raw_value.bytes.byte0 = spi_input[3]
            self.__ai0_raw_value.bytes.byte1 = spi_input[4]
            self.__ai1_raw_value.bytes.byte0 = spi_input[5]
            self.__ai1_raw_value.bytes.byte1 = spi_input[6]
            self.__ai2_raw_value.bytes.byte0 = spi_input[7]
            self.__ai2_raw_value.bytes.byte1 = spi_input[8]
            self.__ai3_raw_value.bytes.byte0 = spi_input[9]
            self.__ai3_raw_value.bytes.byte1 = spi_input[10]
            self.__gpio_states_auto_in = spi_input[11]
            self.__temp0_raw_value.bytes.byte0 = spi_input[12]
            self.__temp0_raw_value.bytes.byte1 = spi_input[13]
            self.__temp1_raw_value.bytes.byte0 = spi_input[14]
            self.__temp1_raw_value.bytes.byte1 = spi_input[15]
            self.__temp2_raw_value.bytes.byte0 = spi_input[16]
            self.__temp2_raw_value.bytes.byte1 = spi_input[17]
            self.__temp3_raw_value.bytes.byte0 = spi_input[18]
            self.__temp3_raw_value.bytes.byte1 = spi_input[19]
            self.__humid0_raw_value.bytes.byte0 = spi_input[20]
            self.__humid0_raw_value.bytes.byte1 = spi_input[21]
            self.__humid1_raw_value.bytes.byte0 = spi_input[22]
            self.__humid1_raw_value.bytes.byte1 = spi_input[23]
            self.__humid2_raw_value.bytes.byte0 = spi_input[24]
            self.__humid2_raw_value.bytes.byte1 = spi_input[25]
            self.__humid3_raw_value.bytes.byte0 = spi_input[26]
            self.__humid3_raw_value.bytes.byte1 = spi_input[27]
            self.__uc_version.UC_VERSIONL = spi_input[28]
            self.__uc_version.UC_VERSIONH = spi_input[29]
            self.__uc_status = spi_input[30]

            # Calculate the measured voltage from raw value to volts based on the 10 volts jumper setting
            if self.__ai0_jumper_setting_10_volts == 1:
                self.__ai0_value = c_float(self.__ai0_raw_value.asUint16 * (10.0 / 1024))
            else:
                self.__ai0_value = c_float(self.__ai0_raw_value.asUint16 * (5.0 / 1024))

            if self.__ai1_jumper_setting_10_volts == 1:
                self.__ai1_value = c_float(self.__ai1_raw_value.asUint16 * (10.0 / 1024))
            else:
                self.__ai1_value = c_float(self.__ai1_raw_value.asUint16 * (5.0 / 1024))

            # Calculate the milli-amps from raw value of analog inputs 2 and 3
            self.__ai2_value = c_float(self.__ai2_raw_value.asUint16 * 0.024194115990990990990990990991)
            self.__ai3_value = c_float(self.__ai3_raw_value.asUint16 * 0.024194115990990990990990990991)
            self.__temp0_value = c_float(self.__temp0_raw_value.asUint16 / 10.0)
            self.__temp1_value = c_float(self.__temp1_raw_value.asUint16 / 10.0)
            self.__temp2_value = c_float(self.__temp2_raw_value.asUint16 / 10.0)
            self.__temp3_value = c_float(self.__temp3_raw_value.asUint16 / 10.0)
            self.__humid0_value = c_float(self.__humid0_raw_value.asUint16 / 10.0)
            self.__humid1_value = c_float(self.__humid1_raw_value.asUint16 / 10.0)
            self.__humid2_value = c_float(self.__humid2_raw_value.asUint16 / 10.0)
            self.__humid3_value = c_float(self.__humid3_raw_value.asUint16 / 10.0)

            return 0

    @staticmethod
    def __calc_crc16(bycrc, bydata):
        """
        Calculates a 16 bit CRC value.

        :param int bycrc: CRC value
        :param int bydata: data byte to be added to the CRC value
        :return: Calculated CRC value
        :rtype: int
        """

        bycrc = bycrc ^ bydata

        for i in range(0, 8, 1):
            if bycrc & 1:
                bycrc = (bycrc >> 1) ^ 0xA001
            else:
                bycrc = bycrc >> 1

        return bycrc

    # </editor-fold>

    # <editor-fold desc="Region: Serial Operations">

    @property
    def serial_mode(self):
        """
        Get or Set the serial mode of the PiXtend board. Use boolean values: False = RS232 and True = RS485
        
        Example:
        p.serial_mode = p.RS232 # or p.serial_mode = False
        or
        p.serial_mode = p.RS485 # or p.serial_mode = True
        
        :return: Value of the serial mode
        :rtype: bool
        """

        return GPIO.input(self.PIXTEND_SERIAL_PIN)

    @serial_mode.setter
    def serial_mode(self, value):
        if value is True or value is False:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: " +
                             "False = RS232 or True = RS485")
        GPIO.output(self.PIXTEND_SERIAL_PIN, value)

    # </editor-fold>

    # <editor-fold desc="Region: Real Time Clock - RTC">

    @staticmethod
    def update_rtc():
        """
        Update the hardware real time clock (RTC) with the current Linux system time.
        The system time is updated by the NTP service, which is active by default, if it is able to connect to
        the Internet and get the current time and date.
        """

        subprocess.call(shlex.split("hwclock -w"))

    # </editor-fold>

    # <editor-fold desc="Region: Bit Operation">

    @staticmethod
    def __test_bit(int_type, offset):
        """
        __test_bit() returns 1, if the bit at 'offset' is one else 0 if the bit is not set.
        
        :param int int_type: Integer value to test 
        :param int offset: Offset value which bit to test
        :return: Integer based value of 0 if bit at 'offset' is not set or 1 if bit is set
        :rtype: int
        """

        mask = 1 << offset
        bit_value = int_type & mask
        if bit_value > 0:
            res = 1
        else:
            res = 0

        return res

    @staticmethod
    def __set_bit(int_type, offset):
        """
        __set_bit() returns an integer with the bit at 'offset' set to 1.

        :param int int_type: Integer value in which to set one bit
        :param int offset: Offset value which bit to set
        :return: Integer with bit set at 'offset'
        :rtype: int
        """

        mask = 1 << offset
        return int_type | mask

    @staticmethod
    def __clear_bit(int_type, offset):
        """
        __clear_bit() returns an integer with the bit at 'offset' cleared, set to 0.

        :param int int_type: Integer value in which to clear one bit
        :param int offset: Offset value which bit to clear
        :return: Integer with bit cleared a 'offset'
        :rtype: int
        """

        mask = ~(1 << offset)
        return int_type & mask

    @staticmethod
    def __toggle_bit(int_type, offset):
        """
        __toggle_bit() returns an integer with the bit at 'offset' inverted, 0 -> 1 and 1 -> 0.

        :param int int_type: Integer value to toggle one bit
        :param int offset: Offset value which bit to toggle
        :return: integer with bit set a 'offset'
        :rtype: int
        """

        mask = 1 << offset
        return int_type ^ mask

    # </editor-fold>
