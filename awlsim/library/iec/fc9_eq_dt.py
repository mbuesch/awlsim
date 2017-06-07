# -*- coding: utf-8 -*-
#
# AWL simulator - IEC library - FC 9 "EQ_DT"
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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


class Lib__IEC__FC9_EQ_DT(AwlLibFC):
	libraryName	= "IEC"
	staticIndex	= 9
	symbolName	= "EQ_DT"
	description	= "Compare two DATE_AND_TIME for equality"

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="DT1", dataType="DATE_AND_TIME"),
			BlockInterfaceField(name="DT2", dataType="DATE_AND_TIME"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="RET_VAL", dataType="BOOL"),
		),
		BlockInterfaceField.FTYPE_TEMP	: (
			BlockInterfaceField(name="DBNR", dataType="INT"),
		),
	}

	awlCodeCopyright = "Copyright (c) 2014 Michael Buesch <m@bues.ch>"
	awlCodeLicense = "BSD-2-clause"
	awlCodeIsStandard = True
	awlCodeVersion = "0.1"

	awlCode = """
	// Load a pointer to #DT1 into AR1 and open the DB
	LAR1	P##DT1
	L	W [AR1, P#0.0]
	T	#DBNR
	AUF	DB [#DBNR]
	L	D [AR1, P#2.0]
	LAR1

	// Load a pointer to #DT2 into AR2 and open the DB as DI
	LAR2	P##DT2
	L	W [AR2, P#0.0]
	T	#DBNR
	AUF	DI [#DBNR]
	L	D [AR2, P#2.0]
	// If #DT2 points to DB (area 84) change it to DI (area 85).
	// This also works, if #DT2 points to VL (area 87).
	// Other areas are not possible.
	OD	DW#16#85000000
	LAR2

	// Compare #DT1 with #DT2
	L	D [AR1, P#0.0]
	L	D [AR2, P#0.0]
	==D
	U(
	L	D [AR1, P#4.0]
	L	D [AR2, P#4.0]
	==D
	)
	=	#RET_VAL

	SET
	SAVE
	BE
"""

AwlLib.registerEntry(Lib__IEC__FC9_EQ_DT)
