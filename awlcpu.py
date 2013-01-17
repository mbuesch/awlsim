# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import time

from awlparser import *
from awldatatypes import *
from awlinstructions import *
from awloperators import *
from awlinsntrans import *
from awloptrans import *
from awlblocks import *
from awldatablocks import *
from awlstatusword import *
from awllabels import *
from awltimers import *
from awlcounters import *
from util import *
from lfsr import *
from objectcache import *


class FlagByte(GenericByte):
	"Flag byte"

	def __init__(self):
		GenericByte.__init__(self)

class InputByte(GenericByte):
	"PAE byte"

	def __init__(self):
		GenericByte.__init__(self)

class OutputByte(GenericByte):
	"PAA byte"

	def __init__(self):
		GenericByte.__init__(self)

class LocalByte(GenericByte):
	"L byte"

	def __init__(self):
		GenericByte.__init__(self)

class Accu(GenericDWord):
	"Accumulator register"

	def __init__(self):
		GenericDWord.__init__(self)

class Adressregister(GenericDWord):
	"Address register"

	def __init__(self):
		GenericDWord.__init__(self)

class ParenStackElem(object):
	"Parenthesis stack element"

	def __init__(self, insnType, statusWord):
		self.insnType = insnType
		self.NER = statusWord.NER
		self.VKE = statusWord.VKE
		self.OR = statusWord.OR

	def __repr__(self):
		return '(insn="%s" VKE=%s OR=%d)' %\
			(AwlInsn.type2name[self.insnType],
			 self.VKE, self.OR)

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

class McrStackElem(object):
	"MCR stack element"

	def __init__(self, statusWord):
		self.VKE = statusWord.VKE

	def __bool__(self):
		return bool(self.VKE)

	__nonzero__ = __bool__

class S7CPUSpecs(object):
	"STEP 7 CPU Specifications"

	def __init__(self, cpu):
		self.cpu = None
		self.setNrAccus(2)
		self.setNrTimers(2048)
		self.setNrCounters(2048)
		self.setNrFlags(8192)
		self.setNrInputs(8192)
		self.setNrOutputs(8192)
		self.setNrLocalbytes(1024)
		self.cpu = cpu

	def setNrAccus(self, count):
		if count not in (2, 4):
			raise AwlSimError("Invalid number of accus")
		self.nrAccus = count
		if self.cpu:
			self.cpu.reallocate()

	def getNrAccus(self):
		return self.nrAccus

	def setNrTimers(self, count):
		self.nrTimers = count
		if self.cpu:
			self.cpu.reallocate()

	def getNrTimers(self):
		return self.nrTimers

	def setNrCounters(self, count):
		self.nrCounters = count
		if self.cpu:
			self.cpu.reallocate()

	def getNrCounters(self):
		return self.nrCounters

	def setNrFlags(self, count):
		self.nrFlags = count
		if self.cpu:
			self.cpu.reallocate()

	def getNrFlags(self):
		return self.nrFlags

	def setNrInputs(self, count):
		self.nrInputs = count
		if self.cpu:
			self.cpu.reallocate()

	def getNrInputs(self):
		return self.nrInputs

	def setNrOutputs(self, count):
		self.nrOutputs = count
		if self.cpu:
			self.cpu.reallocate()

	def getNrOutputs(self):
		return self.nrOutputs

	def setNrLocalbytes(self, count):
		self.nrLocalbytes = count
		if self.cpu:
			self.cpu.reallocate()

	def getNrLocalbytes(self):
		return self.nrLocalbytes

class S7CPU(object):
	"STEP 7 CPU"

	def __init__(self, sim):
		self.sim = sim
		self.simplePRNG = Simple_PRNG()
		self.specs = S7CPUSpecs(self)
		self.setCycleTimeLimit(5.0)
		self.setCycleExitCallback(None)
		self.setBlockExitCallback(None)
		self.setPostInsnCallback(None)
		self.setDirectPeripheralCallback(None)
		self.reset()
		self.__extendedInsnsEnabled = False

	def getSimplePRNG(self):
		return self.simplePRNG

	def enableExtendedInsns(self, en=True):
		self.__extendedInsnsEnabled = en

	def setCycleTimeLimit(self, newLimit):
		self.cycleTimeLimit = float(newLimit)

	def __translateInsn(self, rawInsn, ip):
		ex = None
		try:
			insn = AwlInsnTranslator.fromRawInsn(rawInsn,
				self.__extendedInsnsEnabled)
			insn.setCpu(self)
			insn.setIP(ip)
		except AwlSimError as e:
			ex = e
		if ex:
			raise AwlSimError("%s\nline %d: %s" %\
				(str(rawInsn), rawInsn.getLineNr(),
				 str(ex)))
		return insn

	def __translateInsns(self, rawInsns):
		insns = []
		for ip, rawInsn in enumerate(rawInsns):
			insns.append(self.__translateInsn(rawInsn, ip))
		return insns

	def __translateDBField(self, db, name, valueTokens, type):
		dtype = AwlDataType.makeByName(type)
		value = dtype.parseImmediate(valueTokens)
		db.addField(fieldData = value,
			    size = dtype.width,
			    name = name)

	def __translateDB(self, rawDB):
		db = DB(rawDB.index)
		if rawDB.isInstanceDB():
			if any(f.type for f in rawDB.fields):
				raise AwlSimError("DB %d is an instance DB, but "
					"declares a data structure." % rawDB.index)
			#TODO
			raise AwlSimError("Instance DBs not supported, yet.")
		else:
			for f in rawDB.fields:
				if not f.type:
					raise AwlSimError(
						"DB %d assigns field '%s', "
						"but does not declare it." %\
						(rawDB.index, f.name))
				if f.valueTokens is None:
					raise AwlSimError(
						"DB %d declares field '%s', "
						"but does not initialize." %\
						(rawDB.index, f.name))
				self.__translateDBField(db, f.name,
							f.valueTokens,
							f.type)
		return db

	def load(self, parseTree):
		# Translate the AWL tree
		self.reset()
		for obNumber in parseTree.obs.keys():
			insns = self.__translateInsns(parseTree.obs[obNumber].insns)
			self.obs[obNumber] = OB(insns, obNumber)
		for fbNumber in parseTree.fbs.keys():
			insns = self.__translateInsns(parseTree.fbs[fbNumber].insns)
			self.fbs[fbNumber] = FB(insns, fbNumber)
		for fcNumber in parseTree.fcs.keys():
			insns = self.__translateInsns(parseTree.fcs[fcNumber].insns)
			self.fcs[fcNumber] = FC(insns, fcNumber)
		for dbNumber in parseTree.dbs.keys():
			db = self.__translateDB(parseTree.dbs[dbNumber])
			self.dbs[dbNumber] = db
		try:
			self.obs[1]
		except KeyError:
			raise AwlSimError("No OB1 defined")

	def reallocate(self, force=False):
		if force or (self.specs.getNrAccus() == 4) != self.is4accu:
			self.accu1, self.accu2 = Accu(), Accu()
			if self.specs.getNrAccus() == 2:
				self.accu3, self.accu4 = None, None
			elif self.specs.getNrAccus() == 4:
				self.accu3, self.accu4 = Accu(), Accu()
			else:
				assert(0)
		if force or self.specs.getNrTimers() != len(self.timers):
			self.timers = [ Timer(self, i)
					for i in range(self.specs.getNrTimers()) ]
		if force or self.specs.getNrCounters() != len(self.counters):
			self.counters = [ Counter(self, i)
					  for i in range(self.specs.getNrCounters()) ]
		if force or self.specs.getNrFlags() != len(self.flags):
			self.flags = [ FlagByte()
				       for _ in range(self.specs.getNrFlags()) ]
		if force or self.specs.getNrInputs() != len(self.inputs):
			self.inputs = [ InputByte()
					for _ in range(self.specs.getNrInputs()) ]
		if force or self.specs.getNrOutputs() != len(self.outputs):
			self.outputs = [ OutputByte()
					 for _ in range(self.specs.getNrOutputs()) ]
		CallStackElem.resetCache()

	def reset(self):
		self.dbs = {
			# User DBs
		}
		self.obs = {
			# OBs
		}
		self.fcs = {
			# User FCs
		}
		self.fbs = {
			# User FBs
		}
		self.reallocate(force=True)
		self.ar1 = Adressregister()
		self.ar2 = Adressregister()
		self.globDB = None
		self.callStack = [ ]
		self.setMcrActive(False)
		self.mcrStack = [ ]

		self.relativeJump = 1

		# Stats
		self.cycleCount = 0
		self.insnCount = 0
		self.insnCountMod = self.simplePRNG.getBits(7) + 1
		self.runtimeSec = 0.0
		self.insnPerSecond = 0.0
		self.avgInsnPerCycle = 0.0
		self.cycleStartTime = 0.0
		self.maxCycleTime = 0.0
		self.avgCycleTime = 0.0

		self.updateTimestamp()

	def setCycleExitCallback(self, cb, data=None):
		if not cb:
			cb = lambda data: None
		self.cbCycleExit = cb
		self.cbCycleExitData = data

	def setBlockExitCallback(self, cb, data=None):
		if not cb:
			cb = lambda data: None
		self.cbBlockExit = cb
		self.cbBlockExitData = data

	def setPostInsnCallback(self, cb, data=None):
		if not cb:
			cb = lambda data: None
		self.cbPostInsn = cb
		self.cbPostInsnData = data

	def setDirectPeripheralCallback(self, cb, data=None):
		if not cb:
			cb = lambda data, operator: None
		self.cbDirectPeripheral = cb
		self.cbDirectPeripheralData = data

	@property
	def is4accu(self):
		return self.accu4 is not None

	# Get the active status word
	@property
	def status(self):
		return self.callStack[-1].status

	# Get the active parenthesis stack
	@property
	def parenStack(self):
		return self.callStack[-1].parenStack

	def __runTimeCheck(self):
		if self.now - self.cycleStartTime > self.cycleTimeLimit:
			raise AwlSimError("Cycle time exceed %.3f seconds" %\
					  self.cycleTimeLimit)

	# Run one cycle of the user program
	def runCycle(self):
		self.__startCycleTimeMeasurement()
		# Initialize CPU state
		self.callStack = [ CallStackElem(self, self.obs[1], None) ]
		# Run the user program cycle
		while self.callStack:
			cse = self.callStack[-1]
			while cse.ip < len(cse.insns):
				insn = cse.insns[cse.ip]
				self.relativeJump = 1
				insn.run()
				self.cbPostInsn(self.cbPostInsnData)
				cse.ip += self.relativeJump
				cse = self.callStack[-1]
				self.insnCount += 1
				if self.insnCount % self.insnCountMod == 0:
					self.updateTimestamp()
					self.__runTimeCheck()
					self.insnCountMod = self.simplePRNG.getBits(7) + 1
			self.cbBlockExit(self.cbBlockExitData)
			self.callStack.pop().destroy()
		self.cbCycleExit(self.cbCycleExitData)
		self.cycleCount += 1
		self.__endCycleTimeMeasurement()

	def inCycle(self):
		# Return true, if we are in runCycle().
		return bool(self.callStack)

	def __startCycleTimeMeasurement(self):
		self.updateTimestamp()
		self.cycleStartTime = self.now

	def __endCycleTimeMeasurement(self):
		self.updateTimestamp()
		elapsedTime = self.now - self.cycleStartTime
		self.runtimeSec += elapsedTime
		if self.cycleCount >= 50:
			self.runtimeSec = max(self.runtimeSec, 0.00001)
			self.insnPerSecond = self.insnCount / self.runtimeSec
			self.avgInsnPerCycle = self.insnCount / self.cycleCount
			self.cycleCount, self.insnCount, self.runtimeSec =\
				0, 0, 0.0
		self.maxCycleTime = max(self.maxCycleTime, elapsedTime)
		self.avgCycleTime = (self.avgCycleTime + elapsedTime) / 2

	def getCurrentIP(self):
		try:
			return self.callStack[-1].ip
		except IndexError as e:
			return None

	def getCurrentInsn(self):
		try:
			cse = self.callStack[-1]
			return cse.insns[cse.ip]
		except IndexError as e:
			return None

	def labelIdxToRelJump(self, labelIndex):
		cse = self.callStack[-1]
		label = cse.labels[labelIndex]
		referencedInsn = label.getInsn()
		referencedIp = referencedInsn.getIP()
		assert(referencedIp < len(cse.insns))
		return referencedIp - cse.ip

	def jumpToLabel(self, labelIndex):
		self.relativeJump = self.labelIdxToRelJump(labelIndex)

	def jumpRelative(self, insnOffset):
		self.relativeJump = insnOffset

	def __call_FC(self, blockOper, dbOper):
		if dbOper:
			raise AwlSimError("FC call must not "
				"have DB operand")
		try:
			fc = self.fcs[blockOper.offset]
		except KeyError as e:
			raise AwlSimError("Called FC not found")
		return CallStackElem(self, fc, self.callStack[-1].db)

	def __call_FB(self, blockOper, dbOper):
		if not dbOper or dbOper.type != AwlOperator.BLKREF_DB:
			raise AwlSimError("FB call must have "
				"DB operand")
		try:
			fb = self.fbs[blockOper.offset]
		except KeyError as e:
			raise AwlSimError("Called FB not found")
		try:
			db = self.dbs[dbOper.offset]
		except KeyError as e:
			raise AwlSimError("DB used in FB call not found")
		return CallStackElem(self, fb, db)

	def __call_SFC(self, blockOper, dbOper):
		#TODO
		raise AwlSimError("SFC calls not implemented, yet")

	def __call_SFB(self, blockOper, dbOper):
		#TODO
		raise AwlSimError("SFB calls not implemented, yet")

	__callHelpers = {
		AwlOperator.BLKREF_FC	: __call_FC,
		AwlOperator.BLKREF_FB	: __call_FB,
		AwlOperator.BLKREF_SFC	: __call_SFC,
		AwlOperator.BLKREF_SFB	: __call_SFB,
	}

	def run_CALL(self, blockOper, dbOper=None):
		try:
			callHelper = self.__callHelpers[blockOper.type]
		except KeyError:
			raise AwlSimError("Invalid CALL operand")
		self.callStack.append(callHelper(self, blockOper, dbOper))

	def run_BE(self):
		s = self.status
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
		# Jump beyond end of block
		cse = self.callStack[-1]
		self.relativeJump = len(cse.insns) - cse.ip

	def run_AUF(self, dbOper):
		try:
			db = self.dbs[dbOper.offset]
		except KeyError:
			raise AwlSimError("Datablock %i does not exist" %\
					  dbOper.offset)
		if dbOper.type == AwlOperator.BLKREF_DB:
			self.globDB = db
		elif dbOper.type == AwlOperator.BLKREF_DI:
			self.callStack[-1].db = db
		else:
			raise AwlSimError("Invalid DB reference in AUF")

	def run_TDB(self):
		cse = self.callStack[-1]
		# Swap global and instance DB
		cse.db, self.globDB = self.globDB, cse.db

	def updateTimestamp(self):
		self.now = time.time()

	def getStatusWord(self):
		return self.status

	def getAccu(self, index):
		if index < 1 or index > self.specs.getNrAccus():
			raise AwlSimError("Invalid ACCU offset")
		return (self.accu1, self.accu2,
			self.accu3, self.accu4)[index - 1]

	def getAR(self, index):
		if index < 1 or index > 2:
			raise AwlSimError("Invalid AR offset")
		return (self.ar1, self.ar2)[index - 1]

	def getTimer(self, index):
		try:
			return self.timers[index]
		except IndexError as e:
			raise AwlSimError("Fetched invalid timer %d" % index)

	def getCounter(self, index):
		try:
			return self.counters[index]
		except IndexError as e:
			raise AwlSimError("Fetched invalid counter %d" % index)

	def getSpecs(self):
		return self.specs

	def setMcrActive(self, active):
		self.mcrActive = active

	def mcrIsOn(self):
		if not self.mcrActive:
			return True
		if all(self.mcrStack):
			return True
		return False

	def mcrStackAppend(self, statusWord):
		self.mcrStack.append(McrStackElem(statusWord))
		if len(self.mcrStack) > 8:
			raise AwlSimError("MCR stack overflow")

	def mcrStackPop(self):
		try:
			return self.mcrStack.pop()
		except IndexError:
			raise AwlSimError("MCR stack underflow")

	def parenStackAppend(self, insnType, statusWord):
		self.parenStack.append(ParenStackElem(insnType, statusWord))
		if len(self.parenStack) > 7:
			raise AwlSimError("Parenthesis stack overflow")

	def fetch(self, operator):
		try:
			fetchMethod = self.fetchTypeMethods[operator.type]
		except KeyError:
			raise AwlSimError("Invalid fetch request")
		return fetchMethod(self, operator)

	def fetchIMM(self, operator):
		return operator.immediate

	def fetchIMM_REAL(self, operator):
		return operator.immediate

	def fetchIMM_S5T(self, operator):
		return operator.immediate

	def fetchSTW(self, operator):
		if operator.width == 1:
			return self.status.getByBitNumber(operator.bitOffset)
		elif operator.width == 16:
			return self.status.getWord()
		else:
			assert(0)

	def fetchSTW_Z(self, operator):
		return (~self.status.A0 & ~self.status.A1) & 1

	def fetchSTW_NZ(self, operator):
		return self.status.A0 | self.status.A1

	def fetchSTW_POS(self, operator):
		return (~self.status.A0 & self.status.A1) & 1

	def fetchSTW_NEG(self, operator):
		return (self.status.A0 & ~self.status.A1) & 1

	def fetchSTW_POSZ(self, operator):
		return ~self.status.A0 & 1

	def fetchSTW_NEGZ(self, operator):
		return ~self.status.A1 & 1

	def fetchSTW_UO(self, operator):
		return self.status.A0 & self.status.A1

	def fetchE(self, operator):
		return AwlOperator.fetchFromByteArray(self.inputs, operator)

	def fetchA(self, operator):
		return AwlOperator.fetchFromByteArray(self.outputs, operator)

	def fetchM(self, operator):
		return AwlOperator.fetchFromByteArray(self.flags, operator)

	def fetchL(self, operator):
		return AwlOperator.fetchFromByteArray(self.callStack[-1].localdata,
						      operator)

	def fetchDB(self, operator):
		if not self.globDB:
			raise AwlSimError("Fetch from global DB, "
				"but no DB is opened")
		return self.globDB.fetch(operator)

	def fetchDI(self, operator):
		cse = self.callStack[-1]
		if not cse.db:
			raise AwlSimError("Fetch from instance DI, "
				"but no DI is opened")
		return cse.db.fetch(operator)

	def fetchPE(self, operator):
		self.cbDirectPeripheral(self.cbDirectPeripheralData,
					operator)
		return AwlOperator.fetchFromByteArray(self.inputs, operator)

	def fetchT(self, operator):
		timer = self.getTimer(operator.offset)
		if operator.insn.type == AwlInsn.TYPE_L:
			return timer.getTimevalBin()
		elif operator.insn.type == AwlInsn.TYPE_LC:
			return timer.getTimevalS5T()
		return timer.get()

	def fetchZ(self, operator):
		counter = self.getCounter(operator.offset)
		if operator.insn.type == AwlInsn.TYPE_L:
			return counter.getValueBin()
		elif operator.insn.type == AwlInsn.TYPE_LC:
			return counter.getValueBCD()
		return counter.get()

	def fetchVirtACCU(self, operator):
		return self.getAccu(operator.offset).get()

	def fetchVirtAR(self, operator):
		return self.getAR(operator.offset).get()

	fetchTypeMethods = {
		AwlOperator.IMM			: fetchIMM,
		AwlOperator.IMM_REAL		: fetchIMM_REAL,
		AwlOperator.IMM_S5T		: fetchIMM_S5T,
		AwlOperator.MEM_E		: fetchE,
		AwlOperator.MEM_A		: fetchA,
		AwlOperator.MEM_M		: fetchM,
		AwlOperator.MEM_L		: fetchL,
		AwlOperator.MEM_DB		: fetchDB,
		AwlOperator.MEM_DI		: fetchDI,
		AwlOperator.MEM_T		: fetchT,
		AwlOperator.MEM_Z		: fetchZ,
		AwlOperator.MEM_PE		: fetchPE,
		AwlOperator.MEM_STW		: fetchSTW,
		AwlOperator.MEM_STW_Z		: fetchSTW_Z,
		AwlOperator.MEM_STW_NZ		: fetchSTW_NZ,
		AwlOperator.MEM_STW_POS		: fetchSTW_POS,
		AwlOperator.MEM_STW_NEG		: fetchSTW_NEG,
		AwlOperator.MEM_STW_POSZ	: fetchSTW_POSZ,
		AwlOperator.MEM_STW_NEGZ	: fetchSTW_NEGZ,
		AwlOperator.MEM_STW_UO		: fetchSTW_UO,
		AwlOperator.VIRT_ACCU		: fetchVirtACCU,
		AwlOperator.VIRT_AR		: fetchVirtAR,
	}

	def store(self, operator, value):
		try:
			storeMethod = self.storeTypeMethods[operator.type]
		except KeyError:
			raise AwlSimError("Invalid store request")
		storeMethod(self, operator, value)

	def storeE(self, operator, value):
		if self.inCycle():
			raise AwlSimError("Can't store to E")
		AwlOperator.storeToByteArray(self.inputs, operator, value)

	def storeA(self, operator, value):
		AwlOperator.storeToByteArray(self.outputs, operator, value)

	def storeM(self, operator, value):
		AwlOperator.storeToByteArray(self.flags, operator, value)

	def storeL(self, operator, value):
		AwlOperator.storeToByteArray(self.callStack[-1].localdata,
					     operator, value)

	def storeDB(self, operator, value):
		if not self.globDB:
			raise AwlSimError("Store to global DB, "
				"but no DB is opened")
		self.globDB.store(operator, value)

	def storeDI(self, operator, value):
		cse = self.callStack[-1]
		if not cse.db:
			raise AwlSimError("Store to instance DI, "
				"but no DI is opened")
		cse.db.store(operator, value)

	def storePA(self, operator, value):
		AwlOperator.storeToByteArray(self.outputs, operator, value)
		self.cbDirectPeripheral(self.cbDirectPeripheralData,
					operator)

	def storeSTW(self, operator, value):
		if operator.width == 1:
			raise AwlSimError("Cannot store to individual STW bits")
		elif operator.width == 16:
			self.status.setWord(value)
		else:
			assert(0)

	storeTypeMethods = {
		AwlOperator.MEM_E		: storeE,
		AwlOperator.MEM_A		: storeA,
		AwlOperator.MEM_M		: storeM,
		AwlOperator.MEM_L		: storeL,
		AwlOperator.MEM_DB		: storeDB,
		AwlOperator.MEM_DI		: storeDI,
		AwlOperator.MEM_PA		: storePA,
		AwlOperator.MEM_STW		: storeSTW,
	}

	def __dumpMem(self, prefix, memArray, maxLen):
		ret, line, first, count, i = [], [], True, 0, 0
		while i < maxLen:
			line.append(memArray[i].toHex())
			count += 1
			if count >= 16:
				if not first:
					prefix = ' ' * len(prefix)
				first = False
				ret.append(prefix + ' '.join(line))
				line, count = [], 0
			i += 1
		assert(count == 0)
		return '\n'.join(ret)

	def __repr__(self):
		if not self.callStack:
			return ""
		ret = [ "S7-CPU dump:" ]
		ret.append(" status:  " + str(self.status))
		if self.is4accu:
			accus = [ accu.toHex()
				  for accu in (self.accu1, self.accu2,
				  	       self.accu3, self.accu4) ]
		else:
			accus = [ accu.toHex()
				  for accu in (self.accu1, self.accu2) ]
		ret.append("   ACCU:  " + "  ".join(accus))
		ret.append("     AR:  " + self.ar1.toHex() + "  " +\
					  self.ar2.toHex())
		ret.append(self.__dumpMem("      M:  ",
					  self.flags,
					  min(64, self.specs.getNrFlags())))
		ret.append(self.__dumpMem("    PAE:  ",
					  self.inputs,
					  min(64, self.specs.getNrInputs())))
		ret.append(self.__dumpMem("    PAA:  ",
					  self.outputs,
					  min(64, self.specs.getNrOutputs())))
		pstack = str(self.parenStack) if self.parenStack else "Empty"
		ret.append(" PStack:  " + pstack)
		ret.append(" GlobDB:  %s" % str(self.globDB))
		if self.callStack:
			elems = [ str(cse) for cse in self.callStack ]
			elems = " => ".join(elems)
			ret.append(" CStack:  depth:%d  stack: %s" %\
				   (len(self.callStack), elems))
			cse = self.callStack[-1]
			ret.append(self.__dumpMem("      L:  ",
						  cse.localdata,
						  min(16, self.specs.getNrLocalbytes())))
			ret.append(" InstDB:  %s" % str(cse.db))
		else:
			ret.append(" CStack:  Empty")
		ret.append("  insn.:  IP:%s    %s" %\
			   (str(self.getCurrentIP()),
			    str(self.getCurrentInsn())))
		ret.append("  speed:  %d insn/s  %.01f insn/cy  "
			   "ctAvg:%.04fs  "
			   "ctMax:%.04fs" %\
			   (int(round(self.insnPerSecond)),
			    self.avgInsnPerCycle,
			    self.avgCycleTime,
			    self.maxCycleTime))
		return '\n'.join(ret)
