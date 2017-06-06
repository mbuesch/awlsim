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
from awlsim.common.compat import *


__all__ = [
	"Templates",
]


class Templates(object):
	# OB template
	__templateOB = """ORGANIZATION_BLOCK OB @@NR@@
	TITLE		= Insert title here
	AUTHOR		: Insert author name here
	VERSION		: 0.1
	VAR_TEMP@@TEMPVARS@@
		// ... Insert temporary variables here ...
	END_VAR
BEGIN
NETWORK
	TITLE = Insert network title here
	// ... Insert AWL/STL code here ...
	
END_ORGANIZATION_BLOCK
"""

	# OB start info variables
	__obTempVars = (
		( range(1, 1 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_SCAN_1     : BYTE;          // 1 (Cold restart scan 1 of OB @@NR@@), 3 (Scan 2-n of OB @@NR@@)
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_RESERVED_2 : BYTE;
		OB@@NR@@_PREV_CYCLE : INT;           // Cycle time of previous OB @@NR@@ scan (milliseconds)
		OB@@NR@@_MIN_CYCLE  : INT;           // Minimum cycle time of OB @@NR@@ (milliseconds)
		OB@@NR@@_MAX_CYCLE  : INT;           // Maximum cycle time of OB @@NR@@ (milliseconds)
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(10, 17 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          //Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INFO  : BYTE;          // B#16#11 (OB @@NR@@ has started)
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_RESERVED_2 : BYTE;
		OB@@NR@@_PERIOD_EXE : WORD;          // Period of execution (once, per minute/hour/day/week/month/year)
		OB@@NR@@_RESERVED_3 : INT;
		OB@@NR@@_RESERVED_4 : INT;
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(20, 23 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INF   : BYTE;          // B#16#21 (OB @@NR@@ has started)
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_RESERVED_2 : BYTE;
		OB@@NR@@_SIGN       : WORD;          // Identifier input (SIGN) attached to SRT_DINT
		OB@@NR@@_DTIME      : TIME;          // Delay time (DTIME) input to SRT_DINT instruction
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(30, 38 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INF   : BYTE;          // B#16#31 (OB @@NR@@ has started)
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_RESERVED_2 : BYTE;
		OB@@NR@@_PHS_OFFSET : INT;           // Phase offset (integer, milliseconds)
		OB@@NR@@_RESERVED_3 : INT;
		OB@@NR@@_EXC_FREQ   : INT;           // Frequency of execution (msec)
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(40, 47 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INF   : BYTE;          // B#16#41 (OB @@NR@@ has started)
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_IO_FLAG    : BYTE;          // B#16#54 (input module), B#16#55 (output module)
		OB@@NR@@_MDL_ADDR   : WORD;          // Base address of module initiating interrupt
		OB@@NR@@_POINT_ADDR : DWORD;         // Interrupt status of the module
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(55, 57 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INF   : BYTE;          // B#16#55 (OB @@NR@@ has started)
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_IO_FLAG    : BYTE;          // B#16#54 (input module), B#16#55 (output module)
		OB@@NR@@_MDL_ADDR   : WORD;          // Base address of module initiating interrupt
		OB@@NR@@_LEN        : BYTE;          // Length of information
		OB@@NR@@_TYPE       : BYTE;          // Type of alarm
		OB@@NR@@_SLOT       : BYTE;          // Slot
		OB@@NR@@_SPEC       : BYTE;          // Specifier
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(60, 60 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INF   : BYTE;          // B#16#61 (self generated), B#16#62 (external generated)
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_RESERVED_2 : BYTE;
		OB@@NR@@_JOB        : INT;           // Job sign
		OB@@NR@@_RESERVED_3 : INT;
		OB@@NR@@_RESERVED_4 : INT;
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(61, 64 + 1), """
		OB@@NR@@_EV_CLASS    : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INF    : BYTE;          // B#16#36 (OB @@NR@@ has started)
		OB@@NR@@_PRIORITY    : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR    : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1  : BYTE;
		OB@@NR@@_RESERVED_2  : BYTE;
		OB@@NR@@_GC_VIOL     : BOOL;          // Lost Global Control of DP system
		OB@@NR@@_FIRST       : BOOL;          // First Execution after startup or HALT
		OB@@NR@@_MISSED_EXEC : BYTE;          // Count of missed executions of OB @@NR@@ since it was last scheduled
		OB@@NR@@_DP_ID       : BYTE;          // DP master system ID of the synchronous DP system
		OB@@NR@@_RESERVED_3  : BYTE;
		OB@@NR@@_RESERVED_4  : WORD;
		OB@@NR@@_DATE_TIME   : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(70, 72 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Event class 7, module inserted/removed (8/9)
		OB@@NR@@_FLT_ID     : BYTE;          // Fault identifcation code
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : WORD;
		OB@@NR@@_INFO_1     : WORD;          // Info 1
		OB@@NR@@_INFO_2     : WORD;          // Info 2
		OB@@NR@@_INFO_3     : WORD;          // Info 3
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(80, 87 + 1), """
		OB@@NR@@_EV_CLASS     : BYTE;          // B#16#35, Event class 3, Entering event state, Internal fault event
		OB@@NR@@_FLT_ID       : BYTE;          // Fault identifcation code
		OB@@NR@@_PRIORITY     : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR     : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1   : BYTE;
		OB@@NR@@_RESERVED_2   : BYTE;
		OB@@NR@@_ERROR_INFO   : WORD;          // Error information on event
		OB@@NR@@_ERR_EV_CLASS : BYTE;          // Class of event causing error
		OB@@NR@@_ERR_EV_NUM   : BYTE;          // Number of event causing error
		OB@@NR@@_OB_PRIORITY  : BYTE;          // Priority of OB causing error
		OB@@NR@@_OB_NUM       : BYTE;          // Number of OB causing error
		OB@@NR@@_DATE_TIME    : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(90, 90 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // Bits 0-3 = 1 (Coming event), Bits 4-7 = 1 (Event class 1)
		OB@@NR@@_STRT_INF   : BYTE;          // 91 Cold restart, 92 Delete block, 93 Load OB @@NR@@, 95 End background cycle
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_RESERVED_2 : BYTE;
		OB@@NR@@_RESERVED_3 : INT;
		OB@@NR@@_RESERVED_4 : INT;
		OB@@NR@@_RESERVED_5 : INT;
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(100, 102 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // B#16#13, Event class 1, Entering event state, Event logged in diagnostic buffer
		OB@@NR@@_STRTUP     : BYTE;          // B#16#81/82/83/84 Method of startup
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_RESERVED_2 : BYTE;
		OB@@NR@@_STOP       : WORD;          // Event that caused CPU to stop (W#16#4XXX)
		OB@@NR@@_STRT_INFO  : DWORD;         // Information on how system started
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(121, 121 + 1), """
		OB@@NR@@_EV_CLASS   : BYTE;          // B#16#25, Event class 2, Entering event state, Internal fault event
		OB@@NR@@_SW_FLT     : BYTE;          // Software programming fault
		OB@@NR@@_PRIORITY   : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR   : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_BLK_TYPE   : BYTE;          // B#16#88/8A/8B/8C/8E Type of block fault occured in
		OB@@NR@@_RESERVED_1 : BYTE;
		OB@@NR@@_FLT_REG    : WORD;          // Specific register that caused fault
		OB@@NR@@_BLK_NUM    : WORD;          // Number of block that programming fault occured in
		OB@@NR@@_PRG_ADDR   : WORD;          // Address in block where programming fault occured
		OB@@NR@@_DATE_TIME  : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
		( range(122, 122 + 1), """
		OB@@NR@@_EV_CLASS  : BYTE;          // B#16#29, Event class 2, Entering event state, Internal fault event
		OB@@NR@@_SW_FLT    : BYTE;          // Software error code
		OB@@NR@@_PRIORITY  : BYTE;          // Priority of OB execution
		OB@@NR@@_OB_NUMBR  : BYTE;          // @@NR@@ (Organization block @@NR@@, OB @@NR@@)
		OB@@NR@@_BLK_TYPE  : BYTE;          // B#16#88/8C/8E Type of block fault occured in
		OB@@NR@@_MEM_AREA  : BYTE;          // Memory area where access error occured
		OB@@NR@@_MEM_ADDR  : WORD;          // Memory address where access error occured
		OB@@NR@@_BLK_NUM   : WORD;          // Block number in which error occured
		OB@@NR@@_PRG_ADDR  : WORD;          // Program address where error occured
		OB@@NR@@_DATE_TIME : DATE_AND_TIME; // Date and time OB @@NR@@ started"""
		),
	)


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
		
	END_STRUCT;
BEGIN
	// ... Insert data initializations here ...
	
END_DATA_BLOCK
"""

	# UDT template
	__templateUDT = """TYPE UDT @@NR@@
	VERSION : 0.1
	STRUCT
		// ... Insert data structure definitions here ...
		
	END_STRUCT;
END_TYPE
"""

	# FC-call template
	__templateFCcall = """CALL FC @@NR@@ (
	// ... Insert parameter assignments here ...
	// VARIABLE	:= MW 0,
	// RET_VAL	:= MW 2,
)
"""

	# FB-call template
	__templateFBcall = """CALL FB @@FBNR@@, DB @@DBNR@@ (
	// ... Insert parameter assignments here ...
	// VARIABLE	:= MW 0,
)
"""

	@classmethod
	def __removeVerboseness(cls, awl):
		newAwl = []
		for line in awl.splitlines():
			stripped = line.strip()
			if stripped.startswith("TITLE") or\
			   stripped.startswith("AUTHOR") or\
			   stripped.startswith("VERSION") or\
			   stripped.startswith("NETWORK") or\
			   stripped.startswith("// ..."):
				continue
			if stripped.startswith("// Input variables") or\
			   stripped.startswith("// Output variables") or\
			   stripped.startswith("// In/out variables") or\
			   stripped.startswith("// Temporary variables") or\
			   stripped.startswith("// Static variables"):
				newAwl.append("\t\t")
				continue
			newAwl.append(line)
		return "\n".join(newAwl)

	@classmethod
	def getOB(cls, number, verbose):
		awl = cls.__templateOB[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		for rnge, tempvars in cls.__obTempVars:
			if number in rnge:
				tempvars = tempvars.replace("@@NR@@", "%d" % number)
				awl = awl.replace("@@TEMPVARS@@", tempvars)
				break
		else:
			awl = awl.replace("@@TEMPVARS@@", "")
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl

	@classmethod
	def getFC(cls, number, verbose):
		awl = cls.__templateFC[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl

	@classmethod
	def getFB(cls, number, verbose):
		awl = cls.__templateFB[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl

	@classmethod
	def getInstanceDB(cls, dbNumber, fbNumber, verbose):
		awl = cls.__templateIDB[:]
		awl = awl.replace("@@DBNR@@", "%d" % dbNumber)
		awl = awl.replace("@@FBNR@@", "%d" % fbNumber)
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl

	@classmethod
	def getGlobalDB(cls, number, verbose):
		awl = cls.__templateGDB[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl

	@classmethod
	def getUDT(cls, number, verbose):
		awl = cls.__templateUDT[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl

	@classmethod
	def getFCcall(cls, number, verbose):
		awl = cls.__templateFCcall[:]
		awl = awl.replace("@@NR@@", "%d" % number)
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl

	@classmethod
	def getFBcall(cls, fbNumber, dbNumber, verbose):
		awl = cls.__templateFBcall[:]
		awl = awl.replace("@@FBNR@@", "%d" % fbNumber)
		awl = awl.replace("@@DBNR@@", "%d" % dbNumber)
		if not verbose:
			awl = cls.__removeVerboseness(awl)
		return awl
