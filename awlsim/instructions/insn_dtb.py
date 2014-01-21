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


class AwlInsn_DTB(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_DTB, rawInsn)
		self.assertOpCount(0)

	def run(self):
		s = self.cpu.statusWord
		binval, bcd = dwordToSignedPyInt(self.cpu.accu1.get()), 0
		if binval < 0:
			bcd |= 0xF0000000
		binval = abs(binval)
		if binval > 9999999:
			s.OV, s.OS = 1, 1
			return
		bcd |= binval % 10
		bcd |= ((binval // 10) % 10) << 4
		bcd |= ((binval // 100) % 10) << 8
		bcd |= ((binval // 1000) % 10) << 12
		bcd |= ((binval // 10000) % 10) << 16
		bcd |= ((binval // 100000) % 10) << 20
		bcd |= ((binval // 1000000) % 10) << 24
		self.cpu.accu1.set(bcd)
		s.OV = 0
