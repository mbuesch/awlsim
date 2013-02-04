# -*- coding: utf-8 -*-
#
# AWL simulator - CPU call stack
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from awldatatypes import *
from awlstatusword import *
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

	def __init__(self, cpu, block, db):
		self.cpu = cpu
		self.status = S7StatusWord()
		self.parenStack = []
		self.ip = 0
		self.localdata = self.localdataCache.get(cpu)
		assert(len(self.localdata) == cpu.specs.getNrLocalbytes())
		self.block = block
		self.db = db

	@property
	def insns(self):
		return self.block.insns

	@property
	def labels(self):
		return self.block.labels

	def destroy(self):
		# Only put it back into the cache, if the size didn't change.
		if len(self.localdata) == self.cpu.specs.getNrLocalbytes():
			self.localdataCache.put(self.localdata)
		self.localdata = None

	def __repr__(self):
		return str(self.block)


