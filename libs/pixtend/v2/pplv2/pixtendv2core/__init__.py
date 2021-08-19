#!/usr/bin/python
# coding=utf-8

# MIT License
# 
# Copyright (C) 2021 Kontron Electronics GmbH <support@pixtend.de>
# Copyright (C) 2018 Michael Buesch
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

import RPi.GPIO as GPIO
from abc import ABCMeta, abstractmethod
import time
import spidev
import threading

__author__ = "Robin Turner"
__version__ = "0.1.4"


class PiXtendV2Core:
    """
    The PiXtendV2 base class can be used to build PiXtend V2 modules, which use the same code base, thus reducing
    code multiplication. This class implements the most basic functions, properties and infrastructure needed to
    create a PiXtend V2 module in Python. This class cannot run on its own, it needs to be inherited by a child
    class and the functions '_pack_spi_data' and '_unpack_spi_data' have to be implemented there as these are
    defined as abstract functions and cannot be used directly.
    Furthermore, for the SPI data transfer to work correctly, the child class needs to implement a list[int] variable
    which holds the data which is sent to the microcontroller. The needed list[int] length can be found in the
    SPI protocol specification of the PiXtend V2 board.
    """

    __metaclass__ = ABCMeta

    # <editor-fold desc="Class defines">

    # Class defines
    MC_RESET_PIN = 23
    SPI_ENABLE_PIN = 24
    SPI_NOT_FOUND = -1
    SPI_SPEED = 700000

    # Definitions to make use of settings easier
    PIXTENDV2S_MODEL = 83
    PIXTENDV2L_MODEL = 76
    ON = True
    OFF = False
    RS232 = 0
    RS485 = 0
    DAC_A = 0
    DAC_B = 1
    SERVO_MODE = 0
    PWM_MODE = 1
    GPIO_INPUT = 0
    GPIO_OUTPUT = 1
    GPIO_DHT11 = 2
    GPIO_DHT22 = 3
    DHT11 = 0
    DHT22 = 1
    COM_INTERVAL_DHT = 0.03
    COM_INTERVAL_DEFAULT = 0.03
    COM_INTERVAL_MINIMUM = 0.01
    JUMPER_5V = 0
    JUMPER_10V = 1
    WDT_OFF = 0
    WDT_16MS = 16
    WDT_32MS = 32
    WDT_64MS = 64
    WDT_125MS = 125
    WDT_250MS = 250
    WDT_500MS = 500
    WDT_1S = 1000
    WDT_2S = 2000
    WDT_4S = 4000
    WDT_8S = 8000
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

    def __init__(self, spi_speed=SPI_SPEED, com_interval=COM_INTERVAL_DEFAULT, model=0, disable_dac=False):
        """
        Constructor of the PixtendV2 base class. Setup SPI communication, base variables and start
        the cyclic communication using a timer from the threading module.

        :param int spi_speed: SPI communication speed, default is 700000
        :param float com_interval: Cycle time of the communication, how often is data exchanged between the
                                   Raspberry Pi and the microcontroller on the PiXtend board, default is 30 ms
        :param int model: The model number of the PiXtend board which is used. S = 83 and L = 76
        :param bool disable_dac: The DAC (analog output) can be disabled to allow the use of the CAN-Bus on the
                                 PiXtend V2 -L- board
        """

        if model == 0:
            raise RuntimeError("PiXtend V2 model parameter cannot be 0 (Zero), a valid model number is needed")
        if model != self.PIXTENDV2S_MODEL and model != self.PIXTENDV2L_MODEL:
            raise RuntimeError("PiXtend V2 model parameter is not a valid model!")
        if model == self.PIXTENDV2S_MODEL:
            if com_interval < 0.0025:
                raise RuntimeError("PiXtend V2 communication interval (com_interval) is too short! \
                    The minimum value is 0.0025 seconds or 2.5 ms.")
        if model == self.PIXTENDV2L_MODEL:
            if com_interval < 0.005:
                raise RuntimeError("PiXtend V2 communication interval (com_interval) is too short! \
                    The minimum value is 0.005 seconds or 5 ms.")       
        if spi_speed < 100000 or spi_speed > 700000:
            raise RuntimeError("PiXtend V2 SPI speed cannot be lower than 100000 Hz or greater than 700000 Hz! \
                Choose a fitting SPI speed value.")

        # Default SPI frequency is 700 kHz
        self.__spi_speed = spi_speed
        # The microcontroller is on the SPI Master 0 with CS 0
        # self.__spi_channel = 0
        # self.__spi_cs = 0
        self.__spi = None

        # Initialize variables
        self.__thread = None
        self.__thread_interval = com_interval
        self.__use_fahrenheit = False
        self.__is_spi_open = False

        # General data common for all boards, internal variables and statistics
        self._gpio_dht11 = 0
        self._crc_header_in_errors = 0
        self.spi_transfers_begin = 0
        self.spi_transfers = 0
        self._model_in_error = False
        self._is_crc_header_error = False

        # Data which goes to the microcontroller, common for all PiXtend V2 boards
        self.__model_out = model
        self.__uc_mode = 0
        self.__uc_ctrl0 = 0
        self.__uc_ctrl1 = 0
        self._gpio_ctrl = 0
        self._gpio_out = 0
        self._gpio_debounce01 = 0
        self._gpio_debounce23 = 0
        self._temp0_raw_value = 0
        self._temp1_raw_value = 0
        self._temp2_raw_value = 0
        self._temp3_raw_value = 0
        self._humid0_raw_value = 0
        self._humid1_raw_value = 0
        self._humid2_raw_value = 0
        self._humid3_raw_value = 0

        # Data which comes from the microcontroller, common for all PiXtend V2 boards
        self.__firmware = 0
        self.__hardware = 0
        self.__model_in = 0
        self._gpio_in = 0
        self.__uc_state = 0
        self.__uc_warnings = 0

        # Variables for the DAC, the DAC is on the SPI Master 0 with CS 1
        self.__spi_dac = None
        self.__is_spi_dac_open = False
        self.__analog0_dac_value = 0
        self.__analog1_dac_value = 0

        # Turn RPi GPIO warnings off in case GPIOs are still/already in use
        GPIO.setwarnings(False)
        # Change layout to BCM
        GPIO.setmode(GPIO.BCM)
        # Set SPI Enable pin to output
        GPIO.setup(self.SPI_ENABLE_PIN, GPIO.OUT)
        GPIO.setup(self.MC_RESET_PIN, GPIO.OUT)
        # Activate SPI Enable, allow communication
        GPIO.output(self.SPI_ENABLE_PIN, True)
        # Turn microcontroller reset pin off
        GPIO.output(self.MC_RESET_PIN, False)

        # Open SPI Master 0 with CS 0 for communication with the microcontroller
        self._open(0, 0, self.__spi_speed)

        # Check if we need the DAC or if it has been disabled, to make way for the CAN-Bus
        self.__disable_dac = disable_dac
        if not self.__disable_dac:
            # Open SPI Master 0 with CS 1 for communication with the DAC
            self._open_dac(0, 1, self.__spi_speed)

        # Start the endless communication loop to send and receive data from the PiXtend V2's microcontroller
        # at the given interval. This is done automatically. The user should only need to call the _loop_stop()
        # function if the main program needs to exit, otherwise the communication has to go on.
        self._loop_start()

    @staticmethod
    def _dump(obj):
        for attr in dir(obj):
            if hasattr(obj, attr):
                print("obj.%s = %s" % (attr, getattr(obj, attr)))

    def __del__(self):
        """
        Destructor of the Pixtend V2 class. Delete objects.
        """

        self.__thread = None
        self.__spi = None
        self.__spi_dac = None

    def _transfer_spi_data(self, data=None):
        """
        Transfer data to microcontroller all in one block, data needs to be passed
        as list of int's (bytes), the return value is also a list of int's (bytes) of the same int/byte count as was
        sent to the microcontroller. The value of each list element must be between 0 and 255 (8 bits).

        :param List[int] data:
        :return: Response from the microcontroller with a list of int's (bytes) and length of n elements. The length n
        is the same length as the 'data' variable.
        :rtype: List[int]
        """

        # data is mutable, None is used as default, if nothing gets passed, throw error!!!
        if data is None:
            raise ValueError("The parameter 'data' cannot be empty!", "Method _transfer_spi_data was called!")

        if self.__is_spi_open:
            resp = self.__spi.xfer2(data)  # transfer byte data in one block with cs always active during transfer
        else:
            raise IOError("SPI not initialized!!! Use open method first!", "Method _transfer_spi_data was called!")

        return resp

    def _reset_microcontroller(self):
        """
        DO NOT USE DURING NORMAL OPERATION - Internal function to reset the MC for testing
        """

        GPIO.output(self.MC_RESET_PIN, True)
        time.sleep(1)
        GPIO.output(self.MC_RESET_PIN, False)
        time.sleep(1)

    def _open(self, spi_channel=0, spi_cs=0, spi_speed=700000):
        """
        Open SPI Master 0 with Chip Select 0 on the Raspberry Pi to start the communication with the microcontroller
        on the PiXtend V2 board.

        :param int spi_channel: Number of the SPI master, default is 0, optional parameter
        :param int spi_cs:  Chip Select (CS) for the SPI master, default is 0, optional parameter
        :param int spi_speed:  SPI frequency, default 700 kHz, optional parameter
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
            # self.__uc_version_get()
        else:
            raise IOError("Error: SPI 0 CS 0 already opened!")

    def _close(self):
        """
        Close SPI device, clean up Raspberry Pi GPIO device and set all variables to None, False or 0.
        """

        # Stop the timer thread which calls the _auto_mode() function automatically in the background
        try:
            self._loop_stop()
        except:
            pass
        
        # Initialize variables
        self.__thread_terminate = False
        self.__thread = None
        self.__use_fahrenheit = False
        
        self.__model_out = 0
        self.__uc_mode = 0
        self.__uc_ctrl0 = 0
        self.__uc_ctrl1 = 0
        self._gpio_ctrl = 0
        self.__firmware = 0
        self.__hardware = 0
        self.__model_in = 0
        self.__uc_state = 0
        self.__uc_warnings = 0
        
        try:
            GPIO.cleanup()
        except:
            pass

        try:
            self.__spi.close()
        except:
            pass

        del self.__spi
        self.__spi = None
        self.__is_spi_open = False

        try:
            if not self.__disable_dac:
                self.__spi_dac.close()
        except:
            pass

        del self.__spi_dac
        self.__spi_dac = None
        self.__is_spi_dac_open = False
        self.__analog0_dac_value = 0
        self.__analog1_dac_value = 0

    def _loop_forever(self):
        """
        This function call loops in an infinite loop every n milliseconds. It process SPI communication by
        calling the _auto_mode() function.
        """

        # Get a precise timer for our interval timing.
        # Try to get a timer that is guaranteed to only monotonically increase.
        if hasattr(time, "clock_gettime") and hasattr(time, "CLOCK_MONOTONIC_RAW"):
            timer = lambda: time.clock_gettime(time.CLOCK_MONOTONIC_RAW)
        elif hasattr(time, "monotonic"):
            timer = time.monotonic
        else:
            timer = time.time

        next_auto_mode = timer()
        while not self.__thread_terminate:

            # Call the auto mode function
            self._auto_mode()

            # Calculate when the next auto mode is due.
            next_auto_mode += self.__thread_interval
            now = timer()
            if next_auto_mode < now:
                # The next auto_mode already is in the past.
                # We probably are not executing fast enough
                # to hold the deadlines.
                # But sleep at least one millisecond to give other threads
                # a chance. Otherwise we might starve them.
                next_auto_mode = now + 1e-3

            # Calculate the duration to the next auto mode deadline
            # and sleep until then.
            time.sleep(next_auto_mode - now)

    def _loop_start(self):
        """
        This is part of the internal threading. Call this once to start a new thread to process SPI data.
        """
        if self.__thread is not None:
            return -1

        self.__thread_terminate = False
        self.__thread = threading.Thread(target=self._loop_forever)
        self.__thread.daemon = False
        self.__thread.start()

    def _loop_stop(self):
        """
        This is part of the internal threading. Call this once to stop the SPI thread previously created with
        _loop_start(). This call will block until the SPI thread finishes.
        """
        if self.__thread is None:
            return -1

        self.__thread_terminate = True
        self.__thread.join()
        self.__thread = None

    # <editor-fold desc="Region: PiXtend V2 Configuration, Settings and Information">

    @property
    def firmware(self):
        """
        Get the microcontroller's firmware version.

        :return: Current value
        :rtype: int
        """

        return self.__firmware

    @property
    def hardware(self):
        """
        Get the PiXtend V2 hardware revision.

        :return: Current value
        :rtype: int
        """

        return self.__hardware

    @property
    def model_in(self):
        """
        Get the PiXtend V2 model information from the microcontroller.

        :return: Current value
        :rtype: int
        """

        return self.__model_in

    @property
    def save_state(self):
        """
        Get or Set the microcontroller's SaveState bit in case the computer has to shutdown or needs to reboot.
        Settings this property to True will halt the microcontroller and a reset is needed in order to start any
        communication again.

        :return: Current value
        :rtype: bool
        :raises ValueError: If the passed value is not True or False
        """

        return self.test_bit(self.__uc_ctrl1, self.BIT_0) == 1

    @save_state.setter
    def save_state(self, value):
        if value is True or value is False:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: True or False")

        if value:
            self.__uc_ctrl1 = self.set_bit(self.__uc_ctrl1, self.BIT_0)
        if not value:
            self.__uc_ctrl1 = self.clear_bit(self.__uc_ctrl1, self.BIT_0)

    @property
    def retain_copy(self):
        """
        Get or Set the microcontroller's Retain memory option to copy incoming data to the outgoing data
        stream. This way the data which will be stored on the microcontroller, in the event of a sudden power loss,
        can be verified that the data really reaches the microcontroller and that values are correct. This option is
        mainly intended for debugging, but can be used by anyone.

        :return: Current value
        :rtype: bool
        :raises ValueError: If the passed value is not True or False
        """

        return self.test_bit(self.__uc_ctrl1, self.BIT_1) == 1

    @retain_copy.setter
    def retain_copy(self, value):
        if value is True or value is False:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: True or False")

        if value:
            self.__uc_ctrl1 = self.set_bit(self.__uc_ctrl1, self.BIT_1)
        if not value:
            self.__uc_ctrl1 = self.clear_bit(self.__uc_ctrl1, self.BIT_1)

    @property
    def retain_enable(self):
        """
        Get or Set the microcontroller's Retain memory option to enabled. With this option active a specified amount of
        data will be stored in the microcontroller's flash memory in the event of a sudden power loss. The exact amount
        of int's/bytes which a PiXtend V2 board can store can be found in the SPI protocol specifications.

        :return: Current value
        :rtype: bool
        :raises ValueError: If the passed value is not True or False
        """

        return self.test_bit(self.__uc_ctrl1, self.BIT_2) == 1

    @retain_enable.setter
    def retain_enable(self, value):
        if value is True or value is False:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: True or False")

        if value is True:
            self.__uc_ctrl1 = self.set_bit(self.__uc_ctrl1, self.BIT_2)
        if value is False:
            self.__uc_ctrl1 = self.clear_bit(self.__uc_ctrl1, self.BIT_2)

    @property
    def state_led_off(self):
        """
        Get or Set if the State LED (L1) on the PiXtend V2 board is on or off.
        True turns the LED off and False leave the State LED (L1) on.

        :return: Current value
        :rtype: bool
        :raises ValueError: If the passed value is not True or False
        """

        return self.test_bit(self.__uc_ctrl1, self.BIT_3) == 1

    @state_led_off.setter
    def state_led_off(self, value):
        if value is True or value is False:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: True or False")

        if value is True:
            self.__uc_ctrl1 = self.set_bit(self.__uc_ctrl1, self.BIT_3)
        if value is False:
            self.__uc_ctrl1 = self.clear_bit(self.__uc_ctrl1, self.BIT_3)

    @property
    def watchdog(self):
        """
        Get or Set the PiXtend V2 watchdog option. WDT_OFF or 0 ms means the watchdog is disabled. One of the
        following time values 16 ms, 32 ms, 64 ms, 125 ms, 250 ms, 500 ms, 1000 ms (1s), 2000 ms (2s), 4000 ms (4s)
        and 8000 ms (8s) turns the watchdog function in the microcontroller on. If no SPI communication occurs within
        this time frame, the microcontroller will stop working and goes into save state. Only a reset or power cycle
        will bring it back to life once it has entered this stage.

        :return: Current value
        :rtype: int
        :raises ValueError: If the passed value is not one of the following: 16, 32, 64, 125, 250, 500, 1000,
        2000, 4000 or 8000
        """

        # WD is off
        if self.test_bit(self.__uc_ctrl0, self.BIT_0) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 0 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_OFF
        # WD is set to 16 ms
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 0 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_16MS
        # WD is set to 32 ms
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 1 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_32MS
        # WD is set to 64 ms
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 1 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_64MS
        # WD is set to 125 ms
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 0 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_125MS
        # WD is set to 250 ms
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 0 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_250MS
        # WD is set to 500 ms
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 1 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_500MS
        # WD is set to 1 sec
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 1 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 0:
            wdt_value = self.WDT_1S
        # WD is set to 2 seconds
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 0 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 1:
            wdt_value = self.WDT_2S
        # WD is set to 4 seconds
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 1 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 0 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 1:
            wdt_value = self.WDT_4S
        # WD is set to 8 seconds
        elif self.test_bit(self.__uc_ctrl0, self.BIT_0) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_1) == 1 and \
                self.test_bit(self.__uc_ctrl0, self.BIT_2) == 0 and self.test_bit(self.__uc_ctrl0, self.BIT_3) == 1:
            wdt_value = self.WDT_8S
        else:
            wdt_value = self.WDT_OFF

        return wdt_value

    @watchdog.setter
    def watchdog(self, value):
        if value == self.WDT_OFF or value == self.WDT_16MS or value == self.WDT_32MS or value == self.WDT_64MS or \
                value == self.WDT_125MS or value == self.WDT_250MS or value == self.WDT_500MS or value == self.WDT_1S \
                or value == self.WDT_2S or value == self.WDT_4S or value == self.WDT_8S:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only:  16, 32, 64, 125, 250, \
                500, 1000, 2000, 4000 or 8000")

        if value == self.WDT_OFF:
            self.clear_bit(self.__uc_ctrl0, self.BIT_0)
            self.clear_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_16MS:
            self.set_bit(self.__uc_ctrl0, self.BIT_0)
            self.clear_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_32MS:
            self.clear_bit(self.__uc_ctrl0, self.BIT_0)
            self.set_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_64MS:
            self.set_bit(self.__uc_ctrl0, self.BIT_0)
            self.set_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_125MS:
            self.clear_bit(self.__uc_ctrl0, self.BIT_0)
            self.clear_bit(self.__uc_ctrl0, self.BIT_1)
            self.set_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_250MS:
            self.set_bit(self.__uc_ctrl0, self.BIT_0)
            self.clear_bit(self.__uc_ctrl0, self.BIT_1)
            self.set_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_500MS:
            self.clear_bit(self.__uc_ctrl0, self.BIT_0)
            self.set_bit(self.__uc_ctrl0, self.BIT_1)
            self.set_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_1S:
            self.set_bit(self.__uc_ctrl0, self.BIT_0)
            self.set_bit(self.__uc_ctrl0, self.BIT_1)
            self.set_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_2S:
            self.clear_bit(self.__uc_ctrl0, self.BIT_0)
            self.clear_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.set_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_4S:
            self.set_bit(self.__uc_ctrl0, self.BIT_0)
            self.clear_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.set_bit(self.__uc_ctrl0, self.BIT_3)
        elif value == self.WDT_8S:
            self.clear_bit(self.__uc_ctrl0, self.BIT_0)
            self.set_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.set_bit(self.__uc_ctrl0, self.BIT_3)
        else:
            self.clear_bit(self.__uc_ctrl0, self.BIT_0)
            self.clear_bit(self.__uc_ctrl0, self.BIT_1)
            self.clear_bit(self.__uc_ctrl0, self.BIT_2)
            self.clear_bit(self.__uc_ctrl0, self.BIT_3)

    @property
    def uc_warnings(self):
        """
        The UCWarnings byte from the microcontroller contains information of the following internal errors:
        Bit 1: RetainCRCError       - Signals a CRC error in the retain data in the microcontroller
        Bit 2: RetainVoltageError   - The supply voltage is below 19 volts, the Retain memory option cannot be used.

        :return: Current value
        :rtype: int
        """
        return self.__uc_warnings

    @property
    def uc_state(self):
        """
        The UCState byte from the microcontroller contains information of the following internal states:
            Bit 0: Run      - The microcontroller is up and running, this is just a helper bit
            Bit 4: Error0   - Bit 0 of the 4 bit error number from the microcontroller. Together with the next 3
            Bit 5: Error1   - bits a 4 bit number can be formed which results in an error number which is
            Bit 6: Error2   - listed in the SPI protocol specification or the software manual.
            Bit 7: Error3

        :return: Current value
        :rtype: int
        """
        return self.__uc_state

    @property
    def crc_header_in_error(self):
        """
        Get the error state of the CRC check performed on the SPI data header. If the CRC comparision is wrong
        the value will be True, if the header of the SPI data is correct, the value will be False.

        :return: Current value, False means no error, True means the header is not correct, error
        :rtype: bool
        """

        return self._is_crc_header_error

    @property
    def crc_header_in_error_counter(self):
        """
        Get the error counter of the CRC check performed on the incoming SPI data header.

        :return: Current value
        :rtype: int
        """

        return self._crc_header_in_errors
        
    @property
    def model_in_error(self):
        """
        Get the result of the comparison between the configured model, supplied by the child class through the init
        function (constructor) when the object is created, and the reported model by the microcontroller.
        If the configured model and the reported model match, the value will be False,
        if they don't match, the value will be True and signifies an error.

        :return: Current value, False means no error, True means the reported model does not match
        :rtype: bool
        """

        return self._model_in_error

    # </editor-fold>

    # <editor-fold desc="Region: GPIO Configuration and Handling">

    @property
    def gpio_pullups_enable(self):
        """
        Enable or Disable the GPIO 0-3 pullups if the GPIOs are configured as outputs and the pullups are needed.
        Setting this property to True enables the pullups, if it is set to False the pullups remain off.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self.__uc_ctrl1, self.BIT_4) == 1

    @gpio_pullups_enable.setter
    def gpio_pullups_enable(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        if value is True:
            self.__uc_ctrl1 = self.set_bit(self.__uc_ctrl1, self.BIT_4)
        if value is False:
            self.__uc_ctrl1 = self.clear_bit(self.__uc_ctrl1, self.BIT_4)

    def _gpio_config_get(self, gpio_dir, gpio_temp):
        """
        Get the current configuration value, 0 (Input), 1 (Output), 2 (DHT11) or 3 (DHT22), for the given bits in
        the GPIOCtrl byte.

        :param int gpio_dir: Bit number to read in GPIOCtrl to see if a GPIO is Input or Output
        :param int gpio_temp: Bit number to read in GPIOCtrl to see if a GPIO is a sensor input (DHT11 or DHT22)
        :return: Current configuration value: 0, 1, 2 or 3
        :rtype: int
        """
        value = 0
        if self.test_bit(self._gpio_ctrl, gpio_dir) == 0 and self.test_bit(self._gpio_ctrl, gpio_temp) == 0:
            value = self.GPIO_INPUT
        if self.test_bit(self._gpio_ctrl, gpio_dir) == 1 and self.test_bit(self._gpio_ctrl, gpio_temp) == 0:
            value = self.GPIO_OUTPUT
        if self.test_bit(self._gpio_ctrl, gpio_dir) == 0 and self.test_bit(self._gpio_ctrl, gpio_temp) == 1:
            if self.test_bit(self._gpio_dht11, gpio_dir):
                value = self.GPIO_DHT11
            else:
                value = self.GPIO_DHT22
        return value

    def _gpio_config_set(self, gpio_dir, gpio_temp, value):
        """
        Set the configuration for a GPIO to the given configuration. 0 (Input), 1 (Output), 2 (DHT11) or 3 (DHT22)

        :param int gpio_dir: Bit number to change in GPIOCtrl if GPIO is Input or Output
        :param int gpio_temp: Bit number to change in GPIOCtrl if GPIO is sensor input (DHT11/DHT22)
        :param int value: Configuration value: 0, 1, 2 or 3
        """
        if value == self.GPIO_INPUT:
            self._gpio_ctrl = self.clear_bit(self._gpio_ctrl, gpio_dir)
            self._gpio_ctrl = self.clear_bit(self._gpio_ctrl, gpio_temp)
        if value == self.GPIO_OUTPUT:
            self._gpio_ctrl = self.set_bit(self._gpio_ctrl, gpio_dir)
            self._gpio_ctrl = self.clear_bit(self._gpio_ctrl, gpio_temp)
        if value == self.GPIO_DHT11 or value == self.GPIO_DHT22:
            self._gpio_ctrl = self.clear_bit(self._gpio_ctrl, gpio_dir)
            self._gpio_ctrl = self.set_bit(self._gpio_ctrl, gpio_temp)

        if value == self.GPIO_DHT11:
            self._gpio_dht11 = self.set_bit(self._gpio_dht11, gpio_dir)
        else:
            self._gpio_dht11 = self.clear_bit(self._gpio_dht11, gpio_dir)

    def _gpio_check_value(self, value):
        """
        Check if the given value is 1, 2, 3 or 4 meaning that a GPIO will be configured as an Input, Output,
        DHT11 sensor or DHT22 sensor input.
        :rtype: bool
        """
        if value == self.GPIO_INPUT or value == self.GPIO_OUTPUT or value == self.GPIO_DHT11 or \
                value == self.GPIO_DHT22:
            return True
        else:
            return False

    @property
    def gpio0_ctrl(self):
        """
        Get or Set the configuration of GPIO 0. Possible values are 0 (Input), 1 (Output), 2 (DHT11) or 3 (DHT22).

        :return: Current configuration
        :rtype: int
        :raises ValueError: If the passed value is not 0, 1, 2 or 3
        """

        return self._gpio_config_get(self.BIT_0, self.BIT_4)

    @gpio0_ctrl.setter
    def gpio0_ctrl(self, value):
        if self._gpio_check_value(value) is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 (Input), 1 (Output), \
                2 (DHT11) or 3 (DHT22)")

        self._gpio_config_set(self.BIT_0, self.BIT_4, value)

    @property
    def gpio1_ctrl(self):
        """
        Get or Set the configuration of GPIO 1. Possible values are 0 (Input), 1 (Output), 2 (DHT11) or 3 (DHT22).

        :return: Current configuration
        :rtype: int
        :raises ValueError: If the passed value is not 0, 1, 2 or 3
        """

        return self._gpio_config_get(self.BIT_1, self.BIT_5)

    @gpio1_ctrl.setter
    def gpio1_ctrl(self, value):
        if self._gpio_check_value(value) is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 (Input), 1 (Output), \
                2 (DHT11) or 3 (DHT22)")

        self._gpio_config_set(self.BIT_1, self.BIT_5, value)

    @property
    def gpio2_ctrl(self):
        """
        Get or Set the configuration of GPIO 2. Possible values are 0 (Input), 1 (Output), 2 (DHT11) or 3 (DHT22).

        :return: Current configuration
        :rtype: int
        :raises ValueError: If the passed value is not 0, 1, 2  or 3
        """

        return self._gpio_config_get(self.BIT_2, self.BIT_6)

    @gpio2_ctrl.setter
    def gpio2_ctrl(self, value):
        if self._gpio_check_value(value) is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 (Input), 1 (Output), \
                2 (DHT11) or 3 (DHT22)")

        self._gpio_config_set(self.BIT_2, self.BIT_6, value)

    @property
    def gpio3_ctrl(self):
        """
        Get or Set the configuration of GPIO 3. Possible values are 0 (Input), 1 (Output), 2 (DHT11) or 3 (DHT22).

        :return: Current configuration
        :rtype: int
        :raises ValueError: If the passed value is not 0, 1, 2 or 3
        """

        return self._gpio_config_get(self.BIT_3, self.BIT_7)

    @gpio3_ctrl.setter
    def gpio3_ctrl(self, value):
        if self._gpio_check_value(value) is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 (Input), 1 (Output), \
                2 (DHT11) or 3 (DHT22)")

        self._gpio_config_set(self.BIT_3, self.BIT_7, value)

    # </editor-fold>

    # <editor-fold desc="Region: GPIO In/Out">

    # **************************************************************************
    # GPIO Control - GPIO In/Out
    # **************************************************************************

    def _gpio_out_change(self, value, bit_num):
        """
        Change the value of a single bit in an INT variable given by bit_num to the
        value given by value.

        :param bool value: Value of the bit, False = off and True = on
        :param int bit_num: Bit to set or to clear, parameter is zero based
        """

        if value is False:
            self._gpio_out = self.clear_bit(self._gpio_out, bit_num)
        if value is True:
            self._gpio_out = self.set_bit(self._gpio_out, bit_num)

    @property
    def gpio0(self):
        """
        Get or Set the state of GPIO 0. The value False means 'off' and a value of True means 'on'.

        Example:
        p.gpio0 = p.ON # Turns the GPIO on
        p.gpio0 = p.OFF # Turns the GPIO off
        or use
        p.gpio0 = True # Turns the GPIO on
        p.gpio0 = False # Turns the GPIO off

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._gpio_in, self.BIT_0) == 1

    @gpio0.setter
    def gpio0(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")
        bit_num = self.BIT_0
        # Check if a GPIO pin is configured as output or if not if the GPIO PullUps have been enabled
        if self.test_bit(self._gpio_ctrl, bit_num) == 1 or (self.test_bit(self._gpio_ctrl, bit_num) == 0 and self.test_bit(self.__uc_ctrl1, self.BIT_4) == 1):
            self._gpio_out_change(value, bit_num)
        else:
            raise IOError("IOError: GPIO 0 configured as INPUT! Cannot use as OUTPUT or PullUps setting is wrong!")

    @property
    def gpio1(self):
        """
        Get or Set the state of GPIO 1. The value False means 'off' and a value of True means 'on'.

        Example:
        p.gpio1 = p.ON # Turns the GPIO on
        p.gpio1 = p.OFF # Turns the GPIO off
        or use
        p.gpio1 = True # Turns the GPIO on
        p.gpio1 = False # Turns the GPIO off

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._gpio_in, self.BIT_1) == 1

    @gpio1.setter
    def gpio1(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")
        bit_num = self.BIT_1
        # Check if a GPIO pin is configured as output or if not if the GPIO PullUps have been enabled
        if self.test_bit(self._gpio_ctrl, bit_num) == 1 or (self.test_bit(self._gpio_ctrl, bit_num) == 0 and self.test_bit(self.__uc_ctrl1, self.BIT_4) == 1):
            self._gpio_out_change(value, bit_num)
        else:
            raise IOError("IOError: GPIO 1 configured as INPUT! Cannot use as OUTPUT or PullUps setting is wrong!")

    @property
    def gpio2(self):
        """
        Get or Set the state of GPIO 2. The value False means 'off' and a value of True means 'on'.

        Example:
        p.gpio2 = p.ON # Turns the GPIO on
        p.gpio2 = p.OFF # Turns the GPIO off
        or use
        p.gpio2 = True # Turns the GPIO on
        p.gpio2 = False # Turns the GPIO off

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._gpio_in, self.BIT_2) == 1

    @gpio2.setter
    def gpio2(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")
        bit_num = self.BIT_2
        # Check if a GPIO pin is configured as output or if not if the GPIO PullUps have been enabled
        if self.test_bit(self._gpio_ctrl, bit_num) == 1 or (self.test_bit(self._gpio_ctrl, bit_num) == 0 and self.test_bit(self.__uc_ctrl1, self.BIT_4) == 1):
            self._gpio_out_change(value, bit_num)
        else:
            raise IOError("IOError: GPIO 2 configured as INPUT! Cannot use as OUTPUT or PullUps setting is wrong!")

    @property
    def gpio3(self):
        """
        Get or Set the state of GPIO 3. The value False means 'off' and a value of True means 'on'.

        Example:
        p.gpio3 = p.ON # Turns the GPIO on
        p.gpio3 = p.OFF # Turns the GPIO off
        or use
        p.gpio3 = True # Turns the GPIO on
        p.gpio3 = False # Turns the GPIO off

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._gpio_in, self.BIT_3) == 1

    @gpio3.setter
    def gpio3(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")
        bit_num = self.BIT_3
        # Check if a GPIO pin is configured as output or if not if the GPIO PullUps have been enabled
        if self.test_bit(self._gpio_ctrl, bit_num) == 1 or (self.test_bit(self._gpio_ctrl, bit_num) == 0 and self.test_bit(self.__uc_ctrl1, self.BIT_4) == 1):
            self._gpio_out_change(value, bit_num)
        else:
            raise IOError("IOError: GPIO 3 configured as INPUT! Cannot use as OUTPUT or PullUps setting is wrong!")
            
    # </editor-fold>

    # <editor-fold desc="Region: Temperature Inputs 0 - 3">

    # **************************************************************************
    # Temperature Inputs 0 - 3
    # **************************************************************************

    @property
    def use_fahrenheit(self):
        """
        Get or Set if the conversion of the temperature raw value should be done in Fahrenheit.
        Default is 'False', meaning by getting the temperature from temp0 to temp3
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

        :return: Current value
        :rtype: int
        """

        return self._temp0_raw_value

    @property
    def temp_input1_raw(self):
        """
        Get the temperature raw value from temperature input 1.

        :return: Current value
        :rtype: int
        """

        return self._temp1_raw_value

    @property
    def temp_input2_raw(self):
        """
        Get the temperature raw value from temperature input 2.

        :return: Current value
        :rtype: int
        """

        return self._temp2_raw_value

    @property
    def temp_input3_raw(self):
        """
        Get the temperature raw value from temperature input 3.

        :return: Current value
        :rtype: int
        """

        return self._temp3_raw_value

    @property
    def temp0(self):
        """
        Get the converted temperature value from temperature input 0 from a DHT11 or DHT22 sensor.

        :return: Current value
        :rtype: float
        """

        factor = 1.0

        if self._gpio_config_get(self.BIT_0, self.BIT_4) == self.GPIO_DHT22:
            value = self.temp_input0_raw
            if self.test_bit(value, self.BIT_15) == 1:
                value = self.clear_bit(value, self.BIT_15)
                factor = -1.0

            if self.__use_fahrenheit:
                return ((float(value) * 1.8) + 32) * factor
            else:
                return (float(value) / 10.0) * factor
        elif self._gpio_config_get(self.BIT_0, self.BIT_4) == self.GPIO_DHT11:
            if self.__use_fahrenheit:
                return (float(self.temp_input0_raw / 256) * 1.8) + 32
            else:
                return float(self.temp_input0_raw / 256)
        else:
            return 0.0

    @property
    def temp1(self):
        """
        Get the converted temperature value from temperature input 1 from a DHT11 or DHT22 sensor.

        :return: Current value
        :rtype: float
        """

        factor = 1.0

        if self._gpio_config_get(self.BIT_1, self.BIT_5) == self.GPIO_DHT22:
            value = self.temp_input1_raw
            if self.test_bit(value, self.BIT_15) == 1:
                value = self.clear_bit(value, self.BIT_15)
                factor = -1.0

            if self.__use_fahrenheit:
                return ((float(value) * 1.8) + 32) * factor
            else:
                return (float(value) / 10.0) * factor
        elif self._gpio_config_get(self.BIT_1, self.BIT_5) == self.GPIO_DHT11:
            if self.__use_fahrenheit:
                return (float(self.temp_input1_raw / 256) * 1.8) + 32
            else:
                return float(self.temp_input1_raw / 256)
        else:
            return 0.0

    @property
    def temp2(self):
        """
        Get the converted temperature value from temperature input 2 from a DHT11 or DHT22 sensor.

        :return: Current value
        :rtype: float
        """

        factor = 1.0

        if self._gpio_config_get(self.BIT_2, self.BIT_6) == self.GPIO_DHT22:
            value = self.temp_input2_raw
            if self.test_bit(value, self.BIT_15) == 1:
                value = self.clear_bit(value, self.BIT_15)
                factor = -1.0

            if self.__use_fahrenheit:
                return ((float(value) * 1.8) + 32) * factor
            else:
                return (float(value) / 10.0) * factor
        elif self._gpio_config_get(self.BIT_2, self.BIT_6) == self.GPIO_DHT11:
            if self.__use_fahrenheit:
                return (float(self.temp_input2_raw / 256) * 1.8) + 32
            else:
                return float(self.temp_input2_raw / 256)
        else:
            return 0.0

    @property
    def temp3(self):
        """
        Get the converted temperature value from temperature input 3 from a DHT11 or DHT22 sensor.

        :return: Current value
        :rtype: float
        """

        factor = 1.0

        if self._gpio_config_get(self.BIT_3, self.BIT_7) == self.GPIO_DHT22:
            value = self.temp_input3_raw
            if self.test_bit(value, self.BIT_15) == 1:
                value = self.clear_bit(value, self.BIT_15)
                factor = -1.0

            if self.__use_fahrenheit:
                return ((float(value) * 1.8) + 32) * factor
            else:
                return (float(value) / 10.0) * factor
        elif self._gpio_config_get(self.BIT_3, self.BIT_7) == self.GPIO_DHT11:
            if self.__use_fahrenheit:
                return (float(self.temp_input3_raw / 256) * 1.8) + 32
            else:
                return float(self.temp_input3_raw / 256)
        else:
            return 0.0

    # </editor-fold>

    # <editor-fold desc="Region: Humidity Inputs 0 - 3">

    # **************************************************************************
    # Humidity Inputs 0 - 3
    # **************************************************************************

    @property
    def hum_input0_raw(self):
        """
        Get the humidity raw value from humidity input 0.

        :return: Current value
        :rtype: int
        """

        return self._humid0_raw_value

    @property
    def hum_input1_raw(self):
        """
        Get the humidity raw value from humidity input 1.

        :return: Current value
        :rtype: int
        """

        return self._humid1_raw_value

    @property
    def hum_input2_raw(self):
        """
        Get the humidity raw value from humidity input 2.

        :return: Current value
        :rtype: int
        """

        return self._humid2_raw_value

    @property
    def hum_input3_raw(self):
        """
        Get the humidity raw value from humidity input 3.

        :return: Current value
        :rtype: int
        """

        return self._humid3_raw_value

    @property
    def humid0(self):
        """
        Get the converted humidity value from humidity input 0 if a DHT11/DHT22 sensor is physically attached.

        :return: Current value
        :rtype: float
        """

        if self._gpio_config_get(self.BIT_0, self.BIT_4) == self.GPIO_DHT22:
            return float(self.hum_input0_raw) / 10.0
        elif self._gpio_config_get(self.BIT_0, self.BIT_4) == self.GPIO_DHT11:
            return float(self.hum_input0_raw / 256)
        else:
            return 0.0

    @property
    def humid1(self):
        """
        Get the converted humidity value from humidity input 1 if a DHT11/DHT22 sensor is physically attached.

        :return: Current value
        :rtype: float
        """

        if self._gpio_config_get(self.BIT_1, self.BIT_5) == self.GPIO_DHT22:
            return float(self.hum_input1_raw) / 10.0
        elif self._gpio_config_get(self.BIT_1, self.BIT_5) == self.GPIO_DHT11:
            return float(self.hum_input1_raw / 256)
        else:
            return 0.0

    @property
    def humid2(self):
        """
        Get the converted humidity value from humidity input 2 if a DHT11/DHT22 sensor is physically attached.

        :return: Current value
        :rtype: float
        """

        if self._gpio_config_get(self.BIT_2, self.BIT_6) == self.GPIO_DHT22:
            return float(self.hum_input2_raw) / 10.0
        elif self._gpio_config_get(self.BIT_2, self.BIT_6) == self.GPIO_DHT11:
            return float(self.hum_input2_raw / 256)
        else:
            return 0.0

    @property
    def humid3(self):
        """
        Get the converted humidity value from humidity input 3 if a DHT11/DHT22 sensor is physically attached.

        :return: Current value
        :rtype: float
        """

        if self._gpio_config_get(self.BIT_3, self.BIT_7) == self.GPIO_DHT22:
            return float(self.hum_input3_raw) / 10.0
        elif self._gpio_config_get(self.BIT_3, self.BIT_7) == self.GPIO_DHT11:
            return float(self.hum_input3_raw / 256)
        else:
            return 0.0

    # </editor-fold>

    # <editor-fold desc="Region: DAC handling">

    def _open_dac(self, spi_channel=0, spi_cs=1, spi_speed=SPI_SPEED):
        """
        Open SPI Master 0 with Chip Select 1 on the Raspberry Pi to start the communication
        with the DAC on the PiXtend V2 board.

        :param int spi_channel: Number of the SPI master, default is 0, optional parameter
        :param int spi_cs: Chip Select (CS) for the SPI master for the DAC, default is 1, optional parameter
        :param int spi_speed: SPI frequency, default 700 kHz, optional parameter
        :raises IOError: If SPI bus has already been opened
        """

        # Check if we are allowed to use the DAC
        if self.__disable_dac:
            raise IOError("The DAC cannot be used, it has been disabled!", "Method _open_dac was called!")

        self.__spi_channel = spi_channel
        self.__spi_cs = spi_cs
        self.__spi_speed = spi_speed

        # Set the dac gain permanently to 0
        # 0 = 2x (VOUT = 2 * VREF * D/4096),  where internal VREF = 2.048V.
        # self.__analog0_dac_value = self.clear_bit(self.__analog0_dac_value, 1)
        # self.__analog_dac_value.bits.bit1 = 0

        # Set the dac output shutdown control bit permanently to 1
        # 1 = Active mode operation. VOUT is available.
        # self.__analog1_dac_value = self.set_bit(self.__analog1_dac_value, 2)
        # self.__analog_dac_value.bits.bit2 = 1

        # Open SPI bus
        if not self.__is_spi_dac_open:
            try:
                self.__spi_dac = spidev.SpiDev(self.__spi_channel, self.__spi_cs)
                self.__spi_dac.open(self.__spi_channel, self.__spi_cs)
                self.__spi_dac.max_speed_hz = self.__spi_speed
                self.__is_spi_dac_open = True
            except:
                raise IOError("Could not open SPI 0 CS 1, no DAC available!")
        else:
            raise IOError("SPI 0 CS 1 already opened!!!")

    def _transfer_spi_dac_data(self, value0=0, value1=0):
        """
        Transfer data to the DAC on the PiXtend V2 board all in one block, the DAC does not return anything.
        The DAC expects 2 bytes in a special format, see MCP4812 manual for more details.

        :param int value0: First byte for the DAC
        :param int value1: Second byte for the DAC
        """

        # Check if we are allowed to use the DAC
        if self.__disable_dac:
            raise IOError("The DAC cannot be used, it has been disabled!", "Method _transfer_spi_dac_data was called!")

        # Build data list to send to the DAC.
        to_send = [value0, value1]

        if self.__is_spi_dac_open:
            # transfer byte data in one block with cs always active during transfer
            resp = self.__spi_dac.xfer2(to_send)
        else:
            raise IOError("SPI for DAC not initialized!!! Use _open_dac method first!",
                          "Method _transfer_spi_dac_data was called!")

        return resp

    def set_dac_output(self, dac_channel=DAC_A, value=0):
        """
        Set the analog output value for the chosen DAC. The value 0 or constant DAC_A selects DAC A which is
        "Analog Out 0" and the value 1 or constant DAC_B selects DAC B which is "Analog Out 1".
        Example:
        Selecting and setting DAC A:
        p.set_dac_output (p.DAC_A, 512)

        Selecting and setting DAC B:
        p.set_dac_output (p.DAC_B, 256)

        :param int dac_channel: Number of the DAC to set the new value to
        :param int value: Output value for the chosen DAC.
        :raises ValueError: If value is smaller then 0 or larger then 1023
        """

        # Check if we are allowed to use the DAC
        if self.__disable_dac:
            raise IOError("The DAC cannot be used, it has been disabled!", "Method set_dac_output was called!")

        if 0 <= dac_channel <= 1:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 0 for DAC A or 1 \
                for DAC B")

        if 0 <= value <= 1023:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 10bit values max. 1023")

        temp_value = value

        # Copy the 10 relevant bits from the user var to the DAC MCP4812 data format.
        # The first 2 bits in the DAC 16 bit data format are unused! Therefore we start with bit2.
        # See the DAC manual for more details.
        temp_value = temp_value << 2
        temp_value = self.clear_bit(temp_value, self.BIT_0)
        temp_value = self.clear_bit(temp_value, self.BIT_1)

        # bit 15 A/B: DAC A or DAC B Selection bit
        if dac_channel == self.DAC_A:
            temp_value = self.clear_bit(temp_value, self.BIT_15)
        if dac_channel == self.DAC_B:
            temp_value = self.set_bit(temp_value, self.BIT_15)

        # bit 14 Don't care
        # temp_value.bits.bit14 = 0
        temp_value = self.clear_bit(temp_value, self.BIT_14)
        # bit 13 Output Gain Selection bit, this is set permanently to 0
        # 0 = 2x (VOUT = 2 * VREF * D/4096),  where internal VREF = 2.048V.
        # temp_value.bits.bit13 = self.__analog_dac_value.bits.bit1
        temp_value = self.clear_bit(temp_value, self.BIT_13)
        # Set the dac output shutdown control bit (bit 12) permanently to 1
        # 1 = Active mode operation. VOUT is available.
        # temp_value.bits.bit12 = self.__analog_dac_value.bits.bit2
        temp_value = self.set_bit(temp_value, self.BIT_12)

        # Split the int value (should be max. 16 bits) into 2 individual bytes to send via SPI
        c, f = divmod(temp_value, 1 << 8)

        # Send the 2 bytes to the DAC via SPI
        self._transfer_spi_dac_data(c, f)


    @property
    def analog_out0(self):
        """
        Get or Set the value of the Digital Analog Converter (DAC) for Analog Output 0.
        This function wraps the 'set_dac_output' function, this way only one value has
        to be provided, the DAC selection is automatic.
        Value range 0..1023 for 0V to 10V.

        Example:
        p.analog_out0 = 512
        myvalue = p.analog_out0

        :return: Current value
        :rtype: int
        """

        return self.__analog0_dac_value

    @analog_out0.setter
    def analog_out0(self, value):
        if 0 <= value <= 1023:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 10bit values max. 1023")

        self.__analog0_dac_value = value
        self.set_dac_output (self.DAC_A, self.__analog0_dac_value)
        
    @property
    def analog_out1(self):
        """
        Get or Set the value of the Digital Analog Converter (DAC) for Analog Output 1.
        This function wraps the 'set_dac_output' function, this way only one value has
        to be provided, the DAC selection is automatic.
        Value range 0..1023 for 0V to 10V.

        Example:
        p.analog_out1 = 255        
        myvalue = p.analog_out1

        :return: Current value
        :rtype: int
        """

        return self.__analog1_dac_value

    @analog_out1.setter
    def analog_out1(self, value):
        if 0 <= value <= 1023:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: 10bit values max. 1023")

        self.__analog1_dac_value = value
        self.set_dac_output (self.DAC_B, self.__analog1_dac_value)

    # </editor-fold>

    # <editor-fold desc="Region: Bit Operation">

    @staticmethod
    def test_bit(int_type, offset):
        """
        test_bit() returns 1, if the bit at 'offset' is one else 0 if the bit is not set.

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
    def set_bit(int_type, offset):
        """
        set_bit() returns an integer with the bit at 'offset' set to 1.

        :param int int_type: Integer value in which to set one bit
        :param int offset: Offset value which bit to set
        :return: Integer with bit set at 'offset'
        :rtype: int
        """

        mask = 1 << offset
        return int_type | mask

    @staticmethod
    def clear_bit(int_type, offset):
        """
        clear_bit() returns an integer with the bit at 'offset' cleared, set to 0.

        :param int int_type: Integer value in which to clear one bit
        :param int offset: Offset value which bit to clear
        :return: Integer with bit cleared a 'offset'
        :rtype: int
        """

        mask = ~(1 << offset)
        return int_type & mask

    @staticmethod
    def toggle_bit(int_type, offset):
        """
        toggle_bit() returns an integer with the bit at 'offset' inverted, 0 -> 1 and 1 -> 0.

        :param int int_type: Integer value to toggle one bit within
        :param int offset: Offset value which bit to toggle
        :return: integer with bit toggled at 'offset'
        :rtype: int
        """

        mask = 1 << offset
        return int_type ^ mask

    # </editor-fold>

    @abstractmethod
    def _pack_spi_data(self):
        """"
        Return a list of int's (bytes) which can be sent via SPI to the PiXtend V2 uC for processing
        """
        pass

    @abstractmethod
    def _unpack_spi_data(self, data=None):
        """"
        Check the list of int's (bytes) in the variable 'data' which came in via SPI from the
        PiXtend V2 uC for processing. Assign the int's (bytes) to the correct individual variables for further use.
        """
        pass

    # <editor-fold desc="Region: Auto Mode and data handling">

    @staticmethod
    def _calc_crc16(bycrc, bydata):
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

    def _build_header(self, data=None):
        """
        This function builds the header for the SPI data which is sent to the microcontroller and then calculates the
        CRC info for it. The information is stored in the list variable 'data'. The value 'None' is used as default,
        if nothing gets passed by accident an error is thrown.

        :type data: List[int]
        :return: List which was passed to the function, but now includes the SPI header data and CRC
        :raises ValueError: If passed 'data' variable is None or length is shorter then 8 elements
        """
        if data is None:
            raise ValueError("The parameter 'data' cannot be empty!", "Method _build_header was called!")

        if len(data) < 8:
            raise ValueError("The parameter 'data' has not enough list elements! Min. 9 elements are required.",
                             "Method _build_header was called!")

        # Assign common data
        data[0] = self.__model_out
        data[1] = self.__uc_mode
        data[2] = self.__uc_ctrl0
        data[3] = self.__uc_ctrl1
        data[4] = 0
        data[5] = 0
        data[6] = 0

        # Calculate CRC16 Transmit Checksum
        crc_sum = 0xFFFF

        for i in range(0, 7, 1):
            crc_sum = self._calc_crc16(crc_sum, data[i])

        data[7] = crc_sum & 0xFF  # CRC Low Byte
        data[8] = (crc_sum >> 8) & 0xFF  # CRC High Byte

        return data

    def _split_header(self, data=None):
        """
        This function checks the incoming SPI data stream header using a CRC check and extracts the basic information
        supplied by the microcontroller and stores the information in individual variables for further use.

        :type data: List[int]
        :return: List of int's which came from the microcontroller or if a CRC error is detected, the data is zeroed. /
            The user has to check the error flags and discard the data if a header CRC error is found.
        :raises ValueError: If passed 'data' variable is None or length is shorter then 9 elements
        """
        if data is None:
            raise ValueError("The parameter 'data' cannot be empty!", "Method _split_header was called!")

        if len(data) < 8:
            raise ValueError("The parameter 'data' has not enough list elements! Min. 9 elements are required.",
                             "Method _split_header was called!")

        arlen = len(data)

        # Calculate CRC16 for received data to check against received values which the microcontroller calculated
        header_crc_sum_calc = 0xFFFF
        for i in range(0, 7, 1):
            header_crc_sum_calc = self._calc_crc16(header_crc_sum_calc, data[i])
        # Get header crc value from microcontroller
        header_crc_sum_rx = (data[8] << 8) + data[7]
        # Check if both CRC values match...
        if header_crc_sum_rx != header_crc_sum_calc:
            # Error: CRC of received header and CRC values from the microcontroller do not match.
            self._crc_header_in_errors += 1
            self._is_crc_header_error = True
            ret_val = [0] * arlen
            return ret_val
        # The CRC values match, we can continue
        self._is_crc_header_error = False
        # Now we have to check the model
        if self.__model_out != data[2]:
            self._model_in_error = True
            ret_val = [0] * arlen
            return ret_val
        # Model check was good, now we can get the remaining data from the list of int's (bytes)
        self._model_in_error = False

        # Get the firmware version, i.e. 1, 2, 3 and so on
        self.__firmware = data[0]
        # Get the hardware version, i.e. 20, 21, 22 and so on
        self.__hardware = data[1]
        # Get reported model, as it was programmed in to the microcontroller
        self.__model_in = data[2]
        # Get the microcontroller state
        self.__uc_state = data[3]
        # Get the microcontroller warnings
        self.__uc_warnings = data[4]

        return data

    # **************************************************************************
    # Automatic Mode for PiXtend V2 - Threaded Communication
    # **************************************************************************

    def _auto_mode(self):
        """
        Method for the auto(matic) mode data transfer. The settings and values of all applicable
        properties like outputs, GPIO and PWM configuration for PiXtend V2 are sent to the microcontroller
        in one block and states and values of all digital and analog inputs are received as response.
        """
        if self.__is_spi_open:
            self.spi_transfers_begin += 1

            # Get the data to be sent to the uC
            data = self._pack_spi_data()
            # Build header - CRC calculation
            data = self._build_header(data)
            # Transfer spi data to microcontroller
            response = self._transfer_spi_data(data)
            # Check header crc and unpack header data
            response = self._split_header(response)
            # Call unpack function to split up incoming data, but it will be defined by the child class
            self._unpack_spi_data(response)

            self.spi_transfers += 1

    # </editor-fold>
