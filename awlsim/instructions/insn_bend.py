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

from awlsim.instructions.main import *


class AwlInsn_BEND(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_BEND, rawInsn)
		self.assertOpCount(0)

	def run(self):
		s = self.cpu.statusWord
		try:
			pse = self.cpu.parenStack.pop()
		except IndexError as e:
			raise AwlSimError("Parenthesis stack underflow")
		if pse.insnType == AwlInsn.TYPE_UB:
			if pse.NER:
				s.VKE &= pse.VKE
				s.VKE |= pse.OR
		elif pse.insnType == AwlInsn.TYPE_UNB:
			s.VKE = s.VKE ^ 1
			if pse.NER:
				s.VKE &= pse.VKE
				s.VKE |= pse.OR
		elif pse.insnType == AwlInsn.TYPE_OB:
			if pse.NER:
				s.VKE |= pse.VKE
		elif pse.insnType == AwlInsn.TYPE_ONB:
			s.VKE = s.VKE ^ 1
			if pse.NER:
				s.VKE |= pse.VKE
		elif pse.insnType == AwlInsn.TYPE_XB:
			if pse.NER:
				s.VKE ^= pse.VKE
		elif pse.insnType == AwlInsn.TYPE_XNB:
			s.VKE = s.VKE ^ 1
			if pse.NER:
				s.VKE ^= pse.VKE & 1
		else:
			assert(0)
		s.OR, s.STA, s.NER = pse.OR, 1, 1
