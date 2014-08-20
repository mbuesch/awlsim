# -*- coding: utf-8 -*-
#
# AWL simulator - Source templates
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
from awlsim.core.compat import *


class Templates(object):
	# OB template
	__templateOB = """ORGANIZATION_BLOCK OB @@NR@@
	TITLE		= Insert title here
	AUTHOR		: Insert author name here
	VERSION		: 0.1
	VAR_TEMP
		OB1_EV_CLASS	: BYTE;		// Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB1_SCAN_1	: BYTE;		// 1 (Cold restart scan 1 of OB 1), 3 (Scan 2-n of OB 1)
		OB1_PRIORITY	: BYTE;		// Priority of OB Execution
		OB1_OB_NUMBR	: BYTE;		// 1 (Organization block 1, OB1)
		OB1_RESERVED_1	: BYTE;
		OB1_RESERVED_2	: BYTE;
		OB1_PREV_CYCLE	: INT;		// Cycle time of previous OB1 scan (milliseconds)
		OB1_MIN_CYCLE	: INT;		// Minimum cycle time of OB1 (milliseconds)
		OB1_MAX_CYCLE	: INT;		// Maximum cycle time of OB1 (milliseconds)
		OB1_DATE_TIME	: DATE_AND_TIME;// Date and time OB1 started

		// ... Insert temporary variables here ...
	END_VAR
BEGIN
NETWORK
	TITLE = Insert network title here

	// ... Insert AWL/STL code here ...

END_ORGANIZATION_BLOCK
"""

	# FC template
	__templateFC = """FUNCTION FC @@NR@@ : VOID
	TITLE		= Insert title here
	AUTHOR		: Insert author name here
	VERSION		: 0.1
	VAR_INPUT
		// Input variables
	END_VAR
	VAR_OUTPUT
		// Output variables
	END_VAR
	VAR_IN_OUT
		// In/out variables
	END_VAR
	VAR_TEMP
		// Temporary variables
	END_VAR
BEGIN
NETWORK
	TITLE = Insert network title here

	// ... Insert AWL/STL code here ...

END_FUNCTION
"""

	# FB template
	__templateFB = """FUNCTION_BLOCK FB @@NR@@
	TITLE		= Insert title here
	AUTHOR		: Insert author name here
	VERSION		: 0.1
	VAR
		// Static variables
	END_VAR
	VAR_INPUT
		// Input variables
	END_VAR
	VAR_OUTPUT
		// Output variables
	END_VAR
	VAR_IN_OUT
		// In/out variables
	END_VAR
	VAR_TEMP
		// Temporary variables
	END_VAR
BEGIN
NETWORK
	TITLE = Insert network title here

	// ... Insert AWL/STL code here ...

END_FUNCTION_BLOCK
"""

	# Instance-DB template
	__templateIDB = """DATA_BLOCK DB @@DBNR@@
	FB @@FBNR@@
	TITLE		= Insert title here
	AUTHOR		: Insert author name here
	VERSION		: 0.1
BEGIN

	// ... Insert data initializations here ...

END_DATA_BLOCK
"""

	# Global-DB template
	__templateGDB = """DATA_BLOCK DB @@NR@@
	TITLE		= Insert title here
	AUTHOR		: Insert author name here
	VERSION		: 0.1
	STRUCT

		// ... Insert data structure definitions here ...

	END_STRUCT
BEGIN

	// ... Insert data initializations here ...

END_DATA_BLOCK
"""

	# FC-call template
	__templateFCcall = """	CALL FC @@NR@@ (
		// ... Insert parameter assignments here ...
		// VARIABLE	:= MW 0,
		// RET_VAL	:= MW 2,
	)
"""

	# FB-call template
	__templateFBcall = """	CALL FB @@FBNR@@, DB @@DBNR@@ (
		// ... Insert parameter assignments here ...
		// VARIABLE	:= MW 0,
	)
"""

	@classmethod
	def getOB(cls, number):
		awl = cls.__templateOB[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		return awl

	@classmethod
	def getFC(cls, number):
		awl = cls.__templateFC[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		return awl

	@classmethod
	def getFB(cls, number):
		awl = cls.__templateFB[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		return awl

	@classmethod
	def getInstanceDB(cls, dbNumber, fbNumber):
		awl = cls.__templateIDB[:]
		awl = awl.replace("@@DBNR@@", "%d" % dbNumber)
		awl = awl.replace("@@FBNR@@", "%d" % fbNumber)
		return awl

	@classmethod
	def getGlobalDB(cls, number):
		awl = cls.__templateGDB[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		return awl

	@classmethod
	def getFCcall(cls, number):
		awl = cls.__templateFCcall[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		return awl

	@classmethod
	def getFBcall(cls, fbNumber, dbNumber):
		awl = cls.__templateFBcall[:]
		awl = awl.replace("@@FBNR@@", "%d" % fbNumber)
		awl = awl.replace("@@DBNR@@", "%d" % dbNumber)
		return awl
