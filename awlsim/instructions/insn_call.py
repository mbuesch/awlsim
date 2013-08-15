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


class AwlInsn_AbstractCall(AwlInsn):
	pass

class AwlInsn_CALL(AwlInsn_AbstractCall):
	def __init__(self, cpu, rawInsn):
		AwlInsn_AbstractCall.__init__(self, cpu, AwlInsn.TYPE_CALL, rawInsn)
		self.assertOpCount((1,2))

		if len(self.ops) == 1:
			self.run = self.__run_CALL_FC
		else:
			self.run = self.__run_CALL_FB

	def __run_CALL_FC(self):
		self.cpu.run_CALL(self.ops[0], None, self.params)
		s = self.cpu.callStackTop.status
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0

	def __run_CALL_FB(self):
		self.cpu.run_CALL(self.ops[0], self.ops[1], self.params)
		s = self.cpu.callStackTop.status
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0

class AwlInsn_CC(AwlInsn_AbstractCall):
	def __init__(self, cpu, rawInsn):
		AwlInsn_AbstractCall.__init__(self, cpu, AwlInsn.TYPE_CC, rawInsn)
		self.assertOpCount(1)

	def run(self):
		s = self.cpu.callStackTop.status
		if s.VKE:
			self.cpu.run_CALL(self.ops[0])
		s.OS, s.OR, s.STA, s.VKE, s.NER = 0, 0, 1, 1, 0

class AwlInsn_UC(AwlInsn_AbstractCall):
	def __init__(self, cpu, rawInsn):
		AwlInsn_AbstractCall.__init__(self, cpu, AwlInsn.TYPE_UC, rawInsn)
		self.assertOpCount(1)

	def run(self):
		self.cpu.run_CALL(self.ops[0])
		s = self.cpu.callStackTop.status
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
