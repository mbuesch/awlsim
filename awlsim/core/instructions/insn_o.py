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


class AwlInsn_O(AwlInsn): #+cdef

	__slots__ = (
		"run",
	)

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_O, rawInsn, **kwargs)
		self.assertOpCount((0, 1))

		if self.opCount:				#@nocy
			self.run = self.__run_withOps	#@nocy
		else:					#@nocy
			self.run = self.__run_noOps	#@nocy

	def __run_withOps(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef _Bool STA

		s, STA = self.cpu.statusWord,\
			self.cpu.fetch(self.op0, self._widths_1)
		if s.NER:
			s.OR, s.STA, s.VKE, s.NER = 0, STA, (s.VKE | STA), 1
		else:
			s.OR, s.STA, s.VKE, s.NER = 0, STA, STA, 1

	def __run_noOps(self): #+cdef
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		# UND vor ODER
		s.OR, s.STA, s.NER = s.VKE, 1, 0

#@cy	def run(self): #+cdef
#@cy		if self.opCount:
#@cy			self.__run_withOps()
#@cy		else:
#@cy			self.__run_noOps()
