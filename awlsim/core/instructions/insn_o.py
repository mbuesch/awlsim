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


class AwlInsn_O(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_O, rawInsn)
		self.assertOpCount((0, 1))

		if self.ops:
			self.run = self.__run_withOps
		else:
			self.run = self.__run_noOps

	def __run_withOps(self):
		s, STA = self.cpu.statusWord,\
			self.cpu.fetch(self.ops[0], (1,))
		if s.NER:
			s.OR, s.STA, s.VKE, s.NER = 0, STA, (s.VKE | STA), 1
		else:
			s.OR, s.STA, s.VKE, s.NER = 0, STA, STA, 1

	def __run_noOps(self):
		s = self.cpu.statusWord
		# UND vor ODER
		s.OR, s.STA, s.NER = s.VKE, 1, 0
