# -*- coding: utf-8 -*-
#
# AWL simulator - counters
#
# Copyright 2012-2019 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *
from awlsim.common.util import *


class Counter(object): #+cdef
	"""Classic AWL counter."""

	__slots__ = (
		"cpu",
		"index",
		"prevVKE_FR",
		"prevVKE_S",
		"prevVKE_ZV",
		"prevVKE_ZR",
		"counter",
	)

	def __init__(self, cpu, index):
		self.cpu = cpu
		self.index = index
		self.prevVKE_FR = 0
		self.prevVKE_S = 0
		self.prevVKE_ZV = 0
		self.prevVKE_ZR = 0
		self.counter = 0

	# Get the counter state (Q)
	def get(self): #@nocy
#@cy	cdef _Bool get(self):
		return 1 if self.counter else 0

	# Get the binary counter value (DUAL)
	def getValueBin(self): #@nocy
#@cy	cdef uint16_t getValueBin(self):
		return self.counter

	# Get the BCD counter value (DEZ)
	def getValueBCD(self): #@nocy
#@cy	cdef uint16_t getValueBCD(self):
#@cy		cdef uint16_t bcd

		bcd = self.counter % 10				#+suffix-u
		bcd |= ((self.counter // 10) % 10) << 4		#+suffix-u
		bcd |= ((self.counter // 100) % 10) << 8	#+suffix-u

		return bcd

	# Set the counter to a BCD value
	def setValueBCD(self, bcd): #@nocy
#@cy	cdef setValueBCD(self, uint16_t bcd):
#@cy		cdef uint16_t a
#@cy		cdef uint16_t b
#@cy		cdef uint16_t c

		a, b, c = (bcd & 0xF),\
			  ((bcd >> 4) & 0xF),\
			  ((bcd >> 8) & 0xF)
		if bcd > 0x999 or a > 9 or b > 9 or c > 9:
			raise AwlSimError("Invalid BCD value")
		self.counter = a + (b * 10) + (c * 100)

	# Set (S) the counter to a value (accu1)
	def set(self, VKE): #@nocy
#@cy	cdef set(self, _Bool VKE):
		if (self.prevVKE_S ^ 1) & VKE:
			self.setValueBCD(self.cpu.accu1.get())
		self.prevVKE_S = VKE

	# Reset (R) the counter
	def reset(self): #@nocy
#@cy	cdef void reset(self):
		self.counter = 0

	# Run the FR instruction
	def run_FR(self, VKE): #@nocy
#@cy	cdef void run_FR(self, _Bool VKE):
		if (self.prevVKE_FR ^ 1) & VKE:
			self.prevVKE_S = 0
			self.prevVKE_ZV = 0
			self.prevVKE_ZR = 0
		self.prevVKE_FR = VKE

	# Run the ZV instruction
	def run_ZV(self, VKE): #@nocy
#@cy	cdef void run_ZV(self, _Bool VKE):
		if (self.prevVKE_ZV ^ 1) & VKE:
			if self.counter < 999:
				self.counter += 1
		self.prevVKE_ZV = VKE

	# Run the ZR instruction
	def run_ZR(self, VKE): #@nocy
#@cy	cdef void run_ZR(self, _Bool VKE):
		if (self.prevVKE_ZR ^ 1) & VKE:
			if self.counter > 0:
				self.counter -= 1
		self.prevVKE_ZR = VKE
