# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
#
# Copyright 2012-2018 Michael Buesch <m@bues.ch>
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

from awlsim.core.instructions.main import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport


class AwlInsn_PL_D(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_PL_D, rawInsn, **kwargs)
		self.assertOpCount(0)

	def run(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef uint32_t sumTrunc
#@cy		cdef int64_t _sum

		s = self.cpu.statusWord
		_sum = self.cpu.accu2.getSignedDWord()
		_sum += self.cpu.accu1.getSignedDWord()
		self.cpu.accu1.setDWord(_sum)
		if self.cpu.is4accu:
			self.cpu.accu2.copyFrom(self.cpu.accu3)
			self.cpu.accu3.copyFrom(self.cpu.accu4)
		sumTrunc = _sum & 0xFFFFFFFF #@nocy
#@cy		sumTrunc = <uint32_t>_sum
		if sumTrunc == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif sumTrunc & 0x80000000: #+suffix-u
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if _sum > 0x7FFFFFFF or _sum < -2147483648: #+suffix-LL
			s.OV, s.OS = 1, 1
