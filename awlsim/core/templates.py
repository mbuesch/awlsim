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


awlTemplate_OB = """ORGANIZATION_BLOCK OB xxx
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


awlTemplate_FC = """FUNCTION FC xxx : VOID
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


awlTemplate_FB = """FUNCTION_BLOCK FB xxx
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


awlTemplate_instanceDB = """DATA_BLOCK DB xxx
	FB xxx		// Insert FB name here
	TITLE		= Insert title here
	AUTHOR		: Insert author name here
	VERSION		: 0.1
BEGIN

	// ... Insert data initializations here ...

END_DATA_BLOCK
"""


awlTemplate_globalDB = """DATA_BLOCK DB xxx
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


awlTemplate_FCcall = """	CALL FC xxx (
		// ... Insert parameter assignments here ...
		// VARIABLE	:= MW 0,
		// RET_VAL	:= MW 2,
	)
"""


awlTemplate_FBcall = """	CALL FB xxx, DB xxx (
		// ... Insert parameter assignments here ...
		// VARIABLE	:= MW 0,
	)
"""
