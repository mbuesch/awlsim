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


class AwlInsn_NEGD(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_NEGD, rawInsn)
		self.assertOpCount(0)

	def run(self):
		s = self.cpu.callStackTop.status
		value = -(self.cpu.accu1.getSignedDWord())
		self.cpu.accu1.setDWord(value)
		accu1 = self.cpu.accu1.getSignedDWord()
		if accu1 == 0:
			s.A1, s.A0, s.OV = 0, 0, 0
		elif accu1 < 0:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0
		if value > 0x7FFFFFFF or value < -2147483648:
			s.OV, s.OS = 1, 1