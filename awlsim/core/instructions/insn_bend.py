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
#from awlsim.core.cpu cimport * #@cy


class AwlInsn_BEND(AwlInsn): #+cdef

	__slots__ = (
		"__typeCalls", #@nocy
	)

	def __init__(self, cpu, rawInsn=None, **kwargs):
		self.__typeCalls = self.__typeCallsDict #@nocy
#@cy		self.__type_UB = self.TYPE_UB
#@cy		self.__type_UNB = self.TYPE_UNB
#@cy		self.__type_OB = self.TYPE_OB
#@cy		self.__type_ONB = self.TYPE_ONB
#@cy		self.__type_XB = self.TYPE_XB
#@cy		self.__type_XNB = self.TYPE_XNB

		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_BEND, rawInsn, **kwargs)
		self.assertOpCount(0)

	def __run_UB(self, pse): #@nocy
#@cy	cdef __run_UB(self, ParenStackElem pse):
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		if pse.NER:
			s.VKE &= pse.VKE
		s.VKE |= pse.OR
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_UNB(self, pse): #@nocy
#@cy	cdef __run_UNB(self, ParenStackElem pse):
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		s.VKE = s.VKE ^ 1
		if pse.NER:
			s.VKE &= pse.VKE
		s.VKE |= pse.OR
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_OB(self, pse): #@nocy
#@cy	cdef __run_OB(self, ParenStackElem pse):
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		if pse.NER:
			s.VKE |= pse.VKE
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_ONB(self, pse): #@nocy
#@cy	cdef __run_ONB(self, ParenStackElem pse):
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		s.VKE = s.VKE ^ 1
		if pse.NER:
			s.VKE |= pse.VKE
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_XB(self, pse): #@nocy
#@cy	cdef __run_XB(self, ParenStackElem pse):
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		if pse.NER:
			s.VKE ^= pse.VKE
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_XNB(self, pse): #@nocy
#@cy	cdef __run_XNB(self, ParenStackElem pse):
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		s.VKE = s.VKE ^ 1
		if pse.NER:
			s.VKE ^= pse.VKE & 1
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	__typeCallsDict = {				#@nocy
		AwlInsn.TYPE_UB		: __run_UB,	#@nocy
		AwlInsn.TYPE_UNB	: __run_UNB,	#@nocy
		AwlInsn.TYPE_OB		: __run_OB,	#@nocy
		AwlInsn.TYPE_ONB	: __run_ONB,	#@nocy
		AwlInsn.TYPE_XB		: __run_XB,	#@nocy
		AwlInsn.TYPE_XNB	: __run_XNB,	#@nocy
	}						#@nocy

	def run(self): #+cdef
#@cy		cdef ParenStackElem pse

		try:
			pse = self.cpu.callStackTop.parenStack.pop()
		except IndexError as e:
			raise AwlSimError("Parenthesis stack underflow")

		self.__typeCalls[pse.insnType](self, pse) #@nocy

#@cy		if pse.insnType == self.__type_UB:
#@cy			self.__run_UB(pse)
#@cy		elif pse.insnType == self.__type_UNB:
#@cy			self.__run_UNB(pse)
#@cy		elif pse.insnType == self.__type_OB:
#@cy			self.__run_OB(pse)
#@cy		elif pse.insnType == self.__type_ONB:
#@cy			self.__run_ONB(pse)
#@cy		elif pse.insnType == self.__type_XB:
#@cy			self.__run_XB(pse)
#@cy		elif pse.insnType == self.__type_XNB:
#@cy			self.__run_XNB(pse)
#@cy		else:
#@cy			raise KeyError
