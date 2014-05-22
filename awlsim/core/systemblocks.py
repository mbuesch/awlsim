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

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.core.compat import *

from awlsim.core.instructions.insn_generic_call import *
from awlsim.core.blocks import *


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
		return self.cpu.fetch(self.__interfaceOpers[name])

	# Store a value to a block-interface field.
	def storeInterfaceFieldByName(self, name, value):
		return self.cpu.store(self.__interfaceOpers[name], value)

	# Resolve hard wired symbolic accesses
	# (i.e. accesses not done in AWL instructions)
	def resolveHardwiredSymbols(self):
		self.__interfaceOpers = {}
		for field in self.interface.fields_IN_OUT_INOUT:
			# Create a scratch-operator for the access.
			oper = AwlOperator(AwlOperator.NAMED_LOCAL, 0,
					   field.name)
			# Resolve the scratch-operator.
			oper = self.cpu.resolveNamedLocal(block=self, insn=None,
							  oper=oper, pointer=False)
			# Store the scratch operator for later use.
			self.__interfaceOpers[field.name] = oper

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
