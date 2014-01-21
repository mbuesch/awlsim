# -*- coding: utf-8 -*-
#
# AWL simulator - CPU call stack
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

from awlsim.datatypes import *
from awlsim.blocks import *
from awlsim.parameters import *
from awlsim.objectcache import *
from awlsim.util import *


class CallStackElem(object):
	"Call stack element"

	localdataCache = ObjectCache(lambda cpu: ByteArray(cpu.specs.nrLocalbytes))

	@classmethod
	def resetCache(cls):
		cls.localdataCache.reset()

	def __init__(self, cpu, block, interfaceDB=None, parameters=()):
		(self.cpu,
		 self.parenStack,
		 self.ip,
		 self.localdata,
		 self.block,
		 self.insns,
		 self.labels,
		 self.interfaceDB,
		 self.prevDbRegister,
		 self.prevDiRegister) = (
			cpu,
			[],
			0,
			self.localdataCache.get(cpu),
			block,
			block.insns,
			block.labels,
			interfaceDB,
			cpu.dbRegister,
			cpu.diRegister,
		)

		# Handle parameters
		self.__outboundParams = []
		if parameters:
			blockInterface, interfaceDB, structInstance, callByRef_Types =\
				block.interface, \
				self.interfaceDB, \
				self.interfaceDB.structInstance, \
				BlockInterface.callByRef_Types
			for param in parameters:
				if param.isOutbound(blockInterface):
					# This is an outbound parameter.
					self.__outboundParams.append(param)
				if param.isInbound(blockInterface):
					# This is an inbound parameter.
					# Transfer data into DBI
					structField = param.getLvalueStructField(interfaceDB)
					if structField.dataType.type in callByRef_Types:
						data = param.rvalueOp.resolve().value.byteOffset
					else:
						data = cpu.fetch(param.rvalueOp)
					structInstance.setFieldData(structField, data)

	# Handle the exit from this code block.
	def handleBlockExit(self):
		# Transfer data out of DBI
		if self.__outboundParams:
			cpu, interfaceDB, structInstance =\
				self.cpu, \
				self.interfaceDB, \
				self.interfaceDB.structInstance
			for param in self.__outboundParams:
				cpu.store(
					param.rvalueOp,
					structInstance.getFieldData(param.getLvalueStructField(interfaceDB))
				)
		# Assign the DB/DI registers
		if self.block.interface.requiresInstanceDB:
			# We are returning from an FB
			self.cpu.dbRegister, self.cpu.diRegister = self.interfaceDB, self.prevDiRegister
		else:
			# We are returning from an FC
			self.cpu.dbRegister, self.cpu.diRegister = self.prevDbRegister, self.prevDiRegister

	def destroy(self):
		# Only put it back into the cache, if the size didn't change.
		if len(self.localdata) == self.cpu.specs.nrLocalbytes:
			self.localdataCache.put(self.localdata)

	def __repr__(self):
		return str(self.block)
