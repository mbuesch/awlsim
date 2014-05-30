# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
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

import time
import datetime
import random

from awlsim.core.cpuspecs import *
from awlsim.core.parser import *
from awlsim.core.symbolparser import *
from awlsim.core.datatypes import *
from awlsim.core.instructions.all_insns import *
from awlsim.core.systemblocks.system_sfb import *
from awlsim.core.systemblocks.system_sfc import *
from awlsim.core.operators import *
from awlsim.core.insntrans import *
from awlsim.core.optrans import *
from awlsim.core.blocks import *
from awlsim.core.datablocks import *
from awlsim.core.statusword import *
from awlsim.core.labels import *
from awlsim.core.timers import *
from awlsim.core.counters import *
from awlsim.core.callstack import *
from awlsim.core.obtemp import *
from awlsim.core.util import *


class ParenStackElem(object):
	"Parenthesis stack element"

	def __init__(self, cpu, insnType, statusWord):
		self.cpu = cpu
		self.insnType = insnType
		self.NER = statusWord.NER
		self.VKE = statusWord.VKE
		self.OR = statusWord.OR

	def __repr__(self):
		mnemonics = self.cpu.specs.getMnemonics()
		type2name = {
			S7CPUSpecs.MNEMONICS_EN : AwlInsn.type2name_english,
			S7CPUSpecs.MNEMONICS_DE : AwlInsn.type2name_german,
		}[mnemonics]
		return '(insn="%s" VKE=%s OR=%d)' %\
			(type2name[self.insnType],
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
		self.setCycleTimeLimit(5.0)
		self.setCycleExitCallback(None)
		self.setBlockExitCallback(None)
		self.setPostInsnCallback(None)
		self.setPeripheralReadCallback(None)
		self.setPeripheralWriteCallback(None)
		self.setScreenUpdateCallback(None)
		self.reset()
		self.enableExtendedInsns(False)
		self.enableObTempPresets(False)

	def enableObTempPresets(self, en=True):
		self.__obTempPresetsEnabled = bool(en)

	def obTempPresetsEnabled(self):
		return self.__obTempPresetsEnabled

	def enableExtendedInsns(self, en=True):
		self.__extendedInsnsEnabled = bool(en)

	def extendedInsnsEnabled(self):
		return self.__extendedInsnsEnabled

	def setCycleTimeLimit(self, newLimit):
		self.cycleTimeLimit = float(newLimit)

	def __detectMnemonics(self, parseTree):
		specs = self.getSpecs()
		if specs.getConfiguredMnemonics() != S7CPUSpecs.MNEMONICS_AUTO:
			return
		codeBlocks = list(parseTree.obs.values())
		codeBlocks.extend(parseTree.fbs.values())
		codeBlocks.extend(parseTree.fcs.values())
		errorCounts = {
			S7CPUSpecs.MNEMONICS_EN		: 0,
			S7CPUSpecs.MNEMONICS_DE		: 0,
		}
		detected = None
		for mnemonics in (S7CPUSpecs.MNEMONICS_EN,
				  S7CPUSpecs.MNEMONICS_DE):
			for block in codeBlocks:
				for rawInsn in block.insns:
					ret = AwlInsnTranslator.name2type(rawInsn.getName(),
									  mnemonics)
					if ret is None:
						errorCounts[mnemonics] += 1
					try:
						optrans = AwlOpTranslator(None, mnemonics)
						optrans.translateFromRawInsn(rawInsn)
					except AwlSimError:
						errorCounts[mnemonics] += 1
			if errorCounts[mnemonics] == 0:
				# No error. Use these mnemonics.
				detected = mnemonics
		if detected is None:
			# Select the mnemonics with the lower error count.
			if errorCounts[S7CPUSpecs.MNEMONICS_EN] <= errorCounts[S7CPUSpecs.MNEMONICS_DE]:
				detected = S7CPUSpecs.MNEMONICS_EN
			else:
				detected = S7CPUSpecs.MNEMONICS_DE
		if specs.getMnemonics() != S7CPUSpecs.MNEMONICS_AUTO:
			# Autodetected mnemonics were already set before
			if specs.getMnemonics() != detected:
				raise AwlSimError("Cannot mix multiple AWL files with "\
					"distinct mnemonics. This error may be caused by "\
					"incorrect autodetection. "\
					"Force mnemonics to EN or DE to avoid this error.")
		specs.setDetectedMnemonics(detected)

	def __translateInsn(self, rawInsn, ip):
		ex = None
		try:
			insn = AwlInsnTranslator.fromRawInsn(self, rawInsn)
			insn.setIP(ip)
		except AwlSimError as e:
			if e.getRawInsn() is None:
				e.setRawInsn(rawInsn)
			raise e
		return insn

	def __translateInsns(self, rawInsns):
		insns = []
		# Translate raw instructions to simulator instructions
		for ip, rawInsn in enumerate(rawInsns):
			insns.append(self.__translateInsn(rawInsn, ip))
		# If the last instruction is not BE or BEA, add an implicit BE
		if not insns or insns[-1].type not in (AwlInsn.TYPE_BE,
						       AwlInsn.TYPE_BEA):
			insns.append(AwlInsn_BE(cpu = self, rawInsn = None))
		return insns

	def __translateInterfaceField(self, rawVar):
		dtype = AwlDataType.makeByName(rawVar.typeTokens)
		if rawVar.valueTokens is None:
			initialValue = None
		else:
			initialValue = dtype.parseMatchingImmediate(rawVar.valueTokens)
		field = BlockInterfaceField(name = rawVar.name,
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
				field = BlockInterfaceField(name = "RET_VAL",
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
			db.struct.addFieldNaturallyAligned(f.name, dtype)
		# Allocate the data structure fields
		db.allocate()
		# Initialize the data structure fields
		for f in rawDB.fields:
			dtype = AwlDataType.makeByName(f.typeTokens)
			value = dtype.parseMatchingImmediate(f.valueTokens)
			db.structInstance.setFieldDataByName(f.name, value)
		return db

	def __translateInstanceDB(self, rawDB):
		fbStr = "SFB" if rawDB.fb.isSFB else "FB"
		try:
			if rawDB.fb.isSFB:
				fb = self.sfbs[rawDB.fb.fbNumber]
			else:
				fb = self.fbs[rawDB.fb.fbNumber]
		except KeyError:
			raise AwlSimError("Instance DB %d references %s %d, "
				"but %s %d does not exist." %\
				(rawDB.index,
				 fbStr, rawDB.fb.fbNumber,
				 fbStr, rawDB.fb.fbNumber))
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
			value = dtype.parseMatchingImmediate(f.valueTokens)
			db.structInstance.setFieldDataByName(f.name, value)
		return db

	def __translateDB(self, rawDB):
		if rawDB.index < 0:
			raise AwlSimError("DB number %d is invalid" % rawDB.index)
		if rawDB.isInstanceDB():
			return self.__translateInstanceDB(rawDB)
		return self.__translateGlobalDB(rawDB)

	# Translate classic symbols ("abc")
	def __resolveClassicSym(self, block, insn, oper):
		if oper.type == AwlOperator.SYMBOLIC:
			symbol = self.symbolTable.findByName(oper.value)
			if not symbol:
				raise AwlSimError("Symbol \"%s\" not found in "
					"symbol table." % oper.value,
					insn = insn)
			oper = symbol.operator
		return oper

	# Translate symbolic OB/FB/FC/DB block name
	def __resolveBlockName(self, blockTypeId, blockName):
		if isString(blockName):
			symbol = self.symbolTable.findByName(blockName)
			if not symbol:
				raise AwlSimError("Symbolic block name \"%s\" "
					"not found in symbol table." % blockName)
			if symbol.type.type != blockTypeId:
				raise AwlSimError("Symbolic block name \"%s\" "
					"has an invalid type." % blockName)
			return symbol.operator.value.byteOffset
		return blockName

	# Translate local symbols (#abc or P##abc)
	# If pointer is false, try to resolve #abc.
	# If pointer is true, try to resolve P##abc.
	def resolveNamedLocal(self, block, insn, oper, pointer=False):
		if pointer:
			if oper.type != AwlOperator.NAMED_LOCAL_PTR:
				return oper
		else:
			if oper.type != AwlOperator.NAMED_LOCAL:
				return oper

		field = block.interface.getFieldByName(oper.value)
		if block.interface.hasInstanceDB or\
		   field.fieldType == BlockInterfaceField.FTYPE_TEMP:
			# This is an FB or a TEMP access. Translate the operator
			# to a DI/TEMP access.
			newOper = block.interface.getOperatorForFieldName(oper.value, pointer)
			newOper.setInsn(oper.insn)
			return newOper
		else:
			# This is an FC. Accesses to local symbols
			# are resolved at runtime.
			# Just set the value to the interface index.
			index = block.interface.getFieldIndex(oper.value)
			oper.interfaceIndex = index
		return oper

	def __resolveSymbols_block(self, block):
		for insn in block.insns:
			for i in range(len(insn.ops)):
				insn.ops[i] = self.__resolveClassicSym(block,
								insn, insn.ops[i])
				insn.ops[i] = self.resolveNamedLocal(block,
								insn, insn.ops[i],
								pointer=False)
				if insn.ops[i].type == AwlOperator.INDIRECT:
					insn.ops[i].offsetOper = \
						self.__resolveClassicSym(block,
								insn, insn.ops[i].offsetOper)
					insn.ops[i].offsetOper = \
						self.resolveNamedLocal(block,
								insn, insn.ops[i].offsetOper,
								pointer=False)
				insn.ops[i] = self.resolveNamedLocal(block,
								insn, insn.ops[i],
								pointer=True)
			for i in range(len(insn.params)):
				insn.params[i].rvalueOp = self.__resolveClassicSym(block,
								insn, insn.params[i].rvalueOp)
				insn.params[i].rvalueOp = self.resolveNamedLocal(block,
								insn, insn.params[i].rvalueOp,
								pointer=False)
				if insn.params[i].rvalueOp.type == AwlOperator.INDIRECT:
					insn.params[i].rvalueOp.offsetOper =\
						self.__resolveClassicSym(block,
								insn, insn.params[i].rvalueOp.offsetOper)
					insn.params[i].rvalueOp.offsetOper =\
						self.resolveNamedLocal(block,
								insn, insn.params[i].rvalueOp.offsetOper,
								pointer=False)
				insn.params[i].rvalueOp = self.resolveNamedLocal(block,
								insn, insn.params[i].rvalueOp,
								pointer=True)

	# Resolve all symbols (global and local) on all blocks, as far as possible.
	def __resolveSymbols(self):
		for ob in self.obs.values():
			self.__resolveSymbols_block(ob)
		for fb in self.fbs.values():
			self.__resolveSymbols_block(fb)
		for fc in self.fcs.values():
			self.__resolveSymbols_block(fc)
		for sfc in self.sfcs.values():
			self.__resolveSymbols_block(sfc)
			sfc.resolveHardwiredSymbols()
		for sfb in self.sfbs.values():
			self.__resolveSymbols_block(sfb)
			sfb.resolveHardwiredSymbols()

	# Run static error checks for code block
	def __staticSanityChecks_block(self, block):
		for insn in block.insns:
			insn.staticSanityChecks()

	# Run static error checks
	def __staticSanityChecks(self):
		try:
			self.obs[1]
		except KeyError:
			raise AwlSimError("No OB1 defined")

		for ob in self.obs.values():
			self.__staticSanityChecks_block(ob)
		for fb in self.fbs.values():
			self.__staticSanityChecks_block(fb)
		for fc in self.fcs.values():
			self.__staticSanityChecks_block(fc)

	def load(self, parseTree):
		# Mnemonics autodetection
		self.__detectMnemonics(parseTree)
		# Translate OBs
		for obNumber, rawOB in parseTree.obs.items():
			obNumber = self.__resolveBlockName(AwlDataType.TYPE_OB_X,
							   obNumber)
			if obNumber in self.obs:
				raise AwlSimError("Multiple definitions of "\
					"OB %d" % obNumber)
			rawOB.index = obNumber
			ob = self.__translateCodeBlock(rawOB, OB)
			self.obs[obNumber] = ob
			# Create the TEMP-preset handler table
			try:
				presetHandlerClass = OBTempPresets_table[obNumber]
			except KeyError:
				presetHandlerClass = OBTempPresets_dummy
			self.obTempPresetHandlers[obNumber] = presetHandlerClass(self)
		# Translate FBs
		for fbNumber, rawFB in parseTree.fbs.items():
			fbNumber = self.__resolveBlockName(AwlDataType.TYPE_FB_X,
							   fbNumber)
			if fbNumber in self.fbs:
				raise AwlSimError("Multiple definitions of "\
					"FB %d" % fbNumber)
			rawFB.index = fbNumber
			fb = self.__translateCodeBlock(rawFB, FB)
			self.fbs[fbNumber] = fb
		# Translate FCs
		for fcNumber, rawFC in parseTree.fcs.items():
			fcNumber = self.__resolveBlockName(AwlDataType.TYPE_FC_X,
							   fcNumber)
			if fcNumber in self.fcs:
				raise AwlSimError("Multiple definitions of "\
					"FC %d" % fcNumber)
			rawFC.index = fcNumber
			fc = self.__translateCodeBlock(rawFC, FC)
			self.fcs[fcNumber] = fc

		if not self.sfbs:
			# Create the SFB tables
			for sfbNumber in SFB_table.keys():
				if sfbNumber < 0 and not self.__extendedInsnsEnabled:
					continue
				sfb = SFB_table[sfbNumber](self)
				sfb.interface.buildDataStructure()
				self.sfbs[sfbNumber] = sfb
		if not self.sfcs:
			# Create the SFC tables
			for sfcNumber in SFC_table.keys():
				if sfcNumber < 0 and not self.__extendedInsnsEnabled:
					continue
				sfc = SFC_table[sfcNumber](self)
				sfc.interface.buildDataStructure()
				self.sfcs[sfcNumber] = sfc

		# Translate DBs
		for dbNumber, rawDB in parseTree.dbs.items():
			dbNumber = self.__resolveBlockName(AwlDataType.TYPE_DB_X,
							   dbNumber)
			if dbNumber in self.dbs:
				raise AwlSimError("Multiple definitions of "\
					"DB %d" % dbNumber)
			rawDB.index = dbNumber
			db = self.__translateDB(rawDB)
			self.dbs[dbNumber] = db

	def loadSymbolTable(self, symbolTable):
		self.symbolTable.merge(symbolTable)

	def reallocate(self, force=False):
		if force or (self.specs.nrAccus == 4) != self.is4accu:
			self.accu1, self.accu2 = Accu(), Accu()
			if self.specs.nrAccus == 2:
				self.accu3, self.accu4 = None, None
			elif self.specs.nrAccus == 4:
				self.accu3, self.accu4 = Accu(), Accu()
			else:
				assert(0)
		if force or self.specs.nrTimers != len(self.timers):
			self.timers = [ Timer(self, i)
					for i in range(self.specs.nrTimers) ]
		if force or self.specs.nrCounters != len(self.counters):
			self.counters = [ Counter(self, i)
					  for i in range(self.specs.nrCounters) ]
		if force or self.specs.nrFlags != len(self.flags):
			self.flags = ByteArray(self.specs.nrFlags)
		if force or self.specs.nrInputs != len(self.inputs):
			self.inputs = ByteArray(self.specs.nrInputs)
		if force or self.specs.nrOutputs != len(self.outputs):
			self.outputs = ByteArray(self.specs.nrOutputs)
		CallStackElem.resetCache()

	def reset(self):
		self.dbs = {
			# DBs
			0 : DB(0, permissions = 0), # read/write-protected system-DB
		}
		self.obs = {
			# OBs
		}
		self.obTempPresetHandlers = {
			# OB TEMP-preset handlers
		}
		self.fcs = {
			# User FCs
		}
		self.fbs = {
			# User FBs
		}
		self.sfcs = {
			# System SFCs
		}
		self.sfbs = {
			# System SFBs
		}
		self.symbolTable = SymbolTable()
		self.reallocate(force=True)
		self.ar1 = Adressregister()
		self.ar2 = Adressregister()
		self.dbRegister = self.dbs[0]
		self.diRegister = self.dbs[0]
		self.callStack = [ ]
		self.callStackTop = None
		self.setMcrActive(False)
		self.mcrStack = [ ]
		self.statusWord = S7StatusWord()

		self.relativeJump = 1

		# Stats
		self.__insnCount = 0
		self.__cycleCount = 0
		self.insnPerSecond = 0.0
		self.avgInsnPerCycle = 0.0
		self.cycleStartTime = 0.0
		self.minCycleTime = 86400.0
		self.maxCycleTime = 0.0
		self.avgCycleTime = 0.0
		self.startupTime = 0.0
		self.__speedMeasureStartTime = 0
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0

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

	def setPeripheralReadCallback(self, cb, data=None):
		self.cbPeripheralRead = cb
		self.cbPeripheralReadData = data

	def setPeripheralWriteCallback(self, cb, data=None):
		self.cbPeripheralWrite = cb
		self.cbPeripheralWriteData = data

	def setScreenUpdateCallback(self, cb, data=None):
		self.cbScreenUpdate = cb
		self.cbScreenUpdateData = data

	def requestScreenUpdate(self):
		if self.cbScreenUpdate:
			self.cbScreenUpdate(self.cbScreenUpdateData)

	@property
	def is4accu(self):
		return self.accu4 is not None

	def __runOB(self, block):
		# Update timekeeping
		self.updateTimestamp()
		self.cycleStartTime = self.now

		# Initialize CPU state
		self.callStack = [ CallStackElem(self, block) ]
		self.dbRegister = self.diRegister = self.dbs[0]
		cse = self.callStackTop = self.callStack[-1]
		if self.__obTempPresetsEnabled:
			# Populate the TEMP region
			self.obTempPresetHandlers[block.index].generate(cse.localdata)

		# Run the user program cycle
		while self.callStack:
			while cse.ip < len(cse.insns):
				insn, self.relativeJump = cse.insns[cse.ip], 1
				insn.run()
				if self.cbPostInsn:
					self.cbPostInsn(self.cbPostInsnData)
				cse.ip += self.relativeJump
				cse, self.__insnCount = self.callStackTop,\
							(self.__insnCount + 1) & 0x3FFFFFFF
				if not self.__insnCount % 64:
					self.updateTimestamp()
					self.__runTimeCheck()
			if self.cbBlockExit:
				self.cbBlockExit(self.cbBlockExitData)
			prevCse = self.callStack.pop()
			if self.callStack:
				cse = self.callStackTop = self.callStack[-1]
				prevCse.handleBlockExit()
			prevCse.destroy()
		if self.cbCycleExit:
			self.cbCycleExit(self.cbCycleExitData)

	# Run startup code
	def startup(self):
		# Resolve symbolic instructions and operators
		self.__resolveSymbols()
		# Run some static sanity checks on the code
		self.__staticSanityChecks()

		self.updateTimestamp()
		self.__speedMeasureStartTime = self.now
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0
		self.startupTime = self.now

		# Run startup OB
		for obNumber in (100, 101, 102):
			ob = self.obs.get(obNumber)
			if ob is not None:
				self.__runOB(ob)
				break

	# Run one cycle of the user program
	def runCycle(self):
		# Run the actual OB1 code
		self.__runOB(self.obs[1])

		# Update timekeeping and statistics
		self.updateTimestamp()
		self.__cycleCount = (self.__cycleCount + 1) & 0x3FFFFFFF

		# Evaluate speed measurement
		elapsedTime = self.now - self.__speedMeasureStartTime
		if elapsedTime >= 1.0:
			# Calculate instruction and cycle counts.
			cycleCount = (self.__cycleCount - self.__speedMeasureStartCycleCount) &\
				     0x3FFFFFFF
			insnCount = (self.__insnCount - self.__speedMeasureStartInsnCount) &\
				    0x3FFFFFFF

			# Calculate instruction statistics.
			self.insnPerSecond = insnCount / elapsedTime
			self.avgInsnPerCycle = insnCount / cycleCount

			# Get the average cycle time over the measurement period.
			cycleTime = elapsedTime / cycleCount

			# Store overall-average cycle time and maximum cycle time.
			self.maxCycleTime = max(self.maxCycleTime, cycleTime)
			self.minCycleTime = min(self.minCycleTime, cycleTime)
			self.avgCycleTime = (self.avgCycleTime + cycleTime) / 2.0

			# Reset the counters
			self.__speedMeasureStartTime = self.now
			self.__speedMeasureStartInsnCount = self.__insnCount
			self.__speedMeasureStartCycleCount = self.__cycleCount

	def __updateTimestamp_perf(self):
		self.now = time.perf_counter()

	def __updateTimestamp_time(self):
		self.now = time.time()

	# Construct updateTimestamp() method.
	# updateTimestamp() updates self.now, which is a
	# floating point count of seconds.
	if hasattr(time, "perf_counter"):
		updateTimestamp = __updateTimestamp_perf
	else:
		updateTimestamp = __updateTimestamp_time

	__dateAndTimeWeekdayMap = {
		0	: 2,	# monday
		1	: 3,	# tuesday
		2	: 4,	# wednesday
		3	: 5,	# thursday
		4	: 6,	# friday
		5	: 7,	# saturday
		6	: 1,	# sunday
	}

	# Make a DATE_AND_TIME for the current wall-time and
	# store it in byteArray, which is a list of GenericByte objects.
	# If byteArray is smaller than 8 bytes, an IndexError is raised.
	def makeCurrentDateAndTime(self, byteArray, offset):
		dt = datetime.datetime.now()
		year, month, day, hour, minute, second, msec =\
			dt.year, dt.month, dt.day, dt.hour, \
			dt.minute, dt.second, dt.microsecond // 1000
		byteArray[offset] = (year % 10) | (((year // 10) % 10) << 4)
		byteArray[offset + 1] = (month % 10) | (((month // 10) % 10) << 4)
		byteArray[offset + 2] = (day % 10) | (((day // 10) % 10) << 4)
		byteArray[offset + 3] = (hour % 10) | (((hour // 10) % 10) << 4)
		byteArray[offset + 4] = (minute % 10) | (((minute // 10) % 10) << 4)
		byteArray[offset + 5] = (second % 10) | (((second // 10) % 10) << 4)
		byteArray[offset + 6] = ((msec // 10) % 10) | (((msec // 100) % 10) << 4)
		byteArray[offset + 7] = ((msec % 10) << 4) |\
					self.__dateAndTimeWeekdayMap[dt.weekday()]

	def __runTimeCheck(self):
		if self.now - self.cycleStartTime > self.cycleTimeLimit:
			raise AwlSimError("Cycle time exceed %.3f seconds" %\
					  self.cycleTimeLimit)

	def getCurrentIP(self):
		try:
			return self.callStackTop.ip
		except IndexError as e:
			return None

	def getCurrentInsn(self):
		try:
			cse = self.callStackTop
			if not cse:
				return None
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
		fc = self.fcs[blockOper.value.byteOffset]
		return CallStackElem(self, fc, None, parameters)

	def __call_RAW_FC(self, blockOper, dbOper, parameters):
		fc = self.fcs[blockOper.value.byteOffset]
		return CallStackElem(self, fc, None, (), True)

	def __call_FB(self, blockOper, dbOper, parameters):
		fb = self.fbs[blockOper.value.byteOffset]
		db = self.dbs[dbOper.value.byteOffset]
		cse = CallStackElem(self, fb, db, parameters)
		self.dbRegister, self.diRegister = self.diRegister, db
		return cse

	def __call_RAW_FB(self, blockOper, dbOper, parameters):
		fb = self.fbs[blockOper.value.byteOffset]
		return CallStackElem(self, fb, self.diRegister, (), True)

	def __call_SFC(self, blockOper, dbOper, parameters):
		sfc = self.sfcs[blockOper.value.byteOffset]
		return CallStackElem(self, sfc, None, parameters)

	def __call_RAW_SFC(self, blockOper, dbOper, parameters):
		sfc = self.sfcs[blockOper.value.byteOffset]
		return CallStackElem(self, sfc, None, (), True)

	def __call_SFB(self, blockOper, dbOper, parameters):
		sfb = self.sfbs[blockOper.value.byteOffset]
		db = self.dbs[dbOper.value.byteOffset]
		cse = CallStackElem(self, sfb, db, parameters)
		self.dbRegister, self.diRegister = self.diRegister, db
		return cse

	def __call_RAW_SFB(self, blockOper, dbOper, parameters):
		sfb = self.sfbs[blockOper.value.byteOffset]
		return CallStackElem(self, sfb, self.diRegister, (), True)

	def __call_INDIRECT(self, blockOper, dbOper, parameters):
		blockOper = blockOper.resolve()
		callHelper = self.__rawCallHelpers[blockOper.type]
		try:
			return callHelper(self, blockOper, dbOper, parameters)
		except KeyError as e:
			raise AwlSimError("Code block %d not found in indirect call" %\
					  blockOper.value.byteOffset)

	__callHelpers = {
		AwlOperator.BLKREF_FC	: __call_FC,
		AwlOperator.BLKREF_FB	: __call_FB,
		AwlOperator.BLKREF_SFC	: __call_SFC,
		AwlOperator.BLKREF_SFB	: __call_SFB,
	}

	__rawCallHelpers = {
		AwlOperator.BLKREF_FC	: __call_RAW_FC,
		AwlOperator.BLKREF_FB	: __call_RAW_FB,
		AwlOperator.BLKREF_SFC	: __call_RAW_SFC,
		AwlOperator.BLKREF_SFB	: __call_RAW_SFB,
		AwlOperator.INDIRECT	: __call_INDIRECT,
	}

	def run_CALL(self, blockOper, dbOper=None, parameters=(), raw=False):
		try:
			if raw:
				callHelper = self.__rawCallHelpers[blockOper.type]
			else:
				callHelper = self.__callHelpers[blockOper.type]
		except KeyError:
			raise AwlSimError("Invalid CALL operand")
		newCse = callHelper(self, blockOper, dbOper, parameters)
		if newCse:
			self.callStack.append(newCse)
			self.callStackTop = newCse

	def run_BE(self):
		s = self.statusWord
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
		# Jump beyond end of block
		cse = self.callStackTop
		self.relativeJump = len(cse.insns) - cse.ip

	def run_AUF(self, dbOper):
		dbOper = dbOper.resolve()
		try:
			db = self.dbs[dbOper.value.byteOffset]
		except KeyError:
			raise AwlSimError("Datablock %i does not exist" %\
					  dbOper.value.byteOffset)
		if dbOper.type == AwlOperator.BLKREF_DB:
			self.dbRegister = db
		elif dbOper.type == AwlOperator.BLKREF_DI:
			self.diRegister = db
		else:
			raise AwlSimError("Invalid DB reference in AUF")

	def run_TDB(self):
		# Swap global and instance DB
		self.diRegister, self.dbRegister = self.dbRegister, self.diRegister

	def getStatusWord(self):
		return self.statusWord

	def getAccu(self, index):
		if index < 1 or index > self.specs.nrAccus:
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
		return (not self.mcrActive or all(self.mcrStack))

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
		cse = self.callStackTop
		cse.parenStack.append(ParenStackElem(self, insnType, statusWord))
		if len(cse.parenStack) > 7:
			raise AwlSimError("Parenthesis stack overflow")

	# Fetch a range in the 'output' memory area.
	# 'byteOffset' is the byte offset into the output area.
	# 'byteCount' is the number if bytes to fetch.
	# Returns a bytearray.
	def fetchOutputRange(self, byteOffset, byteCount):
		return self.outputs[byteOffset : byteOffset + byteCount]

	# Store a range in the 'input' memory area.
	# 'byteOffset' is the byte offset into the input area.
	# 'data' is a bytearray.
	def storeInputRange(self, byteOffset, data):
		self.inputs[byteOffset : byteOffset + len(data)] = data

	def fetch(self, operator, enforceWidth=()):
		try:
			fetchMethod = self.fetchTypeMethods[operator.type]
		except KeyError:
			raise AwlSimError("Invalid fetch request: %s" %\
				AwlOperator.type2str[operator.type])
		return fetchMethod(self, operator, enforceWidth)

	def __fetchWidthError(self, operator, enforceWidth):
		raise AwlSimError("Data fetch of %d bits, "
			"but only %s bits are allowed." %\
			(operator.width,
			 listToHumanStr(enforceWidth)))

	def fetchIMM(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return operator.value

	def fetchDBLG(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.dbRegister.struct.getSize()

	def fetchDBNO(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.dbRegister.index

	def fetchDILG(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.diRegister.struct.getSize()

	def fetchDINO(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.diRegister.index

	def fetchAR2(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.getAR(2).get()

	def fetchSTW(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		if operator.width == 1:
			return self.statusWord.getByBitNumber(operator.value.bitOffset)
		elif operator.width == 16:
			return self.statusWord.getWord()
		else:
			assert(0)

	def fetchSTW_Z(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return (self.statusWord.A0 ^ 1) & (self.statusWord.A1 ^ 1)

	def fetchSTW_NZ(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.statusWord.A0 | self.statusWord.A1

	def fetchSTW_POS(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return (self.statusWord.A0 ^ 1) & self.statusWord.A1

	def fetchSTW_NEG(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.statusWord.A0 & (self.statusWord.A1 ^ 1)

	def fetchSTW_POSZ(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.statusWord.A0 ^ 1

	def fetchSTW_NEGZ(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.statusWord.A1 ^ 1

	def fetchSTW_UO(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.statusWord.A0 & self.statusWord.A1

	def fetchE(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.inputs.fetch(operator.value, operator.width)

	def fetchA(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.outputs.fetch(operator.value, operator.width)

	def fetchM(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.flags.fetch(operator.value, operator.width)

	def fetchL(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.callStackTop.localdata.fetch(operator.value, operator.width)

	def fetchVL(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		try:
			cse = self.callStack[-2]
		except IndexError:
			raise AwlSimError("Fetch of parent localstack, "
				"but no parent present.")
		return cse.localdata.fetch(operator.value, operator.width)

	def fetchDB(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		if operator.value.dbNumber is not None:
			# This is a fully qualified access (DBx.DBx X)
			# Open the data block first.
			self.run_AUF(AwlOperator(AwlOperator.BLKREF_DB, 16,
						 AwlOffset(operator.value.dbNumber),
						 operator.insn))
		if not self.dbRegister:
			raise AwlSimError("Fetch from global DB, "
				"but no DB is opened")
		return self.dbRegister.fetch(operator)

	def fetchDI(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		if not self.diRegister:
			raise AwlSimError("Fetch from instance DI, "
				"but no DI is opened")
		return self.diRegister.fetch(operator)

	def fetchPE(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		value = None
		if self.cbPeripheralRead:
			value = self.cbPeripheralRead(self.cbPeripheralReadData,
						      operator.width,
						      operator.value.byteOffset)
		if value is None:
			raise AwlSimError("There is no hardware to handle "
				"the direct peripheral fetch. "
				"(width=%d, offset=%d)" %\
				(operator.width, operator.value.byteOffset))
		self.inputs.store(operator.value, operator.width, value)
		return self.inputs.fetch(operator.value, operator.width)

	def fetchT(self, operator, enforceWidth):
		insnType = operator.insn.type
		if insnType == AwlInsn.TYPE_L or insnType == AwlInsn.TYPE_LC:
			width = 32
		else:
			width = 1
		if width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		timer = self.getTimer(operator.value.byteOffset)
		if insnType == AwlInsn.TYPE_L:
			return timer.getTimevalBin()
		elif insnType == AwlInsn.TYPE_LC:
			return timer.getTimevalS5T()
		return timer.get()

	def fetchZ(self, operator, enforceWidth):
		insnType = operator.insn.type
		if insnType == AwlInsn.TYPE_L or insnType == AwlInsn.TYPE_LC:
			width = 32
		else:
			width = 1
		if width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		counter = self.getCounter(operator.value.byteOffset)
		if insnType == AwlInsn.TYPE_L:
			return counter.getValueBin()
		elif insnType == AwlInsn.TYPE_LC:
			return counter.getValueBCD()
		return counter.get()

	def fetchNAMED_LOCAL(self, operator, enforceWidth):
		# load from an FC interface field.
		return self.fetch(self.callStackTop.interfRefs[operator.interfaceIndex].resolve(False),
				  enforceWidth)

	def fetchNAMED_LOCAL_PTR(self, operator, enforceWidth):
		return self.callStackTop.interfRefs[operator.interfaceIndex].resolve(False).makePointer()

	def fetchINDIRECT(self, operator, enforceWidth):
		return self.fetch(operator.resolve(False), enforceWidth)

	def fetchVirtACCU(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.getAccu(operator.value.byteOffset).get()

	def fetchVirtAR(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return self.getAR(operator.value.byteOffset).get()

	def fetchVirtDBR(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		if operator.value.byteOffset == 1:
			if self.dbRegister:
				return self.dbRegister.index
		elif operator.value.byteOffset == 2:
			if self.diRegister:
				return self.diRegister.index
		else:
			raise AwlSimError("Invalid __DBR %d. "
				"Must be 1 for DB-register or "
				"2 for DI-register." %\
				operator.value.byteOffset)
		return 0

	fetchTypeMethods = {
		AwlOperator.IMM			: fetchIMM,
		AwlOperator.IMM_REAL		: fetchIMM,
		AwlOperator.IMM_S5T		: fetchIMM,
		AwlOperator.IMM_TIME		: fetchIMM,
		AwlOperator.IMM_DATE		: fetchIMM,
		AwlOperator.IMM_TOD		: fetchIMM,
		AwlOperator.IMM_PTR		: fetchIMM,
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
		AwlOperator.MEM_DBLG		: fetchDBLG,
		AwlOperator.MEM_DBNO		: fetchDBNO,
		AwlOperator.MEM_DILG		: fetchDILG,
		AwlOperator.MEM_DINO		: fetchDINO,
		AwlOperator.MEM_AR2		: fetchAR2,
		AwlOperator.MEM_STW		: fetchSTW,
		AwlOperator.MEM_STW_Z		: fetchSTW_Z,
		AwlOperator.MEM_STW_NZ		: fetchSTW_NZ,
		AwlOperator.MEM_STW_POS		: fetchSTW_POS,
		AwlOperator.MEM_STW_NEG		: fetchSTW_NEG,
		AwlOperator.MEM_STW_POSZ	: fetchSTW_POSZ,
		AwlOperator.MEM_STW_NEGZ	: fetchSTW_NEGZ,
		AwlOperator.MEM_STW_UO		: fetchSTW_UO,
		AwlOperator.NAMED_LOCAL		: fetchNAMED_LOCAL,
		AwlOperator.NAMED_LOCAL_PTR	: fetchNAMED_LOCAL_PTR,
		AwlOperator.INDIRECT		: fetchINDIRECT,
		AwlOperator.VIRT_ACCU		: fetchVirtACCU,
		AwlOperator.VIRT_AR		: fetchVirtAR,
		AwlOperator.VIRT_DBR		: fetchVirtDBR,
	}

	def store(self, operator, value, enforceWidth=()):
		try:
			storeMethod = self.storeTypeMethods[operator.type]
		except KeyError:
			raise AwlSimError("Invalid store request")
		storeMethod(self, operator, value, enforceWidth)

	def __storeWidthError(self, operator, enforceWidth):
		raise AwlSimError("Data store of %d bits, "
			"but only %s bits are allowed." %\
			(operator.width,
			 listToHumanStr(enforceWidth)))

	def storeE(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		self.inputs.store(operator.value, operator.width, value)

	def storeA(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		self.outputs.store(operator.value, operator.width, value)

	def storeM(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		self.flags.store(operator.value, operator.width, value)

	def storeL(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		self.callStackTop.localdata.store(operator.value, operator.width, value)

	def storeVL(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		try:
			cse = self.callStack[-2]
		except IndexError:
			raise AwlSimError("Store to parent localstack, "
				"but no parent present.")
		cse.localdata.store(operator.value, operator.width, value)

	def storeDB(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		if operator.value.dbNumber is None:
			db = self.dbRegister
			if not db:
				raise AwlSimError("Store to global DB, "
					"but no DB is opened")
		else:
			try:
				db = self.dbs[operator.value.dbNumber]
			except KeyError:
				raise AwlSimError("Store to DB %d, but DB "
					"does not exist" % operator.value.dbNumber)
		db.store(operator, value)

	def storeDI(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		if not self.diRegister:
			raise AwlSimError("Store to instance DI, "
				"but no DI is opened")
		self.diRegister.store(operator, value)

	def storePA(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		self.outputs.store(operator.value, operator.width, value)
		ok = False
		if self.cbPeripheralWrite:
			ok = self.cbPeripheralWrite(self.cbPeripheralWriteData,
						    operator.width,
						    operator.value.byteOffset,
						    value)
		if not ok:
			raise AwlSimError("There is no hardware to handle "
				"the direct peripheral store. "
				"(width=%d, offset=%d, value=0x%X)" %\
				(operator.width, operator.value.byteOffset,
				 value))

	def storeAR2(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		self.getAR(2).set(value)

	def storeSTW(self, operator, value, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__storeWidthError(operator, enforceWidth)

		if operator.width == 1:
			raise AwlSimError("Cannot store to individual STW bits")
		elif operator.width == 16:
			self.statusWord.setWord(value)
		else:
			assert(0)

	def storeNAMED_LOCAL(self, operator, value, enforceWidth):
		# store to an FC interface field.
		self.store(self.callStackTop.interfRefs[operator.interfaceIndex].resolve(True),
			   value, enforceWidth)

	def storeINDIRECT(self, operator, value, enforceWidth):
		self.store(operator.resolve(True), value, enforceWidth)

	storeTypeMethods = {
		AwlOperator.MEM_E		: storeE,
		AwlOperator.MEM_A		: storeA,
		AwlOperator.MEM_M		: storeM,
		AwlOperator.MEM_L		: storeL,
		AwlOperator.MEM_VL		: storeVL,
		AwlOperator.MEM_DB		: storeDB,
		AwlOperator.MEM_DI		: storeDI,
		AwlOperator.MEM_PA		: storePA,
		AwlOperator.MEM_AR2		: storeAR2,
		AwlOperator.MEM_STW		: storeSTW,
		AwlOperator.NAMED_LOCAL		: storeNAMED_LOCAL,
		AwlOperator.INDIRECT		: storeINDIRECT,
	}

	def __dumpMem(self, prefix, memArray, maxLen):
		ret, line, first, count, i = [], [], True, 0, 0
		while i < maxLen:
			line.append("%02X" % memArray[i])
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
		self.updateTimestamp()
		ret = []
		ret.append("=== S7-CPU dump ===  (t: %.01fs)" %\
			   (self.now - self.startupTime))
		ret.append("    STW:  " + str(self.statusWord))
		if self.is4accu:
			accus = [ accu.toHex()
				  for accu in (self.accu1, self.accu2,
				  	       self.accu3, self.accu4) ]
		else:
			accus = [ accu.toHex()
				  for accu in (self.accu1, self.accu2) ]
		ret.append("   Accu:  " + "  ".join(accus))
		ars = [ "%s (%s)" % (ar.toHex(), ar.toPointerString())
			for ar in (self.ar1, self.ar2) ]
		ret.append("     AR:  " + "  ".join(ars))
		ret.append(self.__dumpMem("      M:  ",
					  self.flags,
					  min(64, self.specs.nrFlags)))
		ret.append(self.__dumpMem("    PAE:  ",
					  self.inputs,
					  min(64, self.specs.nrInputs)))
		ret.append(self.__dumpMem("    PAA:  ",
					  self.outputs,
					  min(64, self.specs.nrOutputs)))
		pstack = str(self.callStackTop.parenStack) if self.callStackTop.parenStack else "Empty"
		ret.append(" PStack:  " + pstack)
		ret.append("     DB:  %s" % str(self.dbRegister))
		ret.append("     DI:  %s" % str(self.diRegister))
		if self.callStack:
			elems = [ str(cse) for cse in self.callStack ]
			elems = " => ".join(elems)
			ret.append("  Calls:  depth:%d   %s" %\
				   (len(self.callStack), elems))
			cse = self.callStack[-1]
			ret.append(self.__dumpMem("      L:  ",
						  cse.localdata,
						  min(16, self.specs.nrLocalbytes)))
		else:
			ret.append("  Calls:  None")
		curInsn = self.getCurrentInsn()
		ret.append("   Stmt:  IP:%s   %s" %\
			   (str(self.getCurrentIP()),
			    str(curInsn) if curInsn else ""))
		ret.append("  Speed:  %d stmt/s  %.01f stmt/cycle" %\
			   (int(round(self.insnPerSecond)),
			    self.avgInsnPerCycle))
		ret.append(" CycleT:  avg:%.06fs  min:%.06fs  max:%.06fs" %\
			   (self.avgCycleTime, self.minCycleTime,
			    self.maxCycleTime))
		return '\n'.join(ret)
