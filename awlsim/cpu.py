# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import time
import random

from awlsim.cpuspecs import *
from awlsim.parser import *
from awlsim.datatypes import *
from awlsim.instructions import *
from awlsim.operators import *
from awlsim.insntrans import *
from awlsim.optrans import *
from awlsim.blocks import *
from awlsim.datablocks import *
from awlsim.statusword import *
from awlsim.labels import *
from awlsim.timers import *
from awlsim.counters import *
from awlsim.callstack import *
from awlsim.util import *

from awlsim.system_sfc import *
from awlsim.system_sfb import *


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

class McrStackElem(object):
	"MCR stack element"

	def __init__(self, statusWord):
		self.VKE = statusWord.VKE

	def __bool__(self):
		return bool(self.VKE)

	__nonzero__ = __bool__

class S7CPU(object):
	"STEP 7 CPU"

	def __init__(self, sim):
		self.sim = sim
		self.specs = S7CPUSpecs(self)
		self.enableRNG(False)
		self.setCycleTimeLimit(5.0)
		self.setCycleExitCallback(None)
		self.setBlockExitCallback(None)
		self.setPostInsnCallback(None)
		self.setDirectPeripheralCallback(None)
		self.setScreenUpdateCallback(None)
		self.reset()
		self.enableExtendedInsns(False)

	def enableExtendedInsns(self, en=True):
		self.__extendedInsnsEnabled = en

	def extendedInsnsEnabled(self):
		return self.__extendedInsnsEnabled

	def setCycleTimeLimit(self, newLimit):
		self.cycleTimeLimit = float(newLimit)

	def enableRNG(self, enabled=True):
		self.__rngEnabled = enabled

	def getRandomInt(self, minval, maxval):
		if self.__rngEnabled:
			return random.randint(minval, maxval)
		return (maxval - minval) // 2 + minval

	def __detectMnemonics(self, parseTree):
		specs = self.getSpecs()
		if specs.getConfiguredMnemonics() != S7CPUSpecs.MNEMONICS_AUTO:
			return
		codeBlocks = list(parseTree.obs.values())
		codeBlocks.extend(parseTree.fbs.values())
		codeBlocks.extend(parseTree.fcs.values())
		counts = {
			S7CPUSpecs.MNEMONICS_EN		: 0,
			S7CPUSpecs.MNEMONICS_DE		: 0,
		}
		for block in codeBlocks:
			for rawInsn in block.insns:
				for mnemonics in (S7CPUSpecs.MNEMONICS_EN,
						  S7CPUSpecs.MNEMONICS_DE):
					ret = AwlInsnTranslator.name2type(rawInsn.getName(),
									  mnemonics)
					if ret is not None:
						counts[mnemonics] += 1
					try:
						optrans = AwlOpTranslator(None, mnemonics)
						optrans.translateFrom(rawInsn)
					except AwlSimError:
						pass
					else:
						counts[mnemonics] += 1
		if counts[S7CPUSpecs.MNEMONICS_EN] >= counts[S7CPUSpecs.MNEMONICS_DE]:
			specs.setDetectedMnemonics(S7CPUSpecs.MNEMONICS_EN)
		else:
			specs.setDetectedMnemonics(S7CPUSpecs.MNEMONICS_DE)

	def __translateInsn(self, rawInsn, ip):
		ex = None
		try:
			insn = AwlInsnTranslator.fromRawInsn(self, rawInsn)
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

	def __translateInterfaceField(self, rawVar):
		dtype = AwlDataType.makeByName(rawVar.typeTokens)
		if rawVar.valueTokens is None:
			initialValue = None
		else:
			initialValue = dtype.parseImmediate(rawVar.valueTokens)
		field = BlockInterface.Field(name = rawVar.name,
					     dataType = dtype,
					     initialValue = initialValue)
		return field

	def __translateCodeBlock(self, rawBlock, blockClass):
		insns = self.__translateInsns(rawBlock.insns)
		block = blockClass(insns, rawBlock.index)
		for rawVar in rawBlock.vars_in:
			block.interface.addField_IN(self.__translateInterfaceField(rawVar))
		for rawVar in rawBlock.vars_out:
			block.interface.addField_OUT(self.__translateInterfaceField(rawVar))
		if rawBlock.retTypeTokens:
			dtype = AwlDataType.makeByName(rawBlock.retTypeTokens)
			if dtype.type != AwlDataType.TYPE_VOID:
				field = BlockInterface.Field(name = "RET_VAL",
							     dataType = dtype)
				block.interface.addField_OUT(field)
		for rawVar in rawBlock.vars_inout:
			block.interface.addField_INOUT(self.__translateInterfaceField(rawVar))
		for rawVar in rawBlock.vars_static:
			block.interface.addField_STAT(self.__translateInterfaceField(rawVar))
		for rawVar in rawBlock.vars_temp:
			block.interface.addField_TEMP(self.__translateInterfaceField(rawVar))
		block.interface.buildDataStructure()
		return block

	def __translateGlobalDB(self, rawDB):
		db = DB(rawDB.index, None)
		# Create the data structure fields
		for f in rawDB.fields:
			if not f.typeTokens:
				raise AwlSimError(
					"DB %d assigns field '%s', "
					"but does not declare it." %\
					(rawDB.index, f.name))
			if f.valueTokens is None:
				raise AwlSimError(
					"DB %d declares field '%s', "
					"but does not initialize." %\
					(rawDB.index, f.name))
			dtype = AwlDataType.makeByName(f.typeTokens)
			db.struct.addFieldNaturallyAligned(f.name, dtype.width)
		# Allocate the data structure fields
		db.allocate()
		# Initialize the data structure fields
		for f in rawDB.fields:
			dtype = AwlDataType.makeByName(f.typeTokens)
			value = dtype.parseImmediate(f.valueTokens)
			db.structInstance.setFieldData(f.name, value)
		return db

	def __translateInstanceDB(self, rawDB):
		fbName, fbNumber = rawDB.fb
		try:
			fb = self.fbs[fbNumber]
		except KeyError:
			raise AwlSimError("Instance DB %d references FB %d, "
				"but FB %d does not exist." %\
				(rawDB.index, fbNumber, fbNumber))
		db = DB(rawDB.index, fb)
		interface = fb.interface
		# Sanity checks
		for f in rawDB.fields:
			if f.typeTokens:
				raise AwlSimError("DB %d is an "
					"instance DB, but it also "
					"declares a data structure." %\
					rawDB.index)
		# Allocate the data structure fields
		db.allocate()
		# Initialize the data structure fields
		for f in rawDB.fields:
			dtype = interface.getFieldByName(f.name).dataType
			value = dtype.parseImmediate(f.valueTokens)
			db.structInstance.setFieldData(f.name, value)
		return db

	def __translateDB(self, rawDB):
		if rawDB.index < 0:
			raise AwlSimError("DB number %d is invalid" % rawDB.index)
		if rawDB.isInstanceDB():
			return self.__translateInstanceDB(rawDB)
		return self.__translateGlobalDB(rawDB)

	def __allocateFCBounceDB(self, fc):
		dbNumber = -abs(fc.index) # Use negative FC number as bounce-DB number
		db = DB(dbNumber, fc)
		db.allocate()
		return db

	def __resolveNamedLocalSym(self, block, oper):
		# Translate local symbols (#abc)
		assert(oper.type == AwlOperator.NAMED_LOCAL)
		interfaceField = block.interface.getFieldByName(oper.value)
		if interfaceField.fieldType == interfaceField.FTYPE_IN or\
		   interfaceField.fieldType == interfaceField.FTYPE_OUT or\
		   interfaceField.fieldType == interfaceField.FTYPE_INOUT or\
		   interfaceField.fieldType == interfaceField.FTYPE_STAT:
			# Translate to interface-DB access
			structField = block.interface.struct.getField(oper.value)
			oper.setType(AwlOperator.INTERF_DB)
		elif interfaceField.fieldType == interfaceField.FTYPE_TEMP:
			# Translate to local-stack access
			structField = block.interface.tempStruct.getField(oper.value)
			oper.setType(AwlOperator.MEM_L)
		else:
			assert(0)
		oper.setWidth(structField.bitSize)
		oper.setOffset(structField.offset.byteOffset,
			       structField.offset.bitOffset)

	def __resolveSymbols_block(self, block):
		for insn in block.insns:
			for oper in insn.ops:
				if oper.type == AwlOperator.NAMED_LOCAL:
					self.__resolveNamedLocalSym(block, oper)

	def __resolveSymbols(self):
		for ob in self.obs.values():
			self.__resolveSymbols_block(ob)
		for fb in self.fbs.values():
			self.__resolveSymbols_block(fb)
		for fc in self.fcs.values():
			self.__resolveSymbols_block(fc)

	def load(self, parseTree):
		# Translate the AWL tree
		self.__detectMnemonics(parseTree)
		self.reset()
		for obNumber in parseTree.obs.keys():
			ob = self.__translateCodeBlock(parseTree.obs[obNumber], OB)
			self.obs[obNumber] = ob
		for fbNumber in parseTree.fbs.keys():
			fb = self.__translateCodeBlock(parseTree.fbs[fbNumber], FB)
			self.fbs[fbNumber] = fb
		for fcNumber in parseTree.fcs.keys():
			fc = self.__translateCodeBlock(parseTree.fcs[fcNumber], FC)
			self.fcs[fcNumber] = fc
			bounceDB = self.__allocateFCBounceDB(fc)
			self.dbs[bounceDB.index] = bounceDB
		for dbNumber in parseTree.dbs.keys():
			db = self.__translateDB(parseTree.dbs[dbNumber])
			self.dbs[dbNumber] = db
		self.__resolveSymbols()
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
		self.callStackTop = None
		self.setMcrActive(False)
		self.mcrStack = [ ]

		self.relativeJump = 1

		# Stats
		self.cycleCount = 0
		self.insnCount = 0
		self.insnCountMod = self.getRandomInt(0, 127) + 1
		self.runtimeSec = 0.0
		self.insnPerSecond = 0.0
		self.avgInsnPerCycle = 0.0
		self.cycleStartTime = 0.0
		self.maxCycleTime = 0.0
		self.avgCycleTime = 0.0

		self.updateTimestamp()

	def setCycleExitCallback(self, cb, data=None):
		self.cbCycleExit = cb
		self.cbCycleExitData = data

	def setBlockExitCallback(self, cb, data=None):
		self.cbBlockExit = cb
		self.cbBlockExitData = data

	def setPostInsnCallback(self, cb, data=None):
		self.cbPostInsn = cb
		self.cbPostInsnData = data

	def setDirectPeripheralCallback(self, cb, data=None):
		self.cbDirectPeripheral = cb
		self.cbDirectPeripheralData = data

	def setScreenUpdateCallback(self, cb, data=None):
		self.cbScreenUpdate = cb
		self.cbScreenUpdateData = data

	def requestScreenUpdate(self):
		if self.cbScreenUpdate:
			self.cbScreenUpdate(self.cbScreenUpdateData)

	@property
	def is4accu(self):
		return self.accu4 is not None

	# Get the active parenthesis stack
	@property
	def parenStack(self):
		return self.callStackTop.parenStack

	def __runTimeCheck(self):
		if self.now - self.cycleStartTime > self.cycleTimeLimit:
			raise AwlSimError("Cycle time exceed %.3f seconds" %\
					  self.cycleTimeLimit)

	def __runBlock(self, block):
		self.__startCycleTimeMeasurement()
		# Initialize CPU state
		self.callStack = [ CallStackElem(self, block) ]
		# Run the user program cycle
		while self.callStack:
			cse = self.callStackTop = self.callStack[-1]
			while cse.ip < len(cse.insns):
				insn, self.relativeJump = cse.insns[cse.ip], 1
				insn.run()
				if self.cbPostInsn:
					self.cbPostInsn(self.cbPostInsnData)
				cse.ip += self.relativeJump
				cse, self.insnCount = self.callStackTop, self.insnCount + 1
				if self.insnCount % self.insnCountMod == 0:
					self.updateTimestamp()
					self.__runTimeCheck()
					self.insnCountMod = self.getRandomInt(0, 127) + 1
			cse.handleOutParameters()
			if self.cbBlockExit:
				self.cbBlockExit(self.cbBlockExitData)
			self.callStack.pop().destroy()
		if self.cbCycleExit:
			self.cbCycleExit(self.cbCycleExitData)
		self.cycleCount += 1
		self.__endCycleTimeMeasurement()

	# Run startup code
	def startup(self):
		self.updateTimestamp()
		self.cpuStartupTime = self.now

		# Run startup OB
		for obNumber in (100, 101, 102):
			ob = self.obs.get(obNumber)
			if ob is not None:
				self.__runBlock(ob)
				break

	# Run one cycle of the user program
	def runCycle(self):
		self.__runBlock(self.obs[1])

	def inCycle(self):
		# Return true, if we are in runCycle().
		#FIXME
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
			return self.callStackTop.ip
		except IndexError as e:
			return None

	def getCurrentInsn(self):
		try:
			cse = self.callStackTop
			return cse.insns[cse.ip]
		except IndexError as e:
			return None

	def labelIdxToRelJump(self, labelIndex):
		cse = self.callStackTop
		label = cse.labels[labelIndex]
		referencedInsn = label.getInsn()
		referencedIp = referencedInsn.getIP()
		assert(referencedIp < len(cse.insns))
		return referencedIp - cse.ip

	def jumpToLabel(self, labelIndex):
		self.relativeJump = self.labelIdxToRelJump(labelIndex)

	def jumpRelative(self, insnOffset):
		self.relativeJump = insnOffset

	def __call_FC(self, blockOper, dbOper, parameters):
		if dbOper:
			raise AwlSimError("FC call must not "
				"have DB operand")
		try:
			fc = self.fcs[blockOper.value.byteOffset]
		except KeyError as e:
			raise AwlSimError("Called FC not found")
		bounceDB = self.dbs[-abs(fc.index)] # Get bounce-DB
		if fc.interface.interfaceFieldCount != len(parameters):
			raise AwlSimError("Call interface mismatch. "
				"Passed %d parameters, but expected %d.\n"
				"====  The block interface is:\n%s\n====" %\
				(len(parameters), fc.interface.interfaceFieldCount,
				 str(fc.interface)))
		return CallStackElem(self, fc, self.callStackTop.instanceDB,
				     bounceDB, parameters)

	def __call_FB(self, blockOper, dbOper, parameters):
		if not dbOper or dbOper.type != AwlOperator.BLKREF_DB:
			raise AwlSimError("FB call must have "
				"DB operand")
		try:
			fb = self.fbs[blockOper.value.byteOffset]
		except KeyError as e:
			raise AwlSimError("Called FB not found")
		try:
			db = self.dbs[dbOper.value.byteOffset]
		except KeyError as e:
			raise AwlSimError("DB used in FB call not found")
		if not db.isInstanceDB():
			raise AwlSimError("DB %d is not an instance DB" % dbOper.value.byteOffset)
		if db.codeBlock.index != fb.index:
			raise AwlSimError("DB %d is not an instance DB for FB %d" %\
				(dbOper.value.byteOffset, blockOper.value.byteOffset))
		return CallStackElem(self, fb, db, db, parameters)

	def __call_SFC(self, blockOper, dbOper):
		if dbOper:
			raise AwlSimError("SFC call must not "
				"have DB operand")
		try:
			sfc = SFC_table[blockOper.value.byteOffset]
		except KeyError as e:
			raise AwlSimError("SFC %d not implemented, yet" %\
					  blockOper.value.byteOffset)
		sfc.run(self)

	def __call_SFB(self, blockOper, dbOper):
		if not dbOper or dbOper.type != AwlOperator.BLKREF_DB:
			raise AwlSimError("SFB call must have "
				"DB operand")
		try:
			sfb = SFB_table[blockOper.value.byteOffset]
		except KeyError as e:
			raise AwlSimError("SFB %d not implemented, yet" %\
					  blockOper.value.byteOffset)
		sfb.run(self, dbOper)

	__callHelpers = {
		AwlOperator.BLKREF_FC	: __call_FC,
		AwlOperator.BLKREF_FB	: __call_FB,
		AwlOperator.BLKREF_SFC	: __call_SFC,
		AwlOperator.BLKREF_SFB	: __call_SFB,
	}

	def run_CALL(self, blockOper, dbOper=None, parameters=()):
		try:
			callHelper = self.__callHelpers[blockOper.type]
		except KeyError:
			raise AwlSimError("Invalid CALL operand")
		newCse = callHelper(self, blockOper, dbOper, parameters)
		if newCse:
			self.callStack.append(newCse)
			self.callStackTop = newCse

	def run_BE(self):
		s = self.callStackTop.status
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
		# Jump beyond end of block
		cse = self.callStackTop
		self.relativeJump = len(cse.insns) - cse.ip

	def run_AUF(self, dbOper):
		try:
			db = self.dbs[dbOper.value.byteOffset]
		except KeyError:
			raise AwlSimError("Datablock %i does not exist" %\
					  dbOper.value.byteOffset)
		if dbOper.type == AwlOperator.BLKREF_DB:
			self.globDB = db
		elif dbOper.type == AwlOperator.BLKREF_DI:
			self.callStackTop.db = db
		else:
			raise AwlSimError("Invalid DB reference in AUF")

	def run_TDB(self):
		cse = self.callStackTop
		# Swap global and instance DB
		cse.instanceDB, self.globDB = self.globDB, cse.instanceDB

	def updateTimestamp(self):
		# self.now is a floating point count of seconds since the epoch.
		self.now = time.time()

	def getStatusWord(self):
		return self.callStackTop.status

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
		return operator.value

	def fetchIMM_REAL(self, operator):
		return operator.value

	def fetchIMM_S5T(self, operator):
		return operator.value

	def fetchIMM_PTR(self, operator):
		return operator.value.toPointerValue()

	def fetchSTW(self, operator):
		if operator.width == 1:
			return self.callStackTop.status.getByBitNumber(operator.value.bitOffset)
		elif operator.width == 16:
			return self.callStackTop.status.getWord()
		else:
			assert(0)

	def fetchSTW_Z(self, operator):
		return (~self.callStackTop.status.A0 & ~self.callStackTop.status.A1) & 1

	def fetchSTW_NZ(self, operator):
		return self.callStackTop.status.A0 | self.callStackTop.status.A1

	def fetchSTW_POS(self, operator):
		return (~self.callStackTop.status.A0 & self.callStackTop.status.A1) & 1

	def fetchSTW_NEG(self, operator):
		return (self.callStackTop.status.A0 & ~self.callStackTop.status.A1) & 1

	def fetchSTW_POSZ(self, operator):
		return ~self.callStackTop.status.A0 & 1

	def fetchSTW_NEGZ(self, operator):
		return ~self.callStackTop.status.A1 & 1

	def fetchSTW_UO(self, operator):
		return self.callStackTop.status.A0 & self.callStackTop.status.A1

	def fetchE(self, operator):
		return AwlOperator.fetchFromByteArray(self.inputs, operator)

	def fetchA(self, operator):
		return AwlOperator.fetchFromByteArray(self.outputs, operator)

	def fetchM(self, operator):
		return AwlOperator.fetchFromByteArray(self.flags, operator)

	def fetchL(self, operator):
		return AwlOperator.fetchFromByteArray(self.callStackTop.localdata,
						      operator)

	def fetchVL(self, operator):
		try:
			cse = self.callStack[-2]
		except IndexError:
			raise AwlSimError("Fetch of parent localstack, "
				"but no parent present.")
		return AwlOperator.fetchFromByteArray(cse.localdata, operator)

	def fetchDB(self, operator):
		if not self.globDB:
			raise AwlSimError("Fetch from global DB, "
				"but no DB is opened")
		return self.globDB.fetch(operator)

	def fetchDI(self, operator):
		cse = self.callStackTop
		if not cse.instanceDB:
			raise AwlSimError("Fetch from instance DI, "
				"but no DI is opened")
		return cse.instanceDB.fetch(operator)

	def fetchINTERF_DB(self, operator):
		cse = self.callStackTop
		if not cse.interfaceDB:
			raise AwlSimError("Fetch from block interface, but "
				"no interface is declared.")
		return cse.interfaceDB.fetch(operator)

	def fetchPE(self, operator):
		if self.cbDirectPeripheral:
			self.cbDirectPeripheral(self.cbDirectPeripheralData,
						operator)
		return AwlOperator.fetchFromByteArray(self.inputs, operator)

	def fetchT(self, operator):
		timer = self.getTimer(operator.value.byteOffset)
		if operator.insn.type == AwlInsn.TYPE_L:
			return timer.getTimevalBin()
		elif operator.insn.type == AwlInsn.TYPE_LC:
			return timer.getTimevalS5T()
		return timer.get()

	def fetchZ(self, operator):
		counter = self.getCounter(operator.value.byteOffset)
		if operator.insn.type == AwlInsn.TYPE_L:
			return counter.getValueBin()
		elif operator.insn.type == AwlInsn.TYPE_LC:
			return counter.getValueBCD()
		return counter.get()

	def fetchINDIRECT(self, operator):
		return self.fetch(operator.resolve(self, False))

	def fetchVirtACCU(self, operator):
		return self.getAccu(operator.value.byteOffset).get()

	def fetchVirtAR(self, operator):
		return self.getAR(operator.value.byteOffset).get()

	fetchTypeMethods = {
		AwlOperator.IMM			: fetchIMM,
		AwlOperator.IMM_REAL		: fetchIMM_REAL,
		AwlOperator.IMM_S5T		: fetchIMM_S5T,
		AwlOperator.IMM_PTR		: fetchIMM_PTR,
		AwlOperator.MEM_E		: fetchE,
		AwlOperator.MEM_A		: fetchA,
		AwlOperator.MEM_M		: fetchM,
		AwlOperator.MEM_L		: fetchL,
		AwlOperator.MEM_VL		: fetchVL,
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
		AwlOperator.INTERF_DB		: fetchINTERF_DB,
		AwlOperator.INDIRECT		: fetchINDIRECT,
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
		AwlOperator.storeToByteArray(self.callStackTop.localdata,
					     operator, value)

	def storeVL(self, operator, value):
		try:
			cse = self.callStack[-2]
		except IndexError:
			raise AwlSimError("Store to parent localstack, "
				"but no parent present.")
		AwlOperator.storeToByteArray(cse.localdata, operator, value)

	def storeDB(self, operator, value):
		if not self.globDB:
			raise AwlSimError("Store to global DB, "
				"but no DB is opened")
		self.globDB.store(operator, value)

	def storeDI(self, operator, value):
		cse = self.callStackTop
		if not cse.instanceDB:
			raise AwlSimError("Store to instance DI, "
				"but no DI is opened")
		cse.instanceDB.store(operator, value)

	def storeINTERF_DB(self, operator, value):
		cse = self.callStackTop
		if not cse.interfaceDB:
			raise AwlSimError("Store to block interface, but "
				"no interface is declared.")
		cse.interfaceDB.store(operator, value)

	def storePA(self, operator, value):
		AwlOperator.storeToByteArray(self.outputs, operator, value)
		if self.cbDirectPeripheral:
			self.cbDirectPeripheral(self.cbDirectPeripheralData,
						operator)

	def storeSTW(self, operator, value):
		if operator.width == 1:
			raise AwlSimError("Cannot store to individual STW bits")
		elif operator.width == 16:
			self.callStackTop.status.setWord(value)
		else:
			assert(0)

	def storeINDIRECT(self, operator, value):
		self.store(operator.resolve(self, True), value)

	storeTypeMethods = {
		AwlOperator.MEM_E		: storeE,
		AwlOperator.MEM_A		: storeA,
		AwlOperator.MEM_M		: storeM,
		AwlOperator.MEM_L		: storeL,
		AwlOperator.MEM_VL		: storeVL,
		AwlOperator.MEM_DB		: storeDB,
		AwlOperator.MEM_DI		: storeDI,
		AwlOperator.MEM_PA		: storePA,
		AwlOperator.MEM_STW		: storeSTW,
		AwlOperator.INTERF_DB		: storeINTERF_DB,
		AwlOperator.INDIRECT		: storeINDIRECT,
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
		ret.append(" status:  " + str(self.callStackTop.status))
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
			ret.append(" InstDB:  %s" % str(cse.instanceDB))
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
