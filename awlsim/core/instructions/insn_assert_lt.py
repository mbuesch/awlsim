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


class AwlInsn_ASSERT_LT(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_ASSERT_LT, rawInsn, **kwargs)
		self.assertOpCount(2)

	def run(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef AwlMemoryObject memObj0
#@cy		cdef AwlMemoryObject memObj1

		s = self.cpu.statusWord
		memObj0 = self.cpu.fetch(self.op0, self._widths_all)
		memObj1 = self.cpu.fetch(self.op1, self._widths_all)
		if memObj0.width <= 32 and memObj1.width <= 32:
			val0 = AwlMemoryObject_asScalar(memObj0)
			val1 = AwlMemoryObject_asScalar(memObj1)
		else:
			val0 = AwlMemoryObject_asBytes(memObj0)
			val1 = AwlMemoryObject_asBytes(memObj1)

		if not (val0 < val1):
			raise AwlSimError("Assertion failed")
		s.NER = 0
