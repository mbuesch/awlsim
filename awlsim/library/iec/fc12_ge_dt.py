# -*- coding: utf-8 -*-
#
# AWL simulator - IEC library - FC 12 "GE_DT"
#
# Copyright 2015 Christian Vitte <vitte.chris@gmail.com>
# Copyright 2015 Michael Buesch <m@bues.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

from awlsim.library.libentry import *


class Lib__IEC__FC12_GE_DT(AwlLibFC):
	libraryName	= "IEC"
	staticIndex	= 12
	symbolName	= "GE_DT"
	description	= "Greater or equal DATE_AND_TIME"

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="DT1", dataType="DATE_AND_TIME"),
			BlockInterfaceField(name="DT2", dataType="DATE_AND_TIME"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="RET_VAL", dataType="BOOL"),
		),
		BlockInterfaceField.FTYPE_TEMP	: (
			BlockInterfaceField(name="YEAR1", dataType="WORD"),
			BlockInterfaceField(name="YEAR2", dataType="WORD"),
			BlockInterfaceField(name="AR1_SAVE", dataType="DWORD"),
		),
	}

	awlCodeCopyright = "Copyright (c) 2015 Christian Vitte <vitte.chris@gmail.com>\n"\
			   "Copyright (c) 2015 Michael Buesch <m@bues.ch>"
	awlCodeLicense = "BSD-2-clause"
	awlCodeIsStandard = True
	awlCodeVersion = "0.1"

	awlCode = """
	TAR1	#AR1_SAVE	// Save AR1 register

	// Load a pointer to #DT1 into AR1 and open the DB
	L	P##DT1
	LAR1
	L	W [AR1, P#0.0]
	T	#YEAR1 // DB number (abuse #YEAR1 temp field)
	AUF	DB [#YEAR1]
	L	D [AR1, P#2.0]
	LAR1

	// Load a pointer to #DT2 into AR2 and open the DB as DI
	L	P##DT2
	LAR2
	L	W [AR2, P#0.0]
	T	#YEAR1 // DB number (abuse #YEAR1 temp field)
	AUF	DI [#YEAR1]
	L	D [AR2, P#2.0]
	// If #DT2 points to DB (area 84) change it to DI (area 85).
	// This also works, if #DT2 points to VL (area 87).
	// Other areas are not possible.
	OD	DW#16#85000000
	LAR2

//------------------------------------------------------
	// Extract years from DT1 and DT2
	L	B [AR1, P#0.0]
	T	#YEAR1
	L	B [AR2, P#0.0]
	T	#YEAR2

	// Check whether the year values from DT1 and DT2
	// are valid BCD numbers.
	L	#YEAR1
	UW	W#16#000F
	L	W#16#0009
	>I
	SPB	FAIL
	L	#YEAR1
	UW	W#16#00F0
	L	W#16#0090
	>I
	SPB	FAIL
	L	#YEAR2
	UW	W#16#000F
	L	W#16#0009
	>I
	SPB	FAIL
	L	#YEAR2
	UW	W#16#00F0
	L	W#16#0090
	>I
	SPB	FAIL

//------------------------------------------------------
	// Check whether specified year is 1990-1999 or 2000-2089
	L	B#16#89
	L	#YEAR1
	>=I
	SPB	_2K1

	// 1900 years correction (applicable for year 1990-1999)
	OW	W#16#1900
	T	#YEAR1
	SPA	Y2

	// 2000 years correction (applicable for year 2000-2089)
_2K1:	OW	W#16#2000
	T	#YEAR1

	// Check whether specified year is 1990-1999 or 2000-2089
Y2:	L	B#16#89
	L	#YEAR2
	>=I
	SPB	_2K2

	// 1900 years correction (applicable for year 1990-1999)
	OW	W#16#1900
	T	#YEAR2
	SPA	YRCK

	// 2000 years correction (applicable for year 2000-2089)
_2K2:	OW	W#16#2000
	T	#YEAR2

//------------------------------------------------------
	// Check if YEAR1 >= YEAR2.
	// This check also works without BCD->INT conversion.
YRCK:	L	#YEAR1
	L	#YEAR2
	<I
	// year1 < year2 -> NOK
	SPB	NOK
	// year1 > year2 -> OK
	>I
	SPB	OK

//------------------------------------------------------
	// Check if M:D:H DT1 >= M:D:H DT2 - Bytes 1 to 3
	// Extract M:D:H from DT1 and DT2 (without year)
	L	D [AR1, P#0.0]
	UD	DW#16#00FFFFFF	// Remove sign (and year)
	L	D [AR2, P#0.0]
	UD	DW#16#00FFFFFF	// Remove sign (and year)
	<D
	// BCD-from-DT1 < BCD-from-DT2 -> NOK
	// This check also works without BCD->INT conversion.
	SPB	NOK
	>D
	// BCD-from-DT1 > BCD-from-DT2 -> OK
	SPB	OK

//------------------------------------------------------
	// Check if M:S:MS1 DT1 >= M:S:MS1 DT2 - Bytes 4 to 6
	// Extract M:S:MS1 from DT1 and DT2
	L	D [AR1, P#3.0]
	UD	DW#16#00FFFFFF	// Remove sign (and hour)
	L	D [AR2, P#3.0]
	UD	DW#16#00FFFFFF	// Remove sign (and hour)
	<D
	// BCD-from-DT1 < BCD-from-DT2 -> NOK
	// This check also works without BCD->INT conversion.
	SPB	NOK
	>D
	// BCD-from-DT1 > BCD-from-DT2 -> OK
	SPB	OK

//------------------------------------------------------
	// Check if MS2:WD DT1 >= MS2:WD DT2 - Byte 7
	// Extract MS2:WD from DT1 and DT2
	L	B [AR1, P#7.0]
	L	B [AR2, P#7.0]
	<I
	// BCD-from-DT1 < BCD-from-DT2 -> NOK
	// This check also works without BCD->INT conversion.
	SPB	NOK

//------------------------------------------------------
	// Everything is Ok.
	// VKE is 1.
OK:	=	#RET_VAL	// RET_VAL := 1
	SAVE			// BIE := 1
	SPA	END

	// BCD failure. Set BIE := 0.
	// Do not touch RET_VAL.
FAIL:	CLR
	SAVE			// BIE := 0
	SPA	END

	// BCD is Ok, but result is negative.
	// VKE is 1.
NOK:	SAVE			// BIE := 1
	CLR
	=	#RET_VAL	// RET_VAL := 0

END:	LAR1	#AR1_SAVE	// Restore AR1 register
	BE
"""

AwlLib.registerEntry(Lib__IEC__FC12_GE_DT)
