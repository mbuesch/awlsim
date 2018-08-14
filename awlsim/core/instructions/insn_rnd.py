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

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.instructions.main import * #+cimport
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport

#from libc.math cimport round #@cy
#from libc.math cimport fabs #@cy
fabs = abs #@nocy


class AwlInsn_RND(AwlInsn): #+cdef

	__slots__ = (
		"__0p5_plus_epsilon",
		"__0p5_minus_epsilon",
	)

	def __init__(self, cpu, rawInsn=None, **kwargs):
#@cy		cdef uint32_t p5DWord
#@cy		cdef uint32_t epsilonDWord

		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_RND, rawInsn, **kwargs)
		self.assertOpCount(0)

		# Calculate the values next to 0.5 in a 32 bit IEEE float.
		p5DWord = pyFloatToDWord(0.5)
		epsilonDWord = floatConst.minNormPosFloat32DWord
		self.__0p5_plus_epsilon = dwordToPyFloat(p5DWord + epsilonDWord)
		self.__0p5_minus_epsilon = dwordToPyFloat(p5DWord - epsilonDWord)

	def __run_python2_or_cython(self): #@nocy
#@cy	cdef run(self):
#@cy		cdef S7StatusWord s
#@cy		cdef double accu1
#@cy		cdef double frac
#@cy		cdef int64_t accu1_floor
#@cy		cdef int64_t accu1_int

		s = self.cpu.statusWord
		accu1 = self.cpu.accu1.getPyFloat()
		if -2147483648.0 <= accu1 <= 2147483647.0: #+likely
			accu1_floor = int(accu1) #@nocy
#@cy			accu1_floor = <int64_t>(accu1)
			frac = fabs(accu1 - accu1_floor)
			if (frac < self.__0p5_plus_epsilon and
			    frac > self.__0p5_minus_epsilon):
				accu1_int = accu1_floor
				if accu1_int & 1:
					accu1_int += 1 if accu1_int > 0 else -1
			else:
				accu1_int = int(round(accu1)) #@nocy
#@cy				accu1_int = <int64_t>(round(accu1))
			if -2147483648 <= accu1_int <= 2147483647: #+likely #+suffix-LL
				self.cpu.accu1.setDWord(accu1_int)
			else:
				s.OV, s.OS = 1, 1
		else:
			s.OV, s.OS = 1, 1

	def __run_python3(self):					#@nocy
		s = self.cpu.statusWord					#@nocy
		accu1 = self.cpu.accu1.getPyFloat()			#@nocy
		if -2147483648.0 <= accu1 <= 2147483647.0:		#@nocy
			accu1_int = round(accu1)			#@nocy
			if -2147483648 <= accu1_int <= 2147483647:	#@nocy
				self.cpu.accu1.setDWord(accu1_int)	#@nocy
			else:						#@nocy
				s.OV, s.OS = 1, 1			#@nocy
		else:							#@nocy
			s.OV, s.OS = 1, 1				#@nocy

	run = py23(__run_python2_or_cython, __run_python3)		#@nocy
