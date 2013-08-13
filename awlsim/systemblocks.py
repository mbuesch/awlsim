# -*- coding: utf-8 -*-
#
# AWL simulator - System-blocks
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

from awlsim.instructions.insn_generic_call import *
from awlsim.blocks import *


class SystemBlock(Block):
	def __init__(self, cpu, index, interface):
		insns = [
			AwlInsn_GENERIC_CALL(cpu, self.run),
		]
		Block.__init__(self, insns, index, interface)
		self.cpu = cpu

	def run(self):
		# Reimplement this method
		raise NotImplementedError

	# Fetch the value of a block-interface field.
	def fetchInterfaceFieldByName(self, name):
		#TODO: We should cache the operator.
		operator = self.interface.getOperatorForFieldName(name, False)
		return self.cpu.fetch(operator)

	# Store a value to a block-interface field.
	def storeInterfaceFieldByName(self, name, value):
		#TODO: We should cache the operator.
		operator = self.interface.getOperatorForFieldName(name, False)
		return self.cpu.store(operator, value)

class SFBInterface(FBInterface):
	pass

class SFB(SystemBlock):
	def __init__(self, cpu, index):
		SystemBlock.__init__(self, cpu, index, SFBInterface())

	def __repr__(self):
		return "SFB %d" % self.index

class SFCInterface(FCInterface):
	pass

class SFC(SystemBlock):
	def __init__(self, cpu, index):
		SystemBlock.__init__(self, cpu, index, SFCInterface())

	def __repr__(self):
		return "SFC %d" % self.index
