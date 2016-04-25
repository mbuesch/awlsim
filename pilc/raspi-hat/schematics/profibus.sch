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
Sheet 3 4
Title "PiLC HAT - PROFIBUS-DP PHY"
Date ""
Rev "0.1"
Comp "Michael Buesch <m@bues.ch>"
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L MAX485 U2
U 1 1 56AD7A26
P 6000 4200
F 0 "U2" H 6000 4550 60  0000 C CNN
F 1 "MAX 485 ECPA" H 6000 3850 60  0000 C CNN
F 2 "" H 6000 4200 60  0000 C CNN
F 3 "" H 6000 4200 60  0000 C CNN
	1    6000 4200
	1    0    0    -1  
$EndComp
$Comp
L DB9 J1
U 1 1 56AD7A2D
P 9950 4250
F 0 "J1" H 9950 4800 70  0000 C CNN
F 1 "DB9" H 9950 3700 70  0000 C CNN
F 2 "" H 9950 4250 60  0000 C CNN
F 3 "" H 9950 4250 60  0000 C CNN
	1    9950 4250
	1    0    0    -1  
$EndComp
$Comp
L +5V #PWR37
U 1 1 56AD7A34
P 6700 4050
F 0 "#PWR37" H 6700 3900 50  0001 C CNN
F 1 "+5V" H 6700 4190 50  0000 C CNN
F 2 "" H 6700 4050 60  0000 C CNN
F 3 "" H 6700 4050 60  0000 C CNN
	1    6700 4050
	0    1    1    0   
$EndComp
$Comp
L GND #PWR38
U 1 1 56AD7A3A
P 6700 4350
F 0 "#PWR38" H 6700 4100 50  0001 C CNN
F 1 "GND" H 6700 4200 50  0000 C CNN
F 2 "" H 6700 4350 60  0000 C CNN
F 3 "" H 6700 4350 60  0000 C CNN
	1    6700 4350
	0    -1   -1   0   
$EndComp
$Comp
L GND #PWR43
U 1 1 56AD7A40
P 9400 3850
F 0 "#PWR43" H 9400 3600 50  0001 C CNN
F 1 "GND" H 9400 3700 50  0000 C CNN
F 2 "" H 9400 3850 60  0000 C CNN
F 3 "" H 9400 3850 60  0000 C CNN
	1    9400 3850
	0    1    1    0   
$EndComp
NoConn ~ 9500 3950
NoConn ~ 9500 4050
NoConn ~ 9500 4350
NoConn ~ 9500 4450
NoConn ~ 9500 4650
Text Notes 10300 4650 1    79   ~ 0
PROFIBUS DP
$Comp
L C_Small C6
U 1 1 56AD7A4D
P 6550 3800
F 0 "C6" H 6560 3870 50  0000 L CNN
F 1 "100n" H 6560 3720 50  0000 L CNN
F 2 "" H 6550 3800 60  0000 C CNN
F 3 "" H 6550 3800 60  0000 C CNN
	1    6550 3800
	1    0    0    -1  
$EndComp
$Comp
L GND #PWR36
U 1 1 56AD7A54
P 6550 3600
F 0 "#PWR36" H 6550 3350 50  0001 C CNN
F 1 "GND" H 6550 3450 50  0000 C CNN
F 2 "" H 6550 3600 60  0000 C CNN
F 3 "" H 6550 3600 60  0000 C CNN
	1    6550 3600
	-1   0    0    1   
$EndComp
$Comp
L R R10
U 1 1 56AD7A5A
P 5100 4050
F 0 "R10" V 5180 4050 50  0000 C CNN
F 1 "1k" V 5100 4050 50  0000 C CNN
F 2 "" V 5030 4050 30  0000 C CNN
F 3 "" H 5100 4050 30  0000 C CNN
	1    5100 4050
	0    1    1    0   
$EndComp
$Comp
L GND #PWR32
U 1 1 56AD7A61
P 4850 3300
F 0 "#PWR32" H 4850 3050 50  0001 C CNN
F 1 "GND" H 4850 3150 50  0000 C CNN
F 2 "" H 4850 3300 60  0000 C CNN
F 3 "" H 4850 3300 60  0000 C CNN
	1    4850 3300
	-1   0    0    1   
$EndComp
$Comp
L ZENER D3
U 1 1 56AD7A67
P 4850 3600
F 0 "D3" H 4850 3700 50  0000 C CNN
F 1 "3.3V" H 4850 3500 50  0000 C CNN
F 2 "" H 4850 3600 60  0000 C CNN
F 3 "" H 4850 3600 60  0000 C CNN
	1    4850 3600
	0    -1   -1   0   
$EndComp
$Comp
L R R8
U 1 1 56AD7A6E
P 4600 4050
F 0 "R8" V 4680 4050 50  0000 C CNN
F 1 "1k" V 4600 4050 50  0000 C CNN
F 2 "" V 4530 4050 30  0000 C CNN
F 3 "" H 4600 4050 30  0000 C CNN
	1    4600 4050
	0    1    1    0   
$EndComp
Text HLabel 1650 4350 0    60   Input ~ 0
TxD
Text HLabel 1650 4050 0    60   Input ~ 0
RxD
Text HLabel 1650 4250 0    60   Input ~ 0
TxForceEn
Text Label 2400 4050 0    60   ~ 0
Rx_data
Text Label 2400 4250 0    60   ~ 0
Tx_force_enable
Text Label 2400 4350 0    60   ~ 0
Tx_data
$Comp
L BS170 Q1
U 1 1 56B7AD47
P 5900 2050
F 0 "Q1" H 6100 2125 50  0000 L CNN
F 1 "BS170" H 6100 2050 50  0000 L CNN
F 2 "~" H 6100 1975 50  0000 L CIN
F 3 "" H 5900 2050 50  0000 L CNN
	1    5900 2050
	1    0    0    -1  
$EndComp
$Comp
L R R13
U 1 1 56B7AD4E
P 6000 1500
F 0 "R13" V 6080 1500 50  0000 C CNN
F 1 "1k" V 6000 1500 50  0000 C CNN
F 2 "" V 5930 1500 30  0000 C CNN
F 3 "" H 6000 1500 30  0000 C CNN
	1    6000 1500
	1    0    0    -1  
$EndComp
$Comp
L GND #PWR35
U 1 1 56B7AD55
P 6000 2450
F 0 "#PWR35" H 6000 2200 50  0001 C CNN
F 1 "GND" H 6000 2300 50  0000 C CNN
F 2 "" H 6000 2450 60  0000 C CNN
F 3 "" H 6000 2450 60  0000 C CNN
	1    6000 2450
	1    0    0    -1  
$EndComp
$Comp
L +3V3 #PWR34
U 1 1 56B7AD5B
P 6000 1250
F 0 "#PWR34" H 6000 1100 50  0001 C CNN
F 1 "+3V3" H 6000 1390 50  0000 C CNN
F 2 "" H 6000 1250 60  0000 C CNN
F 3 "" H 6000 1250 60  0000 C CNN
	1    6000 1250
	1    0    0    -1  
$EndComp
$Comp
L R R9
U 1 1 56B7AD61
P 4750 2800
F 0 "R9" V 4830 2800 50  0000 C CNN
F 1 "1k" V 4750 2800 50  0000 C CNN
F 2 "" V 4680 2800 30  0000 C CNN
F 3 "" H 4750 2800 30  0000 C CNN
	1    4750 2800
	0    -1   -1   0   
$EndComp
$Comp
L R R12
U 1 1 56B7AD68
P 5750 2350
F 0 "R12" V 5830 2350 50  0000 C CNN
F 1 "10k" V 5750 2350 50  0000 C CNN
F 2 "" V 5680 2350 30  0000 C CNN
F 3 "" H 5750 2350 30  0000 C CNN
	1    5750 2350
	0    1    1    0   
$EndComp
$Comp
L R R11
U 1 1 57123077
P 5350 3600
F 0 "R11" V 5430 3600 50  0000 C CNN
F 1 "10k" V 5350 3600 50  0000 C CNN
F 2 "" V 5280 3600 50  0000 C CNN
F 3 "" H 5350 3600 50  0000 C CNN
	1    5350 3600
	1    0    0    -1  
$EndComp
$Comp
L +5V #PWR33
U 1 1 571230C0
P 5350 3300
F 0 "#PWR33" H 5350 3150 50  0001 C CNN
F 1 "+5V" H 5350 3440 50  0000 C CNN
F 2 "" H 5350 3300 50  0000 C CNN
F 3 "" H 5350 3300 50  0000 C CNN
	1    5350 3300
	1    0    0    -1  
$EndComp
$Comp
L +5V #PWR41
U 1 1 5712D4DF
P 9350 4550
F 0 "#PWR41" H 9350 4400 50  0001 C CNN
F 1 "+5V" H 9350 4690 50  0000 C CNN
F 2 "" H 9350 4550 50  0000 C CNN
F 3 "" H 9350 4550 50  0000 C CNN
	1    9350 4550
	0    -1   -1   0   
$EndComp
Text Label 9050 4150 0    39   ~ 0
PROFIBUS_A-
Text Label 9050 4250 0    39   ~ 0
PROFIBUS_B+
Text Label 7000 4150 0    39   ~ 0
MAX_B-
Text Label 7000 4250 0    39   ~ 0
MAX_A+
Text Notes 6850 5400 0    60   ~ 0
MAX485:\nA = Non-inverting line\nB = inverting line
Text Notes 6850 5800 0    60   ~ 0
PROFIBUS:\nB = Non-inverting line\nA = inverting line
$Comp
L R R14
U 1 1 571E6DB9
P 7650 2800
F 0 "R14" V 7730 2800 50  0000 C CNN
F 1 "390" V 7650 2800 50  0000 C CNN
F 2 "" V 7580 2800 50  0000 C CNN
F 3 "" H 7650 2800 50  0000 C CNN
	1    7650 2800
	0    1    1    0   
$EndComp
$Comp
L R R15
U 1 1 571E6E48
P 8050 2800
F 0 "R15" V 8130 2800 50  0000 C CNN
F 1 "220" V 8050 2800 50  0000 C CNN
F 2 "" V 7980 2800 50  0000 C CNN
F 3 "" H 8050 2800 50  0000 C CNN
	1    8050 2800
	0    1    1    0   
$EndComp
$Comp
L R R16
U 1 1 571E6E99
P 8450 2800
F 0 "R16" V 8530 2800 50  0000 C CNN
F 1 "390" V 8450 2800 50  0000 C CNN
F 2 "" V 8380 2800 50  0000 C CNN
F 3 "" H 8450 2800 50  0000 C CNN
	1    8450 2800
	0    1    1    0   
$EndComp
$Comp
L Switch_DPST SW1
U 1 1 571E70AF
P 8050 3500
F 0 "SW1" H 8350 3550 50  0000 C CNN
F 1 "EN_term" H 8350 3450 50  0000 C CNN
F 2 "" H 8050 3500 50  0000 C CNN
F 3 "" H 8050 3500 50  0000 C CNN
	1    8050 3500
	0    -1   -1   0   
$EndComp
$Comp
L +5V #PWR39
U 1 1 571E72EF
P 7400 2800
F 0 "#PWR39" H 7400 2650 50  0001 C CNN
F 1 "+5V" H 7400 2940 50  0000 C CNN
F 2 "" H 7400 2800 50  0000 C CNN
F 3 "" H 7400 2800 50  0000 C CNN
	1    7400 2800
	0    -1   -1   0   
$EndComp
$Comp
L GND #PWR40
U 1 1 571E7327
P 8700 2800
F 0 "#PWR40" H 8700 2550 50  0001 C CNN
F 1 "GND" H 8700 2650 50  0000 C CNN
F 2 "" H 8700 2800 60  0000 C CNN
F 3 "" H 8700 2800 60  0000 C CNN
	1    8700 2800
	0    -1   -1   0   
$EndComp
$Comp
L DB9 J2
U 1 1 571E76BB
P 9950 5550
F 0 "J2" H 9950 6100 70  0000 C CNN
F 1 "DB9" H 9950 5000 70  0000 C CNN
F 2 "" H 9950 5550 60  0000 C CNN
F 3 "" H 9950 5550 60  0000 C CNN
	1    9950 5550
	1    0    0    -1  
$EndComp
$Comp
L GND #PWR44
U 1 1 571E76C1
P 9400 5150
F 0 "#PWR44" H 9400 4900 50  0001 C CNN
F 1 "GND" H 9400 5000 50  0000 C CNN
F 2 "" H 9400 5150 60  0000 C CNN
F 3 "" H 9400 5150 60  0000 C CNN
	1    9400 5150
	0    1    1    0   
$EndComp
NoConn ~ 9500 5250
NoConn ~ 9500 5350
NoConn ~ 9500 5650
NoConn ~ 9500 5750
NoConn ~ 9500 5950
Text Notes 10300 5950 1    79   ~ 0
PROFIBUS DP
$Comp
L +5V #PWR42
U 1 1 571E76CE
P 9350 5850
F 0 "#PWR42" H 9350 5700 50  0001 C CNN
F 1 "+5V" H 9350 5990 50  0000 C CNN
F 2 "" H 9350 5850 50  0000 C CNN
F 3 "" H 9350 5850 50  0000 C CNN
	1    9350 5850
	0    -1   -1   0   
$EndComp
Text Label 9050 5450 0    39   ~ 0
PROFIBUS_A-
Text Label 9050 5550 0    39   ~ 0
PROFIBUS_B+
Wire Wire Line
	6500 4050 6700 4050
Wire Wire Line
	6500 4350 6700 4350
Wire Wire Line
	9400 3850 9500 3850
Connection ~ 6550 4050
Wire Wire Line
	6550 3900 6550 4050
Wire Wire Line
	6550 3600 6550 3700
Wire Wire Line
	5500 4150 5450 4150
Wire Wire Line
	1650 4350 5500 4350
Wire Wire Line
	4850 3300 4850 3400
Wire Wire Line
	5250 4050 5500 4050
Wire Wire Line
	4850 3800 4850 4050
Connection ~ 4850 4050
Wire Wire Line
	4750 4050 4950 4050
Wire Wire Line
	1650 4050 4450 4050
Wire Wire Line
	1650 4250 5500 4250
Wire Wire Line
	5450 4150 5450 4250
Connection ~ 5450 4250
Wire Wire Line
	6000 2450 6000 2250
Wire Wire Line
	6000 1850 6000 1650
Wire Wire Line
	6000 1250 6000 1350
Wire Wire Line
	6000 1750 6450 1750
Connection ~ 6000 1750
Wire Wire Line
	5900 2350 6000 2350
Connection ~ 6000 2350
Wire Wire Line
	5600 2350 5500 2350
Wire Wire Line
	5500 2350 5500 2100
Connection ~ 5500 2100
Wire Wire Line
	6450 1750 6450 2800
Wire Wire Line
	4150 2800 4150 4250
Wire Wire Line
	4150 2800 4600 2800
Wire Wire Line
	6450 2800 4900 2800
Wire Wire Line
	4050 2100 4050 4350
Wire Wire Line
	4050 2100 5700 2100
Connection ~ 4050 4350
Connection ~ 4150 4250
Wire Wire Line
	5350 3300 5350 3450
Wire Wire Line
	5350 3750 5350 4050
Connection ~ 5350 4050
Wire Wire Line
	9350 4550 9500 4550
Wire Wire Line
	8300 2800 8200 2800
Wire Wire Line
	7900 2800 7800 2800
Wire Wire Line
	7850 3200 7850 2800
Connection ~ 7850 2800
Wire Wire Line
	8250 3200 8250 2800
Connection ~ 8250 2800
Wire Wire Line
	7400 2800 7500 2800
Wire Wire Line
	8600 2800 8700 2800
Wire Wire Line
	9400 5150 9500 5150
Wire Wire Line
	9350 5850 9500 5850
$Comp
L L_Small L2
U 1 1 571E79CE
P 8850 4250
F 0 "L2" H 8880 4290 50  0000 L CNN
F 1 " " H 8880 4210 50  0000 L CNN
F 2 "" H 8850 4250 50  0000 C CNN
F 3 "" H 8850 4250 50  0000 C CNN
	1    8850 4250
	0    1    1    0   
$EndComp
$Comp
L L_Small L1
U 1 1 571E7D00
P 8850 4150
F 0 "L1" H 8880 4190 50  0000 L CNN
F 1 " " H 8880 4110 50  0000 L CNN
F 2 "" H 8850 4150 50  0000 C CNN
F 3 "" H 8850 4150 50  0000 C CNN
	1    8850 4150
	0    -1   -1   0   
$EndComp
$Comp
L L_Small L4
U 1 1 571E7F4A
P 8850 5550
F 0 "L4" H 8880 5590 50  0000 L CNN
F 1 " " H 8880 5510 50  0000 L CNN
F 2 "" H 8850 5550 50  0000 C CNN
F 3 "" H 8850 5550 50  0000 C CNN
	1    8850 5550
	0    1    1    0   
$EndComp
$Comp
L L_Small L3
U 1 1 571E7F50
P 8850 5450
F 0 "L3" H 8880 5490 50  0000 L CNN
F 1 " " H 8880 5410 50  0000 L CNN
F 2 "" H 8850 5450 50  0000 C CNN
F 3 "" H 8850 5450 50  0000 C CNN
	1    8850 5450
	0    -1   -1   0   
$EndComp
Wire Wire Line
	9500 4150 8950 4150
Wire Wire Line
	9500 4250 8950 4250
Wire Wire Line
	9500 5450 8950 5450
Wire Wire Line
	8950 5550 9500 5550
Wire Wire Line
	8750 4150 6500 4150
Wire Wire Line
	8750 4250 6500 4250
Wire Wire Line
	8750 5450 8650 5450
Wire Wire Line
	8650 5450 8650 4150
Connection ~ 8650 4150
Wire Wire Line
	8750 5550 8550 5550
Wire Wire Line
	8550 5550 8550 4250
Connection ~ 8550 4250
Wire Wire Line
	8250 3800 8250 4150
Connection ~ 8250 4150
Wire Wire Line
	7850 3800 7850 4250
Connection ~ 7850 4250
$EndSCHEMATC
