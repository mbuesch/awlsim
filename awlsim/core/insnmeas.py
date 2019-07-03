# -*- coding: utf-8 -*-
#
# AWL simulator - Instruction timing measurement
#
# Copyright 2019 Michael Buesch <m@bues.ch>
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

from awlsim.common.util import *
from awlsim.common.exceptions import *
from awlsim.common.monotonic import * #+cimport

#from awlsim.core.insnmeas cimport * #@cy
from awlsim.core.instructions.main import * #+cimport
from awlsim.core.instructions.types import * #+cimport

import time


__all__ = [
	"InsnMeas",
]


class InsnMeasData(object): #+cdef
	def __init__(self):
		self.measured = False
		self.measStart = 0.0
		self.cumRt = 0.0
		self.count = 0
		self.minRt = 9999.0
		self.maxRt = 0.0

	@property
	def avgRt(self):
		if self.count == 0:
			return 9999.0
		return self.cumRt / float(self.count)

	def subtractCal(self, calOffset):
		new = InsnMeasData()
		new.minRt = max(1.0e-9, self.minRt - calOffset)
		new.maxRt = max(1.0e-9, self.maxRt - calOffset)
		new.cumRt = max(1.0e-9, self.avgRt - calOffset)
		new.count = 1
		return new

	def dump(self, name):
		name += " " * (6 - len(name))
		return "%s:  min: %.3f us, max: %.3f us, avg: %.3f us" % (
			name,
			self.minRt * 1.0e6,
			self.maxRt * 1.0e6,
			self.avgRt * 1.0e6)

class InsnMeas(object): #+cdef
	def __init__(self):
		self.__perf_counter = time.perf_counter

		self.__data = [None] * u32_to_s16(AwlInsnTypes.NR_TYPES + 1) #+suffix-u
		for i in range(AwlInsnTypes.NR_TYPES + 1):
			self.__data[i] = InsnMeasData()

		self.__runOffsetCal()

	def __runOffsetCal(self):
		calTime = 3.0
		printInfo("Running instruction measurement "
			  "offset calibration (takes %.1f s)..." % (calTime))
		calEnd = monotonic_time() + calTime
		while monotonic_time() < calEnd:
			self.meas(True, AwlInsnTypes.NR_TYPES)
			self.meas(False, AwlInsnTypes.NR_TYPES)
		printInfo("Instruction measurement cal offset = %.3f us" % (
			  self.__calOffset * 1.0e6))

	def meas(self, begin, insnType): #@nocy
#@cy	cdef void meas(self, _Bool begin, uint32_t insnType):
#@cy		cdef InsnMeasData measData
#@cy		cdef double rt
#@cy		cdef double now

		now = self.__perf_counter()
		measData = self.__data[insnType]
		if begin:
			measData.measStart = now
		else:
			rt = now - measData.measStart
			measData.cumRt += rt
			measData.count += 1
			measData.minRt = min(measData.minRt, rt)
			measData.maxRt = max(measData.maxRt, rt)
			measData.measured = True

	@property
	def haveAnyMeasurements(self):
		return any(self.__data[i].measured
			   for i in range(AwlInsnTypes.NR_TYPES))

	@property
	def __calOffset(self):
		cal = self.__data[AwlInsnTypes.NR_TYPES]
		calOffset = cal.avgRt
		return calOffset

	@property
	def __allMeasData(self):
		calOffset = self.__calOffset
		for insnType in range(AwlInsnTypes.NR_TYPES):
			measData = self.__data[insnType]
			if measData.measured:
				measData = measData.subtractCal(calOffset)
				yield insnType, measData

	def dump(self):
		if not self.haveAnyMeasurements:
			return
		ret = []
		ret.append("Instruction time measurements:")
		for insnType, measData in self.__allMeasData:
			name = AwlInsnTypes.type2name_german[insnType]
			ret.append(measData.dump(name))
		return "\n".join(ret) + "\n"

	def dumpCSV(self):
		if not self.haveAnyMeasurements:
			return ""
		ret = [ "instruction type;"
			"instruction name;"
			"minimum runtime (µs);"
			"maximum runtime (µs);"
			"average runtime (µs)" ]
		for insnType, measData in self.__allMeasData:
			name = AwlInsnTypes.type2name_german[insnType]
			ret.append("%d; %s;%.3f;%.3f;%.3f" % (
				insnType,
				AwlInsnTypes.type2name_german[insnType],
				measData.minRt * 1.0e6,
				measData.maxRt * 1.0e6,
				measData.avgRt * 1.0e6))
		return "\n".join(ret) + "\n"
