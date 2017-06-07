# -*- coding: utf-8 -*-
#
# AWL simulator - IEC library - FC 21 "LEN"
#
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


class Lib__IEC__FC21_LEN(AwlLibFC):
	libraryName	= "IEC"
	staticIndex	= 21
	symbolName	= "LEN"
	description	= "Get STRING length"

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="S", dataType="STRING"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="RET_VAL", dataType="INT"),
		),
		BlockInterfaceField.FTYPE_TEMP	: (
			BlockInterfaceField(name="AR1_SAVE", dataType="DWORD"),
			BlockInterfaceField(name="DBNR", dataType="WORD"),
		),
	}

	awlCodeCopyright = "Copyright (c) 2015 Michael Buesch <m@bues.ch>"
	awlCodeLicense = "BSD-2-clause"
	awlCodeIsStandard = True
	awlCodeVersion = "0.1"

	awlCode = """
	TAR1	#AR1_SAVE	// Save AR1 register

	L	P##S		// Load pointer to DB-pointer
	LAR1
	L	W [AR1, P#0.0]	// Load DB number from DB-pointer
	T	#DBNR
	AUF	DB [#DBNR]	// Open Data Block (if any)
	L	D [AR1, P#2.0]	// Load data pointer from DB-pointer
	LAR1
	L	B [AR1, P#1.0]	// Load actual #S string length (byte 1)
	T	#RET_VAL	// Output actual string length

	LAR1	#AR1_SAVE	// Restore AR1 register
	SET			// VKE := 1
	SAVE			// BIE := 1
	BE
"""

AwlLib.registerEntry(Lib__IEC__FC21_LEN)
