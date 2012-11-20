# -*- coding: utf-8 -*-
#
# AWL simulator
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import sys
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


VERSION_MAJOR = 0
VERSION_MINOR = 2


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

class ObjectCache(object):
	def __init__(self, createCallback, callbackData=None):
		self.__createCallback = createCallback
		self.__callbackData = callbackData
		self.__cache = []

	def get(self):
		try:
			return self.__cache[-1]
		except IndexError as e:
			return self.__createCallback(self.__callbackData)

	def put(self, obj):
		self.__cache.append(obj)

class CallStackElem(object):
	"Call stack element"

	localdataCache = ObjectCache(lambda _:
		[ LocalByte() for _ in range(1024) ]
	)

	def __init__(self, cpu, block, db):
		self.cpu = cpu
		self.status = S7StatusWord()
		self.parenStack = []
		self.ip = 0
		self.localdata = self.localdataCache.get()
		self.insns = block.insns
		self.labels = block.labels
		self.db = db

	def destroy(self):
		self.localdataCache.put(self.localdata)

class S7CPU(object):
	"STEP 7 CPU"

	def __init__(self, sim):
		self.sim = sim
		self.setCycleTimeLimit(5.0)
		self.reset()
		self.__extendedInsnsEnabled = False

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

	def load(self, parseTree):
		# Translate instructions
		self.reset()
		for obNumber in parseTree.obs.keys():
			insns = self.__translateInsns(parseTree.obs[obNumber].insns)
			self.obs[obNumber] = OB(insns)
		for fbNumber in parseTree.fbs.keys():
			insns = self.__translateInsns(parseTree.fbs[fbNumber].insns)
			self.fbs[fbNumber] = FB(insns)
		for fcNumber in parseTree.fcs.keys():
			insns = self.__translateInsns(parseTree.fcs[fcNumber].insns)
			self.fcs[fcNumber] = FC(insns)
		for dbNumber in parseTree.dbs.keys():
			#TODO
			self.dbs[dbNumber] = DB()
		try:
			self.obs[1]
		except KeyError:
			raise AwlSimError("No OB1 defined")

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
		self.accu1 = Accu()
		self.accu2 = Accu()
		self.ar1 = Adressregister()
		self.ar2 = Adressregister()
		self.timers = [ Timer(self, i) for i in range(2048) ]
		self.counters = [ Counter(self, i) for i in range(2048) ]
		self.flags = [ FlagByte() for _ in range(8192) ]
		self.inputs = [ InputByte() for _ in range(8192) ]
		self.outputs = [ OutputByte() for _ in range(8192) ]
		self.globDB = None
		self.callStack = [ ]

		self.relativeJump = 1

		# Callbacks
		self.setBlockExitCallback(lambda x: None)
		self.setPostRunCallback(lambda x: None)

		# Stats
		self.cycleCount = 0
		self.insnCount = 0
		self.runtimeSec = 0.0
		self.insnPerSecond = 0.0
		self.avgInsnPerCycle = 0.0
		self.cycleStartTime = 0.0
		self.maxCycleTime = 0.0
		self.avgCycleTime = 0.0

		self.updateTimestamp()

	def setBlockExitCallback(self, cb, data=None):
		self.cbBlockExit = cb
		self.cbBlockExitData = data

	def setPostRunCallback(self, cb, data=None):
		self.cbPostRun = cb
		self.cbPostRunData = data

	# Get the active status word
	@property
	def status(self):
		return self.callStack[-1].status

	# Get the active parenthesis stack
	@property
	def parenStack(self):
		return self.callStack[-1].parenStack

	def __runTimeCheck(self):
		if self.now - self.cycleStartTime <= self.cycleTimeLimit:
			return
		raise AwlSimError("Cycle time exceed %.3f seconds" %\
				  self.cycleTimeLimit)

	# Run one cycle of the user program
	def runCycle(self):
		self.__startCycleTimeMeasurement()
		# Initialize CPU state
		self.callStack = [ CallStackElem(self, self.obs[1], DB()) ]
		# Run the user program cycle
		while self.callStack:
			cse = self.callStack[-1]
			while cse.ip < len(cse.insns):
				insn = cse.insns[cse.ip]
				self.relativeJump = 1
				insn.run()
				cse.ip += self.relativeJump
				cse = self.callStack[-1]
				self.cbPostRun(self.cbPostRunData)
				self.insnCount += 1
				if self.insnCount % 32 == 0:
					self.updateTimestamp()
					self.__runTimeCheck()
			self.cbBlockExit(self.cbBlockExitData)
			self.callStack.pop().destroy()
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
			return self.callStack[-1].insns[self.getCurrentIP()]
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

	def run_CALL(self, blockOper, dbOper=None):
		if blockOper.type == AwlOperator.BLKREF_FC:
			if dbOper:
				raise AwlSimError("FC call must not "
					"have DB operand")
			try:
				fc = self.fcs[blockOper.offset]
			except KeyError as e:
				raise AwlSimError("Called FC not found")
			cse = CallStackElem(self, fc, self.callStack[-1].db)
		elif blockOper.type == AwlOperator.BLKREF_FB:
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
			cse = CallStackElem(self, fb, db)
		elif blockOper.type == AwlOperand.BLKREF_SFC:
			#TODO
			raise AwlSimError("SFC calls not implemented, yet")
		elif blockOper.type == AwlOperand.BLKREF_SFB:
			#TODO
			raise AwlSimError("SFB calls not implemented, yet")
		else:
			raise AwlSimError("Invalid CALL operand")
		self.callStack.append(cse)

	def run_BE(self):
		s = self.status
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
		# Jump beyond end of block
		cse = self.callStack[-1]
		self.relativeJump = len(cse.insns) - cse.ip

	def updateTimestamp(self):
		self.now = time.time()

	def getStatusWord(self):
		return self.status

	def getAccu(self, index):
		if index < 1 or index > 2:
			raise AwlSimError("Invalid ACCU offset")
		return (self.accu1, self.accu2)[index - 1]

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

	def __fetchFromByteArray(self, array, operator):
		width, byteOff, bitOff =\
			operator.width, operator.offset, operator.bitOffset
		try:
			if width == 1:
				return array[byteOff].getBit(bitOff)
			elif width == 8:
				assert(bitOff == 0)
				return array[byteOff].get()
			elif width == 16:
				assert(bitOff == 0)
				return (array[byteOff].get() << 8) |\
				       array[byteOff + 1].get()
			elif width == 32:
				assert(bitOff == 0)
				return (array[byteOff].get() << 24) |\
				       (array[byteOff + 1].get() << 16) |\
				       (array[byteOff + 2].get() << 8) |\
				       array[byteOff + 3].get()
		except IndexError as e:
			raise AwlSimError("fetch: Offset out of range")
		assert(0)

	def fetchE(self, operator):
		return self.__fetchFromByteArray(self.inputs, operator)

	def fetchA(self, operator):
		return self.__fetchFromByteArray(self.outputs, operator)

	def fetchM(self, operator):
		return self.__fetchFromByteArray(self.flags, operator)

	def fetchL(self, operator):
		return self.__fetchFromByteArray(self.callStack[-1].localdata,
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

	def fetchPA(self, operator):
		pass#TODO
		return 0

	def fetchPE(self, operator):
		pass#TODO
		return 0

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
		AwlOperator.MEM_PA		: fetchPA,
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

	def __storeToByteArray(self, array, operator, value):
		width, byteOff, bitOff =\
			operator.width, operator.offset, operator.bitOffset
		try:
			if width == 1:
				array[byteOff].setBitValue(bitOff, value)
			elif width == 8:
				assert(bitOff == 0)
				array[byteOff].set(value)
			elif width == 16:
				assert(bitOff == 0)
				array[byteOff].set(value >> 8)
				array[byteOff + 1].set(value)
			elif width == 32:
				assert(bitOff == 0)
				array[byteOff].set(value >> 24)
				array[byteOff + 1].set(value >> 16)
				array[byteOff + 2].set(value >> 8)
				array[byteOff + 3].set(value)
			else:
				assert(0)
		except IndexError as e:
			raise AwlSimError("fetch: Offset out of range")

	def storeE(self, operator, value):
		if self.inCycle():
			raise AwlSimError("Can't store to E")
		self.__storeToByteArray(self.inputs, operator, value)

	def storeA(self, operator, value):
		self.__storeToByteArray(self.outputs, operator, value)

	def storeM(self, operator, value):
		self.__storeToByteArray(self.flags, operator, value)

	def storeL(self, operator, value):
		self.__storeToByteArray(self.callStack[-1].localdata,
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
		pass #TODO

	def storePE(self, operator, value):
		pass #TODO

	def storeSTW(self, operator, value):
		if operator.width == 1:
			raise AwlSimError("Cannot store to individual STW bits")
		elif operator.width == 16:
			pass #TODO
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
		AwlOperator.MEM_PE		: storePE,
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
		ret.append("   ACCU:  " + self.accu1.toHex() + "  " +\
					  self.accu2.toHex())
		ret.append("     AR:  " + self.ar1.toHex() + "  " +\
					  self.ar2.toHex())
		ret.append(self.__dumpMem("      M:  ",
					  self.flags, 64))
		ret.append(self.__dumpMem("    PAE:  ",
					  self.inputs, 64))
		ret.append(self.__dumpMem("    PAA:  ",
					  self.outputs, 64))
		ret.append(" PStack:  " + str(self.parenStack))
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

class AwlSim(object):
	def __init__(self):
		self.cpu = S7CPU(self)

	def load(self, parseTree):
		self.cpu.load(parseTree)

	def getCPU(self):
		return self.cpu

	def runCycle(self):
		ex = None
		try:
			self.cpu.runCycle()
		except AwlSimError as e:
			ex = e
		if ex:
			raise AwlSimError("ERROR at AWL line %d: %s\n\n%s" %\
				(self.cpu.getCurrentInsn().getLineNr(),
				 str(ex), str(self.cpu)))

	def __repr__(self):
		return str(self.cpu)
