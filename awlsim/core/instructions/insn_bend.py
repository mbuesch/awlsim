# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

from awlsim.core.instructions.main import *


class AwlInsn_BEND(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_BEND, rawInsn)
		self.assertOpCount(0)

	def __run_UB(self, pse):
		s = self.cpu.statusWord
		if pse.NER:
			s.VKE &= pse.VKE
			s.VKE |= pse.OR
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_UNB(self, pse):
		s = self.cpu.statusWord
		s.VKE = s.VKE ^ 1
		if pse.NER:
			s.VKE &= pse.VKE
			s.VKE |= pse.OR
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_OB(self, pse):
		s = self.cpu.statusWord
		if pse.NER:
			s.VKE |= pse.VKE
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_ONB(self, pse):
		s = self.cpu.statusWord
		s.VKE = s.VKE ^ 1
		if pse.NER:
			s.VKE |= pse.VKE
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_XB(self, pse):
		s = self.cpu.statusWord
		if pse.NER:
			s.VKE ^= pse.VKE
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	def __run_XNB(self, pse):
		s = self.cpu.statusWord
		s.VKE = s.VKE ^ 1
		if pse.NER:
			s.VKE ^= pse.VKE & 1
		s.OR, s.STA, s.NER = pse.OR, 1, 1

	__typeCalls = {
		AwlInsn.TYPE_UB		: __run_UB,
		AwlInsn.TYPE_UNB	: __run_UNB,
		AwlInsn.TYPE_OB		: __run_OB,
		AwlInsn.TYPE_ONB	: __run_ONB,
		AwlInsn.TYPE_XB		: __run_XB,
		AwlInsn.TYPE_XNB	: __run_XNB,
	}

	def run(self):
		try:
			pse = self.cpu.callStackTop.parenStack.pop()
		except IndexError as e:
			raise AwlSimError("Parenthesis stack underflow")
		return self.__typeCalls[pse.insnType](self, pse)
