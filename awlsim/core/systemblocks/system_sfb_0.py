# -*- coding: utf-8 -*-
#
# AWL simulator - SFBs
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.systemblocks.systemblocks import * #+cimport
from awlsim.core.blockinterface import *
from awlsim.core.datatypes import *
from awlsim.core.util import *


class SFB0(SFB): #+cdef
	name = (0, "CTU", "IEC 1131-3 up counter")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="CU", dataType="BOOL"),
			BlockInterfaceField(name="R", dataType="BOOL"),
			BlockInterfaceField(name="PV", dataType="INT"),
		),
		BlockInterfaceField.FTYPE_OUT	: (
			BlockInterfaceField(name="Q", dataType="BOOL"),
			BlockInterfaceField(name="CV", dataType="INT"),
		),
		BlockInterfaceField.FTYPE_STAT	: (
			BlockInterfaceField(name="CUO", dataType="BOOL"),
		),
	}

	def run(self): #+cpdef
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord

		# CU pos-edge detection
		CU = self.fetchInterfaceFieldByName("CU")
		CU_pos_edge = CU & ~self.fetchInterfaceFieldByName("CUO") & 1
		self.storeInterfaceFieldByName("CUO", CU)

		CV = wordToSignedPyInt(self.fetchInterfaceFieldByName("CV"))
		if self.fetchInterfaceFieldByName("R"): # Counter reset
			CV = 0
			self.storeInterfaceFieldByName("CV", CV)
		elif CU_pos_edge and CV < 32767: # Count up
			CV += 1
			self.storeInterfaceFieldByName("CV", CV)

		# Update Q-status
		PV = wordToSignedPyInt(self.fetchInterfaceFieldByName("PV"))
		self.storeInterfaceFieldByName("Q", 1 if CV >= PV else 0)

		s.BIE = 1
