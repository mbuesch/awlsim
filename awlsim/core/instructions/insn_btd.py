# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *

from awlsim.core.instructions.main import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport


class AwlInsn_BTD(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_BTD, rawInsn, **kwargs)
		self.assertOpCount(0)

	def run(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef uint32_t accu1
#@cy		cdef uint32_t bcd
#@cy		cdef uint8_t a
#@cy		cdef uint8_t b
#@cy		cdef uint8_t c
#@cy		cdef uint8_t d
#@cy		cdef uint8_t e
#@cy		cdef uint8_t f
#@cy		cdef uint8_t g
#@cy		cdef uint32_t binval

		accu1 = self.cpu.accu1.get()
		bcd = accu1 & 0x0FFFFFFF
		a, b, c, d, e, f, g = (bcd & 0xF), ((bcd >> 4) & 0xF),\
				((bcd >> 8) & 0xF), ((bcd >> 12) & 0xF),\
				((bcd >> 16) & 0xF), ((bcd >> 20) & 0xF),\
				((bcd >> 24) & 0xF)
		if bcd > 0x9999999 or a > 9 or b > 9 or c > 9 or\
		   d > 9 or e > 9 or f > 9 or g > 9:
			raise AwlSimError("Invalid BCD value")
		binval = (a + (b * 10) + (c * 100) + (d * 1000) +\
			  (e * 10000) + (f * 100000) +\
			  (g * 1000000)) & 0xFFFFFFFF
		if accu1 & 0x80000000:
			binval = (-binval) & 0xFFFFFFFF
		self.cpu.accu1.set(binval)
