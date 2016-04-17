EESchema Schematic File Version 2
LIBS:power
LIBS:device
LIBS:transistors
LIBS:conn
LIBS:linear
LIBS:regul
LIBS:74xx
LIBS:cmos4000
LIBS:adc-dac
LIBS:memory
LIBS:xilinx
LIBS:microcontrollers
LIBS:dsp
LIBS:microchip
LIBS:analog_switches
LIBS:motorola
LIBS:texas
LIBS:intel
LIBS:audio
LIBS:interface
LIBS:digital-audio
LIBS:philips
LIBS:display
LIBS:cypress
LIBS:siliconi
LIBS:opto
LIBS:atmel
LIBS:contrib
LIBS:valves
LIBS:max485
LIBS:rv3029c2
LIBS:pilc-cache
EELAYER 25 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 4 4
Title "PiLC HAT - Digital I/O"
Date ""
Rev "0.1"
Comp "Michael Buesch <m@bues.ch>"
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
Text HLabel 5100 1850 0    60   Input ~ 0
Q0.0
Text HLabel 5100 2050 0    60   Input ~ 0
Q0.1
Text HLabel 5100 2250 0    60   Input ~ 0
Q0.2
Text HLabel 5100 2450 0    60   Input ~ 0
Q0.3
Text HLabel 5100 2650 0    60   Input ~ 0
Q0.4
Text HLabel 5100 2850 0    60   Input ~ 0
Q0.5
Text HLabel 5100 3050 0    60   Input ~ 0
Q0.6
Text HLabel 5100 3250 0    60   Input ~ 0
Q0.7
Text HLabel 5100 4100 0    60   Input ~ 0
I0.0
Text HLabel 5100 4300 0    60   Input ~ 0
I0.1
Text HLabel 5100 4500 0    60   Input ~ 0
I0.2
Text HLabel 5100 4700 0    60   Input ~ 0
I0.3
Text HLabel 5100 4900 0    60   Input ~ 0
I0.4
Text HLabel 5100 5100 0    60   Input ~ 0
I0.5
Text HLabel 5100 5300 0    60   Input ~ 0
I0.6
Text HLabel 5100 5500 0    60   Input ~ 0
I0.7
$Comp
L CONN_01X08 P3
U 1 1 56DCAC47
P 6500 2550
F 0 "P3" H 6500 3000 50  0000 C CNN
F 1 "OUTPUTS_QB0" V 6600 2550 50  0000 C CNN
F 2 "" H 6500 2550 50  0000 C CNN
F 3 "" H 6500 2550 50  0000 C CNN
	1    6500 2550
	1    0    0    -1  
$EndComp
$Comp
L CONN_01X08 P4
U 1 1 56DCAD37
P 6500 4800
F 0 "P4" H 6500 5250 50  0000 C CNN
F 1 "INPUTS_IB0" V 6600 4800 50  0000 C CNN
F 2 "" H 6500 4800 50  0000 C CNN
F 3 "" H 6500 4800 50  0000 C CNN
	1    6500 4800
	1    0    0    -1  
$EndComp
Wire Wire Line
	6300 2500 5500 2500
Wire Wire Line
	5500 2500 5500 2450
Wire Wire Line
	5500 2450 5100 2450
Wire Wire Line
	6300 2600 5500 2600
Wire Wire Line
	5500 2600 5500 2650
Wire Wire Line
	5500 2650 5100 2650
Wire Wire Line
	6300 2400 5600 2400
Wire Wire Line
	5600 2400 5600 2250
Wire Wire Line
	5600 2250 5100 2250
Wire Wire Line
	6300 2300 5700 2300
Wire Wire Line
	5700 2300 5700 2050
Wire Wire Line
	5700 2050 5100 2050
Wire Wire Line
	6300 2200 5800 2200
Wire Wire Line
	5800 2200 5800 1850
Wire Wire Line
	5800 1850 5100 1850
Wire Wire Line
	6300 2700 5600 2700
Wire Wire Line
	5600 2700 5600 2850
Wire Wire Line
	5600 2850 5100 2850
Wire Wire Line
	6300 2800 5700 2800
Wire Wire Line
	5700 2800 5700 3050
Wire Wire Line
	5700 3050 5100 3050
Wire Wire Line
	6300 2900 5800 2900
Wire Wire Line
	5800 2900 5800 3250
Wire Wire Line
	5800 3250 5100 3250
Wire Wire Line
	6300 4750 5500 4750
Wire Wire Line
	5500 4750 5500 4700
Wire Wire Line
	5500 4700 5100 4700
Wire Wire Line
	6300 4850 5500 4850
Wire Wire Line
	5500 4850 5500 4900
Wire Wire Line
	5500 4900 5100 4900
Wire Wire Line
	6300 4950 5600 4950
Wire Wire Line
	5600 4950 5600 5100
Wire Wire Line
	5600 5100 5100 5100
Wire Wire Line
	6300 5050 5700 5050
Wire Wire Line
	5700 5050 5700 5300
Wire Wire Line
	5700 5300 5100 5300
Wire Wire Line
	6300 5150 5800 5150
Wire Wire Line
	5800 5150 5800 5500
Wire Wire Line
	5800 5500 5100 5500
Wire Wire Line
	6300 4650 5600 4650
Wire Wire Line
	5600 4650 5600 4500
Wire Wire Line
	5600 4500 5100 4500
Wire Wire Line
	6300 4550 5700 4550
Wire Wire Line
	5700 4550 5700 4300
Wire Wire Line
	5700 4300 5100 4300
Wire Wire Line
	6300 4450 5800 4450
Wire Wire Line
	5800 4450 5800 4100
Wire Wire Line
	5800 4100 5100 4100
$EndSCHEMATC
