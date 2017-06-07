# -*- coding: utf-8 -*-
#
# AWL simulator - SFCs
#
# Copyright 2015-2017 Michael Buesch <m@bues.ch>
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

import time


class SFC47(SFC): #+cdef
	name = (47, "WAIT", "delay time")

	interfaceFields = {
		BlockInterfaceField.FTYPE_IN	: (
			BlockInterfaceField(name="WT", dataType="INT"),
		)
	}

	def run(self): #+cpdef
#@cy		cdef S7StatusWord s
#@cy		cdef int32_t WT
#@cy		cdef double start
#@cy		cdef double end
#@cy		cdef double now

		# Get the start time early before fetching WT.
		timer = perf_monotonic_time
		start = timer()

		s = self.cpu.statusWord

		# Delay for the specified amount of microseconds.
		# WT is an int, so the maximum delay is 32767 us.
		WT = wordToSignedPyInt(self.fetchInterfaceFieldByName("WT"))
		if WT > 0:
			end = start + (min(WT, 32767) / 1000000.0)
			now = timer()
			while now < end and now >= start:
				now = timer()
		self.cpu.updateTimestamp()

		s.BIE = 1
