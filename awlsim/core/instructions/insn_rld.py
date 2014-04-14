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


class AwlInsn_RLD(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_RLD, rawInsn)
		self.assertOpCount((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM, 0, 255)

	def run(self):
		s = self.cpu.statusWord
		accu1 = self.cpu.accu1.getDWord()
		if self.ops:
			count = self.ops[0].value
		else:
			count = self.cpu.accu2.getByte()
		if count <= 0:
			return
		count = max(0, count % 32)
		accu1 &= 0xFFFFFFFF
		accu1 = ((accu1 << count) | (accu1 >> (32 - count))) & 0xFFFFFFFF
		self.cpu.accu1.set(accu1)
		s.A0, s.A1, s.OV = 0, accu1 & 1, 0
