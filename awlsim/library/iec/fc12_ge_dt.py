# -*- coding: utf-8 -*-
#
# AWL simulator - IEC library - FC 12 "GE_DT"
#
# Copyright 2015 Christian Vitte <vitte.chris@gmail.com>
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
	description	= "Greater or Equal DATE_AND_TIME"

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name = "DT1",
					    dataType = AwlDataType.makeByName("DATE_AND_TIME")),
			BlockInterfaceField(name = "DT2",
					    dataType = AwlDataType.makeByName("DATE_AND_TIME")),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name = "RET_VAL",
					    dataType = AwlDataType.makeByName("BOOL")),
		),
		BlockInterfaceField.FTYPE_TEMP	: (
			BlockInterfaceField(name = "DBNR",
					    dataType = AwlDataType.makeByName("INT")),
			BlockInterfaceField(name = "YEAR1",
					    dataType = AwlDataType.makeByName("WORD")),
			BlockInterfaceField(name = "YEAR2",
					    dataType = AwlDataType.makeByName("WORD")),
			BlockInterfaceField(name = "loop1",
					    dataType = AwlDataType.makeByName("BYTE")),
			BlockInterfaceField(name = "loop2",
					    dataType = AwlDataType.makeByName("BYTE")),
			BlockInterfaceField(name = "BYTE1",
					    dataType = AwlDataType.makeByName("BYTE")),
			BlockInterfaceField(name = "BYTE2",
					    dataType = AwlDataType.makeByName("BYTE")),
			BlockInterfaceField(name = "AR1_SAVE",
					    dataType = AwlDataType.makeByName("DWORD")),
			BlockInterfaceField(name = "BCD1",
					    dataType = AwlDataType.makeByName("DWORD")),
			BlockInterfaceField(name = "BCD2",
					    dataType = AwlDataType.makeByName("DWORD")),
			BlockInterfaceField(name = "BCD_1_2",
					    dataType = AwlDataType.makeByName("WORD")),
		),
	}

	awlCodeCopyright = "Copyright (c) 2015 Christian Vitte <vitte.chris@gmail.com>"
	awlCodeLicense = "BSD-2-clause"
	awlCode = """	
// AR1-Register save    
      TAR1  #AR1_SAVE
// init #RET_VAL
      CLR   
      =     #RET_VAL
// Load a pointer to #DT1 into AR1 and open the DB
      L     P##DT1
      LAR1  
      L     W [AR1,P#0.0]
      T     #DBNR
      AUF   DB [#DBNR]
      L     D [AR1,P#2.0]
      LAR1  

// Load a pointer to #DT2 into AR2 and open the DB as DI
      L     P##DT2
      LAR2  
      L     W [AR2,P#0.0]
      T     #DBNR
      AUF   DI [#DBNR]
      L     D [AR2,P#2.0]
// If #DT2 points to DB (area 84) change it to DI (area 85).
// This also works, if #DT2 points to VL (area 87).
// Other areas are not possible.
      OD    DW#16#85000000
      LAR2  

// Extract years from DT1 and DT2
      L     B [AR1,P#0.0]
      T     #YEAR1
      L     B [AR2,P#0.0]
      T     #YEAR2

// Put YEAR1 and YEAR2 into BCD_1_2 TEMP
      L     B [AR1,P#0.0]
      T     #BYTE1
      L     B [AR2,P#0.0]
      SLW   8
      OW    
      T     #BCD_1_2

//-------------------------------------------------------
// check YEAR1 and YEAR2 are in BCD number
// Loop for check 4 digits in BCD_1_2
      L     4
LOP2: T     #loop2
      L     1
      -I    
      L     4
      *I    
      L     #BCD_1_2
      SRW   
      L     W#16#F
      UW    
      T     #BYTE1

// Loop for check selected digit is BCD format
      L     10
LOP1: T     #loop1
      L     1
      -I    
      T     #BYTE2
      L     #BYTE1
      ==I   
// equal -> exit loop
      SPB   JMP3
      L     #loop1
      LOOP  LOP1

// Loop exit without jump -> fail
      SPB   fail

JMP3: NOP   0

      L     #loop2
      LOOP  LOP2

//------------------------------------------------------
// Checking if specified year is 1990-1999 or 2000-2089
      L     #YEAR1
      L     B#16#89
      >I    
      SPBN  _200

// 1900 years Correction (applicable for year 1990-1999)
      L     #YEAR1
      OW    W#16#1900
      T     #YEAR1
      SPB   JMP1

_200: NOP   0
// 2000 years Correction (applicable for year 2000-2089)
      L     #YEAR1
      OW    W#16#2000
      T     #YEAR1

JMP1: NOP   0
// if the year is > = 89 (ie 1990-1999)
      L     #YEAR2
      L     B#16#89
      >I    
      SPBN  _201

// 1900 years Correction (applicable for year 1990-1999)
      L     #YEAR2
      OW    W#16#1900
      T     #YEAR2
      SPB   CTR1

_201: NOP   0
// 2000 years Correction (applicable for year 2000-2089)
      L     #YEAR2
      OW    W#16#2000
      T     #YEAR2

//------------------------------------------------------
// Checking if YEAR1 >= YEAR2
CTR1: L     #YEAR1
      L     #YEAR2
      >=I   
// year1 >= year2 -> CTR2
      SPB   CTR2
      <I    
// year1 < year2 -> NOK
      SPB   NOK

//------------------------------------------------------
CTR2: NOP   0
// Checking if M:D:H DT1 >= M:D:H DT2 - Bytes 2 to 4

// Extract first data from DT1 and DT2 without year
      L     D [AR1,P#0.0]
      L     DW#16#FFFFFF
      UD    
      T     #BCD1
      L     D [AR2,P#0.0]
      L     DW#16#FFFFFF
      UD    
      T     #BCD2

      L     #BCD1
      L     #BCD2
      >=D   
// BCD1 >= BCD2 -> CTR3
      SPB   CTR3
      <D    
// BCD1 < BCD2 -> NOK
      SPB   NOK

//------------------------------------------------------
CTR3: NOP   0
// Checking if M:S:MS DT1 >= M:S:MS DT2 - Bytes 5 to 8

// Extract second data from DT1 and DT2
      L     D [AR1,P#4.0]
      T     #BCD1
      L     D [AR2,P#4.0]
      T     #BCD2

      L     #BCD1
      L     #BCD2
      >=D   
// BCD1 >= BCD2 -> OK
      SPB   OK
      <D    
// BCD1 < BCD2 -> NOK
      SPB   NOK

//------------------------------------------------------
//  RET_VAL := 1
OK:   SET   
      =     #RET_VAL
// BIE := 1
      SET   
      SAVE  
      SPA   ENDE

// if no BCD number then BIE := 0
fail: CLR   
      SAVE  
      SPA   ENDE

// if BCD number then BIE := 1
NOK:  SET   
      SAVE  

// Load AR1 register
ENDE: L     #AR1_SAVE
      LAR1  
      BE   
"""

AwlLib.registerEntry(Lib__IEC__FC12_GE_DT)
