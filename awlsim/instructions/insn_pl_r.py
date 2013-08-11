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


class AwlInsn_PL_R(AwlInsn):
	def __init__(self, cpu, rawInsn):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_PL_R, rawInsn)
		self.assertOpCount(0)

	def run(self):
		accu2, accu1 = self.cpu.accu2.getPyFloat(),\
			       self.cpu.accu1.getPyFloat()
		_sum = accu2 + accu1
		self.cpu.accu1.setPyFloat(_sum)
		self.cpu.callStackTop.status.setForFloatingPoint(_sum)