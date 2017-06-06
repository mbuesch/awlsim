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


class AwlInsn_RND(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
#@cy		self.__isPy2Compat = isPy2Compat

		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_RND, rawInsn, **kwargs)
		self.assertOpCount(0)

	def __run_python2(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef double accu1
#@cy		cdef int64_t accu1_floor
#@cy		cdef int64_t accu1_int

		s = self.cpu.statusWord
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			accu1_floor = int(accu1)
			if abs(accu1 - accu1_floor) == 0.5:
				accu1_int = accu1_floor
				if accu1_int & 1:
					accu1_int += 1 if accu1_int > 0 else -1
			else:
				accu1_int = int(round(accu1))
			if accu1_int > 2147483647 or accu1_int < -2147483648: #@nocy
#@cy			if accu1_int > 2147483647LL or accu1_int < -2147483648LL:
				raise ValueError
		except (ValueError, OverflowError) as e:
			s.OV, s.OS = 1, 1
			return
		self.cpu.accu1.setDWord(accu1_int)

	def __run_python3(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef double accu1
#@cy		cdef int64_t accu1_int

		s = self.cpu.statusWord
		accu1 = self.cpu.accu1.getPyFloat()
		try:
			accu1_int = int(round(accu1))
			if accu1_int > 2147483647 or accu1_int < -2147483648: #@nocy
#@cy			if accu1_int > 2147483647LL or accu1_int < -2147483648LL:
				raise ValueError
		except (ValueError, OverflowError) as e:
			s.OV, s.OS = 1, 1
			return
		self.cpu.accu1.setDWord(accu1_int)

	run = py23(__run_python2, __run_python3) #@nocy
#@cy	cdef run(self):
#@cy		if self.__isPy2Compat:
#@cy			self.__run_python2()
#@cy		else:
#@cy			self.__run_python3()
