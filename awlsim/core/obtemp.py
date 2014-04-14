# -*- coding: utf-8 -*-
#
# AWL simulator - Organization Block temp variable presets
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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

import math

from awlsim.core.util import *


class OBTempPresets(object):
	"""Abstract Organization Block temporary-variable presets handler."""

	def __init__(self, obNumber, cpu):
		self.obNumber = obNumber
		self.cpu = cpu

	def tempUnderflow(self):
		raise AwlSimError("Localdata (TEMP) area in "
			"OB %d is too small." % self.obNumber)

	# Write the TempPresets.
	# localdata is the TEMP-data array.
	# This method is to be overloaded in the subclass.
	def generate(self, localdata):
		raise NotImplementedError

class OBTempPresets_dummy(OBTempPresets):
	"""Dummy-presets handler. This handler does nothing."""

	def __init__(self, cpu):
		OBTempPresets.__init__(self, -1, cpu)

	def generate(self, localdata):
		pass

class OB1TempPresets(OBTempPresets):
	"""OB 1 temp-presets handler."""

	def __init__(self, cpu):
		OBTempPresets.__init__(self, 1, cpu)

	def generate(self, localdata):
		cpu, ceil = self.cpu, math.ceil
		try:
			avgMs = min(0x7FFF, int(ceil(cpu.avgCycleTime * 1000)))
			minMs = min(0x7FFF, int(ceil(cpu.minCycleTime * 1000)))
			maxMs = min(0x7FFF, int(ceil(cpu.maxCycleTime * 1000)))
			# Sanitize times
			minMs = min(minMs, maxMs)
			avgMs = min(max(avgMs, minMs), maxMs)

			# Byte 0: OB1_EV_CLASS
			localdata[0] = 0x11
			# Byte 1: OB1_SCAN_1
			localdata[1] = 0x03
			# Byte 2: OB1_PRIORITY
			localdata[2] = 0x01
			# Byte 3: OB1_OB_NUMBR
			localdata[3] = 0x01
			# Byte 4: OB1_RESERVED_1
			localdata[4] = 0x00
			# Byte 5: OB1_RESERVED_2
			localdata[5] = 0x00
			# Byte 6-7: OB1_PREV_CYCLE
			#           We write the average cycle time instead
			#           of the previous cycle time,
			#           because we don't measure each cycle.
			localdata[6] = (avgMs >> 8) & 0xFF
			localdata[7] = avgMs & 0xFF
			# Byte 8-9: OB1_MIN_CYCLE
			localdata[8] = (minMs >> 8) & 0xFF
			localdata[9] = minMs & 0xFF
			# Byte 10-11: OB1_MAX_CYCLE
			localdata[10] = (maxMs >> 8) & 0xFF
			localdata[11] = maxMs & 0xFF
			# Byte 12-19: OB1_DATE_TIME
			cpu.makeCurrentDateAndTime(localdata, 12)
		except IndexError:
			self.tempUnderflow()

OBTempPresets_table = {
	1	: OB1TempPresets,
}
