# -*- coding: utf-8 -*-
#
# AWL simulator - SFBs
#
# Copyright 2014-2018 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *
from awlsim.common.util import *

from awlsim.core.systemblocks.systemblocks import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.datatypes import *


class SFB2(SFB): #+cdef
	name = (2, "CTUD", "IEC 1131-3 up/down counter")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="CU", dataType="BOOL"),
			BlockInterfaceField(name="CD", dataType="BOOL"),
			BlockInterfaceField(name="R", dataType="BOOL"),
			BlockInterfaceField(name="LOAD", dataType="BOOL"),
			BlockInterfaceField(name="PV", dataType="INT"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="QU", dataType="BOOL"),
			BlockInterfaceField(name="QD", dataType="BOOL"),
			BlockInterfaceField(name="CV", dataType="INT"),
		),
		BlockInterfaceField.FTYPE_STAT	: (
			BlockInterfaceField(name="CUO", dataType="BOOL"),
			BlockInterfaceField(name="CDO", dataType="BOOL"),
		),
	}

	def run(self): #+cpdef
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord

		# CU pos-edge detection
		CU = AwlMemoryObject_asScalar(self.fetchInterfaceFieldByName("CU"))
		CU_pos_edge = CU & (AwlMemoryObject_asScalar(
			self.fetchInterfaceFieldByName("CUO")) ^ 1) & 1
		self.storeInterfaceFieldByName("CUO",
			make_AwlMemoryObject_fromScalar(CU, 1))

		# CD pos-edge detection
		CD = AwlMemoryObject_asScalar(self.fetchInterfaceFieldByName("CD"))
		CD_pos_edge = CD & (AwlMemoryObject_asScalar(
			self.fetchInterfaceFieldByName("CDO")) ^ 1) & 1
		self.storeInterfaceFieldByName("CDO",
			make_AwlMemoryObject_fromScalar(CD, 1))

		# Count
		PV = wordToSignedPyInt(AwlMemoryObject_asScalar(
			self.fetchInterfaceFieldByName("PV")))
		CV = wordToSignedPyInt(AwlMemoryObject_asScalar(
			self.fetchInterfaceFieldByName("CV")))
		if AwlMemoryObject_asScalar(self.fetchInterfaceFieldByName("R")): # Counter reset
			CV = 0
			self.storeInterfaceFieldByName("CV",
				make_AwlMemoryObject_fromScalar(CV, 16))
		elif AwlMemoryObject_asScalar(self.fetchInterfaceFieldByName("LOAD")): # Counter load
			CV = PV
			self.storeInterfaceFieldByName("CV",
				make_AwlMemoryObject_fromScalar(CV, 16))
		elif CD_pos_edge and not CU_pos_edge and CV > -32768: # Count down
			CV -= 1
			self.storeInterfaceFieldByName("CV",
				make_AwlMemoryObject_fromScalar(CV, 16))
		elif CU_pos_edge and not CD_pos_edge and CV < 32767: # Count up
			CV += 1
			self.storeInterfaceFieldByName("CV",
				make_AwlMemoryObject_fromScalar(CV, 16))

		# Update Q-status
		self.storeInterfaceFieldByName("QU",
			make_AwlMemoryObject_fromScalar(1 if CV >= PV else 0, 1))
		self.storeInterfaceFieldByName("QD",
			make_AwlMemoryObject_fromScalar(1 if CV <= 0 else 0, 1))

		s.BIE = 1
