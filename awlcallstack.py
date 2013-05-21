# -*- coding: utf-8 -*-
#
# AWL simulator - CPU call stack
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awldatatypes import *
from awlstatusword import *
from awlparameters import *
from objectcache import *
from util import *


class CallStackElem(object):
	"Call stack element"

	localdataCache = ObjectCache(lambda cpu:
		[ LocalByte()
		  for _ in range(cpu.specs.getNrLocalbytes()) ]
	)

	@classmethod
	def resetCache(cls):
		cls.localdataCache.reset()

	def __init__(self, cpu, block, instanceDB=None,
		     interfaceDB=None, parameters=()):
		self.cpu = cpu
		self.status = S7StatusWord()
		self.parenStack = []
		self.ip = 0
		self.localdata = self.localdataCache.get(cpu)
		assert(len(self.localdata) == cpu.specs.getNrLocalbytes())
		self.block = block
		self.instanceDB = instanceDB
		self.interfaceDB = interfaceDB if interfaceDB else instanceDB

		self.inboundParams = [ param for param in parameters
				       if param.isInbound(block.interface) ]
		self.outboundParams = [ param for param in parameters
					if param.isOutbound(block.interface) ]
		self.handleInParameters()

	@property
	def insns(self):
		return self.block.insns

	@property
	def labels(self):
		return self.block.labels

	# Transfer data into DBI
	def handleInParameters(self):
		for param in self.inboundParams:
			self.interfaceDB.structInstance.setFieldData(
				param.lvalueName,
				self.cpu.fetch(param.rvalueOp)
			)

	# Transfer data out of DBI
	def handleOutParameters(self):
		for param in self.outboundParams:
			self.cpu.store(
				param.rvalueOp,
				self.interfaceDB.structInstance.getFieldData(param.lvalueName)
			)

	def destroy(self):
		# Only put it back into the cache, if the size didn't change.
		if len(self.localdata) == self.cpu.specs.getNrLocalbytes():
			self.localdataCache.put(self.localdata)
		self.localdata = None

	def __repr__(self):
		return str(self.block)
