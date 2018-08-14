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

#from libc.stdlib cimport abs #@cy


class AwlInsn_DTB(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_DTB, rawInsn, **kwargs)
		self.assertOpCount(0)

	def run(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef int32_t binval
#@cy		cdef uint32_t binvalabs
#@cy		cdef uint32_t bcd

		s = self.cpu.statusWord
		binval, bcd = dwordToSignedPyInt(self.cpu.accu1.get()), 0
		if binval < 0:
			bcd = 0xF0000000
		binvalabs = abs(binval)
		if binvalabs > 9999999:
			s.OV, s.OS = 1, 1
			return
		bcd |= binvalabs % 10				#+suffix-u
		bcd |= ((binvalabs // 10) % 10) << 4		#+suffix-u
		bcd |= ((binvalabs // 100) % 10) << 8		#+suffix-u
		bcd |= ((binvalabs // 1000) % 10) << 12		#+suffix-u
		bcd |= ((binvalabs // 10000) % 10) << 16	#+suffix-u
		bcd |= ((binvalabs // 100000) % 10) << 20	#+suffix-u
		bcd |= ((binvalabs // 1000000) % 10) << 24	#+suffix-u
		self.cpu.accu1.set(bcd)
		s.OV = 0
