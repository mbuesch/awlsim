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
from awlsim.common.datatypehelpers import * #+cimport

from awlsim.core.instructions.main import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport

from math import sqrt
#from libc.math cimport sqrt #@cy


class AwlInsn_SQRT(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_SQRT, rawInsn, **kwargs)
		self.assertOpCount(0)

	def run(self): #+cdef
#@cy		cdef double accu1Float
#@cy		cdef uint32_t accu1DWord

		accu1DWord = self.cpu.accu1.get()
		accu1Float = self.cpu.accu1.getPyFloat()
		if isNaN(accu1DWord):
			self.cpu.accu1.set(floatConst.pNaNDWord)
			accu1Float = self.cpu.accu1.getPyFloat()
		elif accu1DWord == floatConst.negInfDWord or\
		     accu1DWord == floatConst.posInfDWord:
			pass
		elif accu1Float < 0.0:
			accu1Float = floatConst.nNaNFloat
			self.cpu.accu1.set(floatConst.pNaNDWord)
		else:
			accu1Float = sqrt(accu1Float)
			self.cpu.accu1.setPyFloat(accu1Float)
		self.cpu.statusWord.setForFloatingPoint(accu1Float)
