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
VERSION_MINOR = 1


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

	def __init__(self, cpu, block):
		self.cpu = cpu
		self.status = S7StatusWord()
		self.parenStack = []
		self.localdata = self.localdataCache.get()
		self.insns = block.insns
		self.labels = block.labels
		self.db = block.db

	def destroy(self):
		self.localdataCache.put(self.localdata)

class S7CPU(object):
	"STEP 7 CPU"

	def __init__(self, sim):
		self.sim = sim
		self.setCycleTimeLimit(5.0)
		self.reset()

	def setCycleTimeLimit(self, newLimit):
		self.cycleTimeLimit = float(newLimit)

	def load(self, ob1_insns):
		self.reset()
		for insn in ob1_insns:
			insn.setCpu(self)
		self.obs[1] = OB(ob1_insns, DB())

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
		self.callStack = [ ]
		self.__callStackInit(Block(None, None))

		self.ip = None
		self.relativeJump = 1

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

	@property
	def status(self):
		return self.callStack[-1].status

	@property
	def parenStack(self):
		return self.callStack[-1].parenStack

	def __runTimeCheck(self):
		if self.now - self.cycleStartTime <= self.cycleTimeLimit:
			return
		raise AwlSimError("Cycle time exceed %.3f seconds" %\
				  self.cycleTimeLimit)

	def __callStackInit(self, block):
		for cse in self.callStack:
			cse.destroy()
		self.callStack = [ CallStackElem(self, block) ]

	# Run one cycle of the user program
	def runCycle(self):
		self.__startCycleTimeMeasurement()
		# Initialize CPU state
		self.__callStackInit(self.obs[1])
		self.ip = 0
		# Run the user program cycle
		while self.ip < len(self.callStack[-1].insns):
			insn = self.callStack[-1].insns[self.ip]
			self.relativeJump = 1
			insn.run()
			self.insnCount += 1
			if self.insnCount % 32 == 0:
				self.updateTimestamp()
				self.__runTimeCheck()
			self.ip += self.relativeJump
		self.ip = None
		self.cycleCount += 1
		self.__endCycleTimeMeasurement()

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

	def getCurrentInsn(self):
		if self.ip is None or not self.callStack:
			return None
		return self.callStack[-1].insns[self.ip]

	def labelIdxToRelJump(self, labelIndex):
		label = self.callStack[-1].labels[labelIndex]
		referencedInsn = label.getInsn()
		referencedIp = referencedInsn.getIP()
		assert(referencedIp < len(self.callStack[-1].insns))
		return referencedIp - self.ip

	def jumpToLabel(self, labelIndex):
		self.relativeJump = self.labelIdxToRelJump(labelIndex)

	def jumpRelative(self, insnOffset):
		self.relativeJump = insnOffset

	def run_BE(self):
		s = self.status
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
		# Jump beyond end of block
		self.relativeJump = len(self.callStack[-1].insns) - self.ip

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
		fetchMethod = self.fetchTypeMethods[operator.type]
		return fetchMethod(self, operator)

	def fetchIMM(self, operator):
		return operator.immediate

	def fetchIMM_S5T(self, operator):
		return operator.immediate

	def fetchSTW(self, operator):
		return self.status.getByBitNumber(operator.bitOffset)

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

	def fetchD(self, operator):
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
		AwlOperator.IMM_S5T		: fetchIMM_S5T,
		AwlOperator.MEM_E		: fetchE,
		AwlOperator.MEM_A		: fetchA,
		AwlOperator.MEM_M		: fetchM,
		AwlOperator.MEM_L		: fetchL,
		AwlOperator.MEM_D		: fetchD,
		AwlOperator.MEM_T		: fetchT,
		AwlOperator.MEM_Z		: fetchZ,
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
		storeMethod = self.storeTypeMethods[operator.type]
		storeMethod(self, operator, value)

	def __storeInvalid(self, operator, value):
		raise AwlSimError("Invalid store request")

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
		#TODO this is only valid from outside of the cycle
		self.__storeToByteArray(self.inputs, operator, value)

	def storeA(self, operator, value):
		self.__storeToByteArray(self.outputs, operator, value)

	def storeM(self, operator, value):
		self.__storeToByteArray(self.flags, operator, value)

	def storeL(self, operator, value):
		self.__storeToByteArray(self.callStack[-1].localdata,
					operator, value)

	def storeD(self, operator, value):
		pass #TODO

	storeTypeMethods = {
		AwlOperator.IMM			: __storeInvalid,
		AwlOperator.IMM_S5T		: __storeInvalid,
		AwlOperator.MEM_E		: storeE,
		AwlOperator.MEM_A		: storeA,
		AwlOperator.MEM_M		: storeM,
		AwlOperator.MEM_L		: storeL,
		AwlOperator.MEM_D		: storeD,
		AwlOperator.MEM_T		: __storeInvalid,
		AwlOperator.MEM_Z		: __storeInvalid,
		AwlOperator.MEM_STW		: __storeInvalid,
		AwlOperator.MEM_STW_Z		: __storeInvalid,
		AwlOperator.MEM_STW_NZ		: __storeInvalid,
		AwlOperator.MEM_STW_POS		: __storeInvalid,
		AwlOperator.MEM_STW_NEG		: __storeInvalid,
		AwlOperator.MEM_STW_POSZ	: __storeInvalid,
		AwlOperator.MEM_STW_NEGZ	: __storeInvalid,
		AwlOperator.MEM_STW_UO		: __storeInvalid,
		AwlOperator.VIRT_ACCU		: __storeInvalid,
		AwlOperator.VIRT_AR		: __storeInvalid,
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
			   (str(self.ip),
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

	def load(self, ob1_rawInsns):
		# Translate instructions
		insns = []
		for i, rawInsn in enumerate(ob1_rawInsns):
			ex = None
			try:
				insn = AwlInsnTranslator.fromRawInsn(rawInsn)
				insn.setIP(i)
				insns.append(insn)
			except AwlSimError as e:
				ex = e
			if ex:
				raise AwlSimError("%s\nline %d: %s" %\
					(str(rawInsn), rawInsn.getLineNr(),
					 str(ex)))
		self.cpu.load(insns)

	def getCPU(self):
		return self.cpu

	def runCycle(self):
		ex = None
		try:
			self.cpu.runCycle()
		except AwlSimError as e:
			ex = e
		if ex:
			raise AwlSimError("%s\nline %d: %s" %\
				(str(self.cpu),
				 self.cpu.getCurrentInsn().getLineNr(),
				 str(ex)))

	def __repr__(self):
		return str(self.cpu)
