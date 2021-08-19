#!/usr/bin/python
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

from pixtendv2core import PiXtendV2Core

__author__ = "Robin Turner"
__version__ = "0.1.4"


class PiXtendV2S(PiXtendV2Core):
    """
    The PiXtendV2S class is based off of the PiXtendV2Core class, which provides basic and most common functions for
    PiXtend V2. This class must implement the abstract methods _unpack_spi_data and _pack_spi_data otherwise there
    can be no functioning data communication and no usable object at runtime.
    
    Notice:
    Only ONE single instance of this class is allowed per Raspberry Pi. Do not create multiple objects in the
    same or a different program. This will lead to inconsistent states of the PiXtend board used. The PPLv2 and the
    SPI Bus of the Raspberry Pi cannot handle multiple instances or objects.
    """

    # Class defines
    _MAX_SPI_DATA = 67
    _MAX_RETAIN_DATA = 32
    _SPI_DATA = [0] * _MAX_SPI_DATA

    def __init__(self, spi_speed=PiXtendV2Core.SPI_SPEED, com_interval=PiXtendV2Core.COM_INTERVAL_DEFAULT,
                 model=PiXtendV2Core.PIXTENDV2S_MODEL, disable_dac=False):
        """
        Constructor of the PixtendV2S class. Create needed variables to store the settings and values for the PiXtend V2
        board which are transferred via SPI to the on-board microcontroller. The the core class (PiXtendV2Core) does
        not provide all needed variables and functions, only the basic and most common functions of the PiXtend V2
        system. This class has to build and supply the rest.

        :param int spi_speed: SPI communication speed, default is 700000
        :param float com_interval: Cycle time of the communication, how often is data exchanged between the
                                   Raspberry Pi and the microcontroller on the PiXtend board, default is 30 ms
        :param int model: The model number of the PiXtend board which is used. S = 83 and L = 76
        :param bool disable_dac: The DAC (analog output) can be disabled to allow the use of the CAN-Bus on the
                                 PiXtend V2 -L- board
        """

        # Output data from RPi -> uC
        self._digital_in_debounce01 = 0
        self._digital_in_debounce23 = 0
        self._digital_in_debounce45 = 0
        self._digital_in_debounce67 = 0
        self._digital_out = 0
        self._relay_out = 0
        self._pwm0_ctrl0 = 0
        self._pwm0_ctrl1 = 0
        self._pwm0a = 0
        self._pwm0b = 0
        self._pwm1_ctrl0 = 0
        self._pwm1_ctrl1 = 0
        self._pwm1a = 0
        self._pwm1b = 0
        self._retain_data_out = [0] * self._MAX_RETAIN_DATA

        # Input data from uC -> RPi
        self._digital_in = 0
        self._analog_in0 = 0
        self._analog_in1 = 0
        self._analog_in0_jumper_setting = True
        self._analog_in1_jumper_setting = True
        self._retain_data_in = [0] * self._MAX_RETAIN_DATA

        # Flag if the CRC check on the received SPI data resulted in error or if all data is usable.
        self._is_crc_data_in_error = False
        self._crc_data_errors = 0

        super(PiXtendV2S, self).__init__(spi_speed, com_interval, model, disable_dac)

    def close(self):
        """
        The 'close' function needs to be called to terminate the asynchronous SPI communication in the background and to
        close the SPI driver. This function must be called before the PiXtendV2S object is destroyed in the program
        it is used in.
        """
        self._close()

    @property
    def crc_data_in_error(self):
        """
        Get the error state of the CRC check performed on the incoming SPI data.

        :return: Current value, False means no error, True means the data is not correct, error
        :rtype: bool
        """

        return self._is_crc_data_in_error

    @property
    def crc_data_in_error_counter(self):
        """
        Get the error counter of the CRC check performed on the incoming SPI data.

        :return: Current value
        :rtype: int
        """

        return self._crc_data_errors  
        
    # <editor-fold desc="Region: RelayOut - Relays 0 - 3">

    @property
    def relay0(self):
        """
        Get or Set the state of relay 0. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """
        return self.test_bit(self._relay_out, self.BIT_0) == 1

    @relay0.setter
    def relay0(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_0
        if value is self.OFF:
            self._relay_out = self.clear_bit(self._relay_out, bit_num)
        if value is self.ON:
            self._relay_out = self.set_bit(self._relay_out, bit_num)

    @property
    def relay1(self):
        """
        Get or Set the state of relay 1. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """
        return self.test_bit(self._relay_out, self.BIT_1) == 1

    @relay1.setter
    def relay1(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_1
        if value is self.OFF:
            self._relay_out = self.clear_bit(self._relay_out, bit_num)
        if value is self.ON:
            self._relay_out = self.set_bit(self._relay_out, bit_num)

    @property
    def relay2(self):
        """
        Get or Set the state of relay 2. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """
        return self.test_bit(self._relay_out, self.BIT_2) == 1

    @relay2.setter
    def relay2(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_2
        if value is self.OFF:
            self._relay_out = self.clear_bit(self._relay_out, bit_num)
        if value is self.ON:
            self._relay_out = self.set_bit(self._relay_out, bit_num)

    @property
    def relay3(self):
        """
        Get or Set the state of relay 3. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """
        return self.test_bit(self._relay_out, self.BIT_3) == 1

    @relay3.setter
    def relay3(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError(
                "Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_3
        if value is self.OFF:
            self._relay_out = self.clear_bit(self._relay_out, bit_num)
        if value is self.ON:
            self._relay_out = self.set_bit(self._relay_out, bit_num)

    # </editor-fold>

    # <editor-fold desc="Region: DigitalOut - Digital Outputs 0 - 3">

    # **************************************************************************
    # Digital Outputs on the PiXtend V2 -S- Board
    # **************************************************************************

    @property
    def digital_out0(self):
        """
        Get or Set the state of digital output 0. A value False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_out, self.BIT_0) == 1

    @digital_out0.setter
    def digital_out0(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError(
                "Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_0
        if value is self.OFF:
            self._digital_out = self.clear_bit(self._digital_out, bit_num)
        if value is self.ON:
            self._digital_out = self.set_bit(self._digital_out, bit_num)

    @property
    def digital_out1(self):
        """
        Get or Set the state of digital output 1. A value False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_out, self.BIT_1) == 1

    @digital_out1.setter
    def digital_out1(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError(
                "Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_1
        if value is self.OFF:
            self._digital_out = self.clear_bit(self._digital_out, bit_num)
        if value is self.ON:
            self._digital_out = self.set_bit(self._digital_out, bit_num)

    @property
    def digital_out2(self):
        """
        Get or Set the state of digital output 2. A value False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_out, self.BIT_2) == 1

    @digital_out2.setter
    def digital_out2(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError(
                "Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_2
        if value is self.OFF:
            self._digital_out = self.clear_bit(self._digital_out, bit_num)
        if value is self.ON:
            self._digital_out = self.set_bit(self._digital_out, bit_num)

    @property
    def digital_out3(self):
        """
        Get or Set the state of digital output 3. A value False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_out, self.BIT_3) == 1

    @digital_out3.setter
    def digital_out3(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError(
                "Value error!, Value " + str(value) + " not allowed! - Use only: False = off, True = on")

        bit_num = self.BIT_3
        if value is self.OFF:
            self._digital_out = self.clear_bit(self._digital_out, bit_num)
        if value is self.ON:
            self._digital_out = self.set_bit(self._digital_out, bit_num)

    # </editor-fold>

    # <editor-fold desc="Region: DigitalIn - Digital Inputs 0 - 7">

    # **************************************************************************
    # Digital Inputs on the PiXtend V2 -S- Board
    # **************************************************************************

    @property
    def digital_in0(self):
        """
        Get the state of digital input 0. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_0) == 1

    @property
    def digital_in1(self):
        """
        Get the state of digital input 1. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_1) == 1

    @property
    def digital_in2(self):
        """
        Get the state of digital input 2. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_2) == 1

    @property
    def digital_in3(self):
        """
        Get the state of digital input 3. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_3) == 1

    @property
    def digital_in4(self):
        """
        Get the state of digital input 4. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_4) == 1

    @property
    def digital_in5(self):
        """
        Get the state of digital input 5. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_5) == 1

    @property
    def digital_in6(self):
        """
        Get the state of digital input 6. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_6) == 1

    @property
    def digital_in7(self):
        """
        Get the state of digital input 7. A value of False means 'off' and a value of True means 'on'.

        :return: Current value
        :rtype: bool
        """

        return self.test_bit(self._digital_in, self.BIT_7) == 1

    # </editor-fold>

    # <editor-fold desc="Region: PWM0 and PWM1 - Control and Values">

    # <editor-fold desc="Region: Servo Control ">

    # **************************************************************************
    # Servo Control
    # **************************************************************************

    @property
    def servo0(self):
        """
        Get or Set the value for PWM 0 channel A in Servo Mode. Possible values are 0 to 16000.

        :return: Current value
        :rtype: int
        """

        return self._pwm0a

    @servo0.setter
    def servo0(self, value):
        if 0 <= value <= 16000:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 16000")

        if (self.test_bit(self._pwm0_ctrl0, self.BIT_0) == 0) and (self.test_bit(self._pwm0_ctrl0, self.BIT_1) == 0):
            self._pwm0a = value
        else:
            raise ValueError("Mode error! Servo Mode was used, but PWM0 is not configured for Servo Mode!")

    @property
    def servo1(self):
        """
        Get or Set the value for PWM 0 channel B in Servo Mode. Possible values are 0 to 16000.

        :return: Current value
        :rtype: int
        """

        return self._pwm0b

    @servo1.setter
    def servo1(self, value):
        if 0 <= value <= 16000:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 16000")

        if (self.test_bit(self._pwm0_ctrl0, self.BIT_0) == 0) and (self.test_bit(self._pwm0_ctrl0, self.BIT_1) == 0):
            self._pwm0b = value
        else:
            raise ValueError("Mode error! Servo Mode was used, but PWM0 is not configured for Servo Mode!")

    @property
    def servo2(self):
        """
        Get or Set the value for PWM 1 channel A in Servo Mode. Possible values are 0 to 125.

        :return: Current value
        :rtype: int
        """

        return self._pwm1a

    @servo2.setter
    def servo2(self, value):
        if 0 <= value <= 125:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 125")

        if (self.test_bit(self._pwm1_ctrl0, self.BIT_0) == 0) and (self.test_bit(self._pwm1_ctrl0, self.BIT_1) == 0):
            self._pwm1a = value
        else:
            raise ValueError("Mode error! Servo Mode was used, but PWM1 is not configured for Servo Mode!")

    @property
    def servo3(self):
        """
        Get or Set the value for PWM 1 channel B in Servo Mode. Possible values are 0 to 125.

        :return: Current value
        :rtype: int
        """

        return self._pwm1b

    @servo3.setter
    def servo3(self, value):
        if 0 <= value <= 125:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 125")

        if (self.test_bit(self._pwm1_ctrl0, self.BIT_0) == 0) and (self.test_bit(self._pwm1_ctrl0, self.BIT_1) == 0):
            self._pwm1b = value
        else:
            raise ValueError("Mode error! Servo Mode was used, but PWM1 is not configured for Servo Mode!")

    # </editor-fold>

    # <editor-fold desc="Region: PWM0Ctrl0, PWM0Ctrl1, PWM1Ctrl0 and PWM1Ctrl1">

    @property
    def pwm0_ctrl0(self):
        """
        Get or Set the PWM0Ctrl0 property. This int value controls the configuration of PWM0 channel A & B.
        This property has the following bits which control PWM0:
        Bit 0 - Mode0
        Bit 1 - Mode1
        Bit 3 - EnableA
        Bit 4 - EnableB
        Bit 5 - Prescaler0
        Bit 6 - Prescaler1
        Bit 7 - Prescaler2

        See the software manual for more details on this property and it's bits.
        The int value must be between 0 and 255.

        :return: Current PWM0Ctrl0 value.
        :rtype: int
        """
        return self._pwm0_ctrl0

    @pwm0_ctrl0.setter
    def pwm0_ctrl0(self, value):
        if 0 <= value <= 255:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 255.")
        self._pwm0_ctrl0 = value

    @property
    def pwm0_ctrl1(self):
        """
        Get or Set the PWM0Ctrl1 property. It is used to set the frequency for PWM0 channels A & B, but only if the
        selected PWM mode makes use of this value. See the software manual for more information on this topic.
        The int value must be between 0 and 65535 (16 bits).

        :return: Current PWM0Ctrl1 value
        :rtype: int
        """
        return self._pwm0_ctrl1

    @pwm0_ctrl1.setter
    def pwm0_ctrl1(self, value):
        if 0 <= value <= 65535:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 65535.")
        self._pwm0_ctrl1 = value

    @property
    def pwm1_ctrl0(self):
        """
        Get or Set the PWM1Ctrl0 property. This int value controls the configuration of PWM1 channel A & B.
        This property has the following bits which control PWM1:
        Bit 0 - Mode0
        Bit 1 - Mode1
        Bit 3 - EnableA
        Bit 4 - EnableB
        Bit 5 - Prescaler0
        Bit 6 - Prescaler1
        Bit 7 - Prescaler2

        See the software manual for more details on this property and it's bits.
        The int value must be between 0 and 255.

        :return: Current PWM1Ctrl0 value.
        :rtype: int
        """
        return self._pwm1_ctrl0

    @pwm1_ctrl0.setter
    def pwm1_ctrl0(self, value):
        if 0 <= value <= 255:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 255.")
        self._pwm1_ctrl0 = value

    @property
    def pwm1_ctrl1(self):
        """
        Get or Set the PWM1Ctrl1 property. It is used to set the frequency for PWM1 channels A & B, but only if the
        selected PWM mode makes use of this value. See the software manual for more information on this topic.
        The int value must be between 0 and 255 (8 bits).

        :return: Current PWM1Ctrl1 value
        :rtype: int
        """
        return self._pwm1_ctrl1

    @pwm1_ctrl1.setter
    def pwm1_ctrl1(self, value):
        if 0 <= value <= 255:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 255.")
        self._pwm1_ctrl1 = value

    # </editor-fold>

    # <editor-fold desc="Region: PWM0 Channel A & B and PWM1 Channel A & B values ">

    @property
    def pwm0a(self):
        """
        Get or Set the value for PWM0 channel A. This property can be used to set the duty cycle of PWM0, however the
        exact usage depends on the PWM mode selected through the property pwm0_ctrl0. The value must be between
        0 and 65535, more information on the usage of PWM with PiXtend V2 -S- can be found in the software manual.

        :return: Current PWM0 channel A value
        :rtype: int
        """
        return self._pwm0a

    @pwm0a.setter
    def pwm0a(self, value):
        if 0 <= value <= 65535:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 65535.")
        self._pwm0a = value

    @property
    def pwm0b(self):
        """
        Get or Set the value for PWM0 channel B. This property can be used to set the duty cycle of PWM0, however the
        exact usage depends on the PWM mode selected through the property pwm0_ctrl0. The value must be between
        0 and 65535, more information on the usage of PWM with PiXtend V2 -S- can be found in the software manual.

        :return: Current PWM0 channel B value
        :rtype: int
        """
        return self._pwm0b

    @pwm0b.setter
    def pwm0b(self, value):
        if 0 <= value <= 65535:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 65535.")
        self._pwm0b = value

    @property
    def pwm1a(self):
        """
        Get or Set the value for PWM1 channel A. This property can be used to set the duty cycle of PWM1, however the
        exact usage depends on the PWM mode selected through the property pwm1_ctrl0. The value must be between
        0 and 255, more information on the usage of PWM with PiXtend V2 -S- can be found in the software manual.

        :return: Current PWM1 channel A value
        :rtype: int
        """
        return self._pwm1a

    @pwm1a.setter
    def pwm1a(self, value):
        if 0 <= value <= 255:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 255.")
        self._pwm1a = value

    @property
    def pwm1b(self):
        """
        Get or Set the value for PWM1 channel B. This property can be used to set the duty cycle of PWM1, however the
        exact usage depends on the PWM mode selected through the property pwm1_ctrl0. The value must be between
        0 and 255, more information on the usage of PWM with PiXtend V2 -S- can be found in the software manual.

        :return: Current PWM1 channel B value
        :rtype: int
        """
        return self._pwm1b

    @pwm1b.setter
    def pwm1b(self, value):
        if 0 <= value <= 255:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use a value from 0 to 255.")
        self._pwm1b = value

    # </editor-fold>

    # </editor-fold>

    # <editor-fold desc="Region: AnalogIn0 and AnalogIn1 - Jumper setting ref 5V / 10 V">

    @property
    def jumper_setting_ai0(self):
        """
        Get or Set the 5 volts / 10 volts jumper setting, depending if the jumper was physically set on the
        PiXtend V2 -S- board or not.
        The library needs to know this setting to perform correct calculations of the raw analog
        value of the analog input 0 when it is converted it's final float value.

        The default setting is 10 volts (True), no jumper set.

        :return: Current jumper setting
        :rtype: bool
        """
        return self._analog_in0_jumper_setting

    @jumper_setting_ai0.setter
    def jumper_setting_ai0(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = 5 volts, \
                True = 10 volts (default)")

        self._analog_in0_jumper_setting = value

    @property
    def jumper_setting_ai1(self):
        """
        Get or Set the 5 volts / 10 volts jumper setting, depending if the jumper was physically set on the
        PiXtend V2 -S- board or not.
        The library needs to know this setting to perform correct calculations of the raw analog
        value of the analog input 1 when it is converted it's final float value.

        The default setting is 10 volts (True), no jumper set.

        :return: Current jumper setting
        :rtype: bool
        """
        return self._analog_in1_jumper_setting

    @jumper_setting_ai1.setter
    def jumper_setting_ai1(self, value):
        if value is False or value is True:
            pass
        else:
            raise ValueError("Value error!, Value " + str(value) + " not allowed! - Use only: False = 5 volts, \
                True = 10 volts (default)")

        self._analog_in1_jumper_setting = value

    @property
    def analog_in0(self):
        """
        Get the value of analog input 0 as a float value converted to volts. The returned value is
        based on the 5 volts / 10 volts jumper setting.

        :return: Current value
        :rtype: float
        """
        if self._analog_in0_jumper_setting is True:
            value = self._analog_in0 * (10.0 / 1024)
        else:
            value = self._analog_in0 * (5.0 / 1024)
        return value

    @property
    def analog_in0_raw(self):
        """
        Get the raw value of analog input 0.

        :return: Current value
        :rtype: int
        """
        return self._analog_in0

    @property
    def analog_in1(self):
        """
        Get the value of analog input 1 as a float value converted to volts. The returned value is
        based on the 5 volts / 10 volts jumper setting.

        :return: Current value
        :rtype: float
        """
        if self._analog_in1_jumper_setting is True:
            value = self._analog_in1 * (10.0 / 1024)
        else:
            value = self._analog_in1 * (5.0 / 1024)
        return value

    @property
    def analog_in1_raw(self):
        """
        Get the raw value of analog input 1.

        :return: Current value
        :rtype: int
        """
        return self._analog_in1

    # </editor-fold>

    # <editor-fold desc="Region: Retain Data - 32 bytes flash storage">

    @property
    def retain_data_out(self):
        """
        From RetainDataOut return a list of 32 int's, each list element has a value between 0 and 255 (byte value).

        :return: list[int]
        """
        return self._retain_data_out

    @retain_data_out.setter
    def retain_data_out(self, value):
        """
        RetainDataOut list consisting of 32 Bytes (int's), each int/byte cannot exceed the value of 255.

        :type value: list[int]
        """
        if type(value) is not list:
            raise ValueError("The passed value is not of type list! RetainDataOut needs to be of type list with 32 \
                             elements each of type int and each element must have a value between 0 and 255.")
        if len(value) < self._MAX_RETAIN_DATA or len(value) > self._MAX_RETAIN_DATA:
            raise ValueError("The retain data out property needs a list with exactly 32 elements of type int!")
        if not all(isinstance(i, int) for i in value):
            raise ValueError("Not all elements are of the same type! Only int is allowed.")
        for i in range(len(value)):
            if (value[i] < 0) or (value[i] > 255):
                raise ValueError("Value of list element too big! Only values between 0 and 255 are allowed!")

        self._retain_data_out = value

    @property
    def retain_data_in(self):
        """
        From RetainDataIn return a list of 32 int's, each list element has a value between 0 and 255 (byte value).
        If the Retain functions was enabled, this list will contain the data previously stored in the microcontroller's
        flash memory. The values will remain there even if the Retain Enable flag is not set.

        :return: list[int]
        """
        return self._retain_data_in

    # </editor-fold>

    def _unpack_spi_data(self, data=None):
        """"
        Check the list of int's (bytes) in the variable 'data' which came in via SPI from the
        PiXtend V2 microcontroller for processing. Assign the int's (bytes) to the correct individual
        variables for further use.
        """

        if data is None:
            raise ValueError("The parameter 'data' cannot be empty!", "Method _unpack_spi_data was called!")

        if len(data) < self._MAX_SPI_DATA:
            raise ValueError("The parameter 'data' has not enough list elements!",
                             "Method _unpack_spi_data was called!")

        # Get data crc value from microcontroller
        data_crc_sum_rx = (data[self._MAX_SPI_DATA-1] << 8) + data[self._MAX_SPI_DATA-2]

        # Calculate CRC16 Receive Checksum
        data_crc_sum_calc = 0xFFFF

        for i in range(9, self._MAX_SPI_DATA-2, 1):
            data_crc_sum_calc = self._calc_crc16(data_crc_sum_calc, data[i])

        # Check if both CRC values match...
        if data_crc_sum_rx != data_crc_sum_calc:
            self._crc_data_errors += 1
            self._is_crc_data_in_error = True
            return

        self._is_crc_data_in_error = False
        # Assign the incoming SPI data bytes to the correct variables for further use.
        data_cnt = 9
        self._digital_in = data[data_cnt]
        data_cnt += 1  # 10
        self._analog_in0 = (data[data_cnt + 1] << 8) + data[data_cnt]  # 11 / 10
        data_cnt += 2  # 12
        self._analog_in1 = (data[data_cnt + 1] << 8) + data[data_cnt]  # 13 / 12
        data_cnt += 2   # 14
        self._gpio_in = data[data_cnt]
        data_cnt += 1   # 15
        self._temp0_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 16 / 15
        data_cnt += 2   # 17
        self._humid0_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 18 / 17
        data_cnt += 2   # 19
        self._temp1_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 20 / 19
        data_cnt += 2   # 21
        self._humid1_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 22 / 21
        data_cnt += 2   # 23
        self._temp2_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 24 / 23
        data_cnt += 2   # 25
        self._humid2_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 26 / 25
        data_cnt += 2   # 27
        self._temp3_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 28 / 27
        data_cnt += 2   # 29
        self._humid3_raw_value = (data[data_cnt + 1] << 8) + data[data_cnt]  # 30 / 29

        data_cnt = 32

        for i in range(0, self._MAX_RETAIN_DATA, 1):
            data_cnt += 1
            self._retain_data_in[i] = data[data_cnt]

    def _pack_spi_data(self):
        """"
        Return a list of int's (bytes) which can be sent via SPI to the PiXtend V2 microcontroller for processing
        """

        # Delete any previous data - clean slate
        self._SPI_DATA = [0] * self._MAX_SPI_DATA

        # Assigning the individual variables to the correct spot in the out going SPI data stream
        data_cnt = 9
        self._SPI_DATA[data_cnt] = self._digital_in_debounce01
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._digital_in_debounce23
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._digital_in_debounce45
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._digital_in_debounce67
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._digital_out
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._relay_out
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._gpio_ctrl
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._gpio_out
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._gpio_debounce01
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._gpio_debounce23
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm0_ctrl0
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm0_ctrl1 & 0xFF  # Low byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = (self._pwm0_ctrl1 >> 8) & 0xFF  # High byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm0a & 0xFF  # Low byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = (self._pwm0a >> 8) & 0xFF  # High byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm0b & 0xFF  # Low byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = (self._pwm0b >> 8) & 0xFF  # High byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm1_ctrl0
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm1_ctrl1 & 0xFF  # Low byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = (self._pwm1_ctrl1 >> 8) & 0xFF  # High byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm1a & 0xFF  # Low byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = (self._pwm1a >> 8) & 0xFF  # High byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = self._pwm1b & 0xFF  # Low byte
        data_cnt += 1
        self._SPI_DATA[data_cnt] = (self._pwm1b >> 8) & 0xFF  # High byte

        for i in range(0, self._MAX_RETAIN_DATA, 1):
            data_cnt += 1
            self._SPI_DATA[data_cnt] = self._retain_data_out[i]

        # Calculate CRC16 Transmit Checksum
        crc_sum = 0xFFFF

        for i in range(9, self._MAX_SPI_DATA-2, 1):
            crc_sum = self._calc_crc16(crc_sum, self._SPI_DATA[i])

        self._SPI_DATA[self._MAX_SPI_DATA-2] = crc_sum & 0xFF  # CRC Low Byte
        self._SPI_DATA[self._MAX_SPI_DATA-1] = (crc_sum >> 8) & 0xFF  # CRC High Byte

        return self._SPI_DATA
