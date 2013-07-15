# -*- coding: utf-8 -*-
#
# AWL simulator - CPU call stack
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awlsim.datatypes import *
from awlsim.blocks import *
from awlsim.statusword import *
from awlsim.parameters import *
from awlsim.objectcache import *
from awlsim.util import *


class CallStackElem(object):
	"Call stack element"

	localdataCache = ObjectCache(lambda cpu:
		[ LocalByte()
		  for _ in range(cpu.specs.nrLocalbytes) ]
	)

	@classmethod
	def resetCache(cls):
		cls.localdataCache.reset()

	def __init__(self, cpu, block, instanceDB=None,
		     interfaceDB=None, parameters=()):
		(self.cpu,
		 self.status,
		 self.parenStack,
		 self.ip,
		 self.localdata,
		 self.block,
		 self.insns,
		 self.labels,
		 self.instanceDB,
		 self.interfaceDB) = (
			cpu,
			S7StatusWord(),
			[],
			0,
			self.localdataCache.get(cpu),
			block,
			block.insns,
			block.labels,
			instanceDB,
			interfaceDB if interfaceDB else instanceDB,
		)

		# Handle parameters
		self.__outboundParams = []
		for param in parameters:
			if param.isOutbound(block.interface):
				# This is an outbound parameter.
				self.__outboundParams.append(param)
			if param.isInbound(block.interface):
				# This is an inbound parameter.
				# Transfer data into DBI
				structField = self.interfaceDB.structInstance.struct.getField(param.lvalueName)
				if structField.dataType.type in BlockInterface.callByRef_Types:
					data = param.rvalueOp.value.byteOffset
				else:
					data = self.cpu.fetch(param.rvalueOp)
				self.interfaceDB.structInstance.setData(structField.offset,
									structField.bitSize,
									data)

	# Transfer data out of DBI
	def handleOutParameters(self):
		for param in self.__outboundParams:
			self.cpu.store(
				param.rvalueOp,
				self.interfaceDB.structInstance.getFieldData(param.lvalueName)
			)

	def destroy(self):
		# Only put it back into the cache, if the size didn't change.
		if len(self.localdata) == self.cpu.specs.nrLocalbytes:
			self.localdataCache.put(self.localdata)

	def __repr__(self):
		return str(self.block)
