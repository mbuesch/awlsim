# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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
from awlsim.common.compat import *

import time
import datetime
import random
from collections import deque

from awlsim.common.util import *
from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.blockinfo import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *
from awlsim.common.env import *
from awlsim.common.version import *

from awlsim.library.libentry import *

from awlsim.core.symbolparser import *
from awlsim.core.memory import * #+cimport
from awlsim.core.instructions.all_insns import * #+cimport
from awlsim.core.systemblocks.tables import *
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.blocks import * #+cimport
from awlsim.core.datablocks import * #+cimport
from awlsim.core.userdefinedtypes import * #+cimport
from awlsim.core.statusword import * #+cimport
from awlsim.core.labels import *
from awlsim.core.timers import * #+cimport
from awlsim.core.counters import * #+cimport
from awlsim.core.callstack import * #+cimport
from awlsim.core.lstack import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.obtemp import *
from awlsim.core.util import *

from awlsim.awlcompiler.translator import *


class ParenStackElem(object): #+cdef
	"Parenthesis stack element"

	def __init__(self, cpu, insnType, statusWord): #@nocy
#@cy	def __cinit__(self, S7CPU cpu, uint32_t insnType, S7StatusWord statusWord):
		self.cpu = cpu
		self.insnType = insnType
		self.NER = statusWord.NER
		self.VKE = statusWord.VKE
		self.OR = statusWord.OR

	def __repr__(self):
		mnemonics = self.cpu.getMnemonics()
		type2name = {
			S7CPUConfig.MNEMONICS_EN : AwlInsn.type2name_english,
			S7CPUConfig.MNEMONICS_DE : AwlInsn.type2name_german,
		}[mnemonics]
		return '(insn="%s" VKE=%s OR=%d)' %\
			(type2name[self.insnType],
			 self.VKE, self.OR)

class S7Prog(object):
	"S7 CPU program management"

	def __init__(self, cpu):
		self.cpu = cpu

		self.pendingRawDBs = []
		self.pendingRawFBs = []
		self.pendingRawFCs = []
		self.pendingRawOBs = []
		self.pendingRawUDTs = []
		self.pendingLibSelections = []
		self.symbolTable = SymbolTable()

		self.reset()

	def reset(self):
		for rawBlock in itertools.chain(self.pendingRawDBs,
						self.pendingRawFBs,
						self.pendingRawFCs,
						self.pendingRawOBs,
						self.pendingRawUDTs):
			rawBlock.destroySourceRef()
		self.pendingRawDBs = []
		self.pendingRawFBs = []
		self.pendingRawFCs = []
		self.pendingRawOBs = []
		self.pendingRawUDTs = []
		self.pendingLibSelections = []
		self.symbolTable.clear()

	def addRawDB(self, rawDB):
		assert(isinstance(rawDB, RawAwlDB))
		self.pendingRawDBs.append(rawDB)

	def addRawFB(self, rawFB):
		assert(isinstance(rawFB, RawAwlFB))
		self.pendingRawFBs.append(rawFB)

	def addRawFC(self, rawFC):
		assert(isinstance(rawFC, RawAwlFC))
		self.pendingRawFCs.append(rawFC)

	def addRawOB(self, rawOB):
		assert(isinstance(rawOB, RawAwlOB))
		self.pendingRawOBs.append(rawOB)

	def addRawUDT(self, rawUDT):
		assert(isinstance(rawUDT, RawAwlUDT))
		self.pendingRawUDTs.append(rawUDT)

	def addLibrarySelection(self, libSelection):
		assert(isinstance(libSelection, AwlLibEntrySelection))
		self.pendingLibSelections.append(libSelection)

	def loadSymbolTable(self, symbolTable):
		self.symbolTable.merge(symbolTable)

	def __detectMnemonics(self):
		conf = self.cpu.getConf()
		if conf.getConfiguredMnemonics() != S7CPUConfig.MNEMONICS_AUTO:
			return

		detected = None
		errorCounts = {}
		rawBlocks = list(itertools.chain(self.pendingRawOBs,
						 self.pendingRawFBs,
						 self.pendingRawFCs))
		if not rawBlocks:
			if conf.getMnemonics() != S7CPUConfig.MNEMONICS_AUTO:
				# It was already set. We are Ok.
				return
			# There are no blocks and we didn't detect anything, yet.
			# Just set it to EN.
			detected = S7CPUConfig.MNEMONICS_EN
		if detected is None:
			for mnemonics in (S7CPUConfig.MNEMONICS_EN,
					  S7CPUConfig.MNEMONICS_DE):
				errorCount = 0
				for rawBlock in rawBlocks:
					for rawInsn in rawBlock.insns:
						ret = AwlInsnTranslator.name2type(rawInsn.getName(),
										  mnemonics)
						if ret is None:
							errorCount += 1
						try:
							optrans = AwlOpTranslator(mnemonics=mnemonics)
							optrans.translateFromRawInsn(rawInsn)
						except AwlSimError:
							errorCount += 1
				if errorCount == 0:
					# No error. Use these mnemonics.
					detected = mnemonics
					break
				errorCounts[mnemonics] = errorCount
		if detected is None:
			# Select the mnemonics with the lower error count.
			if errorCounts[S7CPUConfig.MNEMONICS_EN] <= errorCounts[S7CPUConfig.MNEMONICS_DE]:
				detected = S7CPUConfig.MNEMONICS_EN
			else:
				detected = S7CPUConfig.MNEMONICS_DE
		if conf.getMnemonics() not in {S7CPUConfig.MNEMONICS_AUTO, detected}:
			# Autodetected mnemonics were already set before
			# to something different.
			raise AwlSimError("Cannot mix multiple AWL files with "\
				"distinct mnemonics. This error may be caused by "\
				"incorrect autodetection. "\
				"Force mnemonics to EN or DE to avoid this error.")
		conf.setDetectedMnemonics(detected)

	def __loadLibraries(self):
		for libSelection in self.pendingLibSelections:
			# Get the block class from the library.
			libEntryCls = AwlLib.getEntryBySelection(libSelection)
			assert(not libEntryCls._isSystemBlock)

			# Get the effective block index.
			effIndex = libSelection.getEffectiveEntryIndex()
			if effIndex < 0:
				effIndex = libSelection.getEntryIndex()

			# Create and translate the block
			translator = AwlTranslator(self.cpu)
			if libEntryCls._isFC:
				block = libEntryCls(index = effIndex)
				if block.index in self.cpu.fcs and\
				   not self.cpu.fcs[block.index].isLibraryBlock:
					raise AwlSimError("Error while loading library "
						"block FC %d: Block FC %d is already "
						"loaded as user defined block." %\
						(block.index, block.index))
				block = translator.translateLibraryCodeBlock(block)
				self.cpu.fcs[block.index] = block
			elif libEntryCls._isFB:
				block = libEntryCls(index = effIndex)
				if block.index in self.cpu.fbs and\
				   not self.cpu.fbs[block.index].isLibraryBlock:
					raise AwlSimError("Error while loading library "
						"block FB %d: Block FB %d is already "
						"loaded as user defined block." %\
						(block.index, block.index))
				block = translator.translateLibraryCodeBlock(block)
				self.cpu.fbs[block.index] = block
			else:
				assert(0)
		self.pendingLibSelections = []

	def __checkCallParamTypeCompat(self, block):
		for insn, calledCodeBlock, calledDataBlock in self.cpu.allCallInsns(block):
			try:
				for param in insn.params:
					# Get the interface field for this variable
					field = calledCodeBlock.interface.getFieldByName(param.lvalueName)
					# Check type compatibility
					param.rvalueOp.checkDataTypeCompat(self.cpu, field.dataType)
			except AwlSimError as e:
				e.setInsn(insn)
				raise e

	# Assign call parameter interface reference.
	def __assignParamInterface(self, block):
		for insn, calledCodeBlock, calledDataBlock in self.cpu.allCallInsns(block):
			try:
				for param in insn.params:
					# Add interface references to the parameter assignment.
					param.setInterface(calledCodeBlock.interface)
			except AwlSimError as e:
				e.setInsn(insn)
				raise e

	# Resolve all symbols (global and local) on all blocks, as far as possible.
	def __resolveSymbols(self):
		resolver = AwlSymResolver(self.cpu)
		for block in self.cpu.allCodeBlocks():
			# Add interface references to the parameter assignment.
			self.__assignParamInterface(block)
			# Check type compatibility between formal and
			# actual parameter of calls.
			self.__checkCallParamTypeCompat(block)
			# Resolve all symbols
			resolver.resolveSymbols_block(block)
			# Check type compatibility between formal and
			# actual parameter of calls again, with resolved symbols.
			self.__checkCallParamTypeCompat(block)

	def __finalizeCodeBlock(self, block):
		translator = AwlTranslator(self.cpu)

		# Finalize call instructions
		for insn, calledCodeBlock, calledDataBlock in self.cpu.allCallInsns(block):
			try:
				for param in insn.params:
					# Final translation of parameter assignment operand.
					translator.translateParamAssignOper(param)
			except AwlSimError as e:
				e.setInsn(insn)
				raise e

		# Run the final setup of all instructions.
		for insn in block.insns:
			insn.finalSetup()

		# Check and account for direct L stack allocations and
		# interface L stack allocations.
		block.accountTempAllocations()

	def __finalizeCodeBlocks(self):
		for block in self.cpu.allUserCodeBlocks():
			self.__finalizeCodeBlock(block)

	# Run static error checks for code block
	def __staticSanityChecks_block(self, block):
		for insn in block.insns:
			insn.staticSanityChecks()

	# Run static error checks
	def staticSanityChecks(self):
		# The main cycle expects OB 1 to be present.
		if 1 not in self.cpu.obs:
			raise AwlSimError("OB 1 is not present in the CPU.")
		# Run the user code checks.
		for block in self.cpu.allUserCodeBlocks():
			self.__staticSanityChecks_block(block)

	def build(self):
		"""Translate the loaded sources into their executable forms.
		"""

		from awlsim.core.datatypes import AwlDataType

		translator = AwlTranslator(self.cpu)
		resolver = AwlSymResolver(self.cpu)

		self.__loadLibraries()

		# Mnemonics autodetection
		self.__detectMnemonics()

		# Translate UDTs
		udts = {}
		for rawUDT in self.pendingRawUDTs:
			udtNumber, sym = resolver.resolveBlockName({AwlDataType.TYPE_UDT_X},
								   rawUDT.index)
			if udtNumber in udts:
				raise AwlSimError("Multiple definitions of "\
					"UDT %d." % udtNumber)
			rawUDT.index = udtNumber
			udt = UDT.makeFromRaw(rawUDT)
			if udtNumber in self.cpu.udts:
				self.cpu.udts[udtNumber].destroySourceRef()
			udts[udtNumber] = udt
			self.cpu.udts[udtNumber] = udt
		self.pendingRawUDTs = []

		# Build all UDTs (Resolve sizes of all fields)
		for udt in dictValues(udts):
			udt.buildDataStructure(self.cpu)

		# Translate OBs
		obs = {}
		for rawOB in self.pendingRawOBs:
			obNumber, sym = resolver.resolveBlockName({AwlDataType.TYPE_OB_X},
								  rawOB.index)
			if obNumber in obs:
				raise AwlSimError("Multiple definitions of "\
					"OB %d." % obNumber)
			rawOB.index = obNumber
			ob = translator.translateCodeBlock(rawOB, OB)
			if obNumber in self.cpu.obs:
				self.cpu.obs[obNumber].destroySourceRef()
			obs[obNumber] = ob
			self.cpu.obs[obNumber] = ob
			# Create the TEMP-preset handler table
			try:
				presetHandlerClass = OBTempPresets_table[obNumber]
			except KeyError:
				presetHandlerClass = OBTempPresets_dummy
			self.cpu.obTempPresetHandlers[obNumber] = presetHandlerClass(self.cpu)
		self.pendingRawOBs = []

		# Translate FBs
		fbs = {}
		for rawFB in self.pendingRawFBs:
			fbNumber, sym = resolver.resolveBlockName({AwlDataType.TYPE_FB_X},
								  rawFB.index)
			if fbNumber in fbs:
				raise AwlSimError("Multiple definitions of "\
					"FB %d." % fbNumber)
			if fbNumber in self.cpu.fbs and\
			   self.cpu.fbs[fbNumber].isLibraryBlock:
				raise AwlSimError("Multiple definitions of FB %d.\n"
					"FB %d is already defined by an "
					"imported library block (%s)." % (
					fbNumber, fbNumber,
					self.cpu.fbs[fbNumber].libraryName))
			rawFB.index = fbNumber
			fb = translator.translateCodeBlock(rawFB, FB)
			if fbNumber in self.cpu.fbs:
				self.cpu.fbs[fbNumber].destroySourceRef()
			fbs[fbNumber] = fb
			self.cpu.fbs[fbNumber] = fb
		self.pendingRawFBs = []

		# Translate FCs
		fcs = {}
		for rawFC in self.pendingRawFCs:
			fcNumber, sym = resolver.resolveBlockName({AwlDataType.TYPE_FC_X},
								  rawFC.index)
			if fcNumber in fcs:
				raise AwlSimError("Multiple definitions of "\
					"FC %d." % fcNumber)
			if fcNumber in self.cpu.fcs and\
			   self.cpu.fcs[fcNumber].isLibraryBlock:
				raise AwlSimError("Multiple definitions of FC %d.\n"
					"FC %d is already defined by an "
					"imported library block (%s)." % (
					fcNumber, fcNumber,
					self.cpu.fcs[fcNumber].libraryName))
			rawFC.index = fcNumber
			fc = translator.translateCodeBlock(rawFC, FC)
			if fcNumber in self.cpu.fcs:
				self.cpu.fcs[fcNumber].destroySourceRef()
			fcs[fcNumber] = fc
			self.cpu.fcs[fcNumber] = fc
		self.pendingRawFCs = []

		if not self.cpu.sfbs:
			# Create the SFB tables
			for sfbNumber in dictKeys(SFB_table):
				if sfbNumber < 0 and not self.cpu.extendedInsnsEnabled():
					continue
				sfb = SFB_table[sfbNumber](self.cpu)
				self.cpu.sfbs[sfbNumber] = sfb

		if not self.cpu.sfcs:
			# Create the SFC tables
			for sfcNumber in dictKeys(SFC_table):
				if sfcNumber < 0 and not self.cpu.extendedInsnsEnabled():
					continue
				sfc = SFC_table[sfcNumber](self.cpu)
				self.cpu.sfcs[sfcNumber] = sfc

		# Build the data structures of code blocks.
		for block in self.cpu.allCodeBlocks():
			block.interface.buildDataStructure(self.cpu)

		# Translate DBs
		dbs = {}
		for rawDB in self.pendingRawDBs:
			dbNumber, sym = resolver.resolveBlockName({AwlDataType.TYPE_DB_X,
								   AwlDataType.TYPE_FB_X,
								   AwlDataType.TYPE_SFB_X},
								  rawDB.index)
			if dbNumber in dbs:
				raise AwlSimError("Multiple definitions of "\
					"DB %d." % dbNumber)
			rawDB.index = dbNumber
			db = translator.translateDB(rawDB)
			if dbNumber in self.cpu.dbs:
				self.cpu.dbs[dbNumber].destroySourceRef()
			dbs[dbNumber] = db
			self.cpu.dbs[dbNumber] = db
		self.pendingRawDBs = []

		# Resolve symbolic instructions and operators
		self.__resolveSymbols()

		# Do some finalizations
		self.__finalizeCodeBlocks()

		# Run some static sanity checks on the code
		self.staticSanityChecks()

	def getBlockInfos(self, getOBInfo = False, getFCInfo = False,
			  getFBInfo = False, getDBInfo = False):
		"""Returns a list of BlockInfo()."""

		blkInfos = []
		for block in itertools.chain(
				sorted(dictValues(self.cpu.obs) if getOBInfo else [],
				       key = lambda blk: blk.index),
				sorted(dictValues(self.cpu.fcs) if getFCInfo else [],
				       key = lambda blk: blk.index),
				sorted(dictValues(self.cpu.fbs) if getFBInfo else [],
				       key = lambda blk: blk.index),
				sorted(dictValues(self.cpu.dbs) if getDBInfo else [],
				       key = lambda blk: blk.index)):
			blkInfo = block.getBlockInfo()
			assert(blkInfo)
			blkInfos.append(blkInfo)
		return blkInfos

	def removeBlock(self, blockInfo, sanityChecks = True):
		"""Remove a block from the CPU.
		"""
		try:
			if blockInfo.blockType == BlockInfo.TYPE_OB:
				block = self.cpu.obs.pop(blockInfo.blockIndex)
				self.cpu.obTempPresetHandlers.pop(blockInfo.blockIndex)
			elif blockInfo.blockType == BlockInfo.TYPE_FC:
				block = self.cpu.fcs.pop(blockInfo.blockIndex)
			elif blockInfo.blockType == BlockInfo.TYPE_FB:
				block = self.cpu.fbs.pop(blockInfo.blockIndex)
			elif blockInfo.blockType == BlockInfo.TYPE_DB:
				block = self.cpu.dbs[blockInfo.blockIndex]
				if (block.permissions & DB.PERM_WRITE) == 0:
					raise AwlSimError("Remove block: Cannot delete "
						"write protected %s." % \
						blockInfo.blockName)
				block = self.cpu.dbs.pop(blockInfo.blockIndex)
			else:
				raise AwlSimError("Remove block: Unknown bock type %d." % \
					blockInfo.blockType)
			block.destroySourceRef()
		except KeyError as e:
			raise AwlSimError("Remove block: Block %s not found." % \
				blockInfo.blockName)
		if sanityChecks:
			# Re-run sanity checks to detect missing blocks.
			self.staticSanityChecks()

class S7CPU(object): #+cdef
	"STEP 7 CPU"

	def __init__(self):
		from awlsim.core.datatypes import AwlDataType

		self.__setAffinity()

		self.__fetchTypeMethods = self.__fetchTypeMethodsDict	#@nocy
		self.__storeTypeMethods = self.__storeTypeMethodsDict	#@nocy
		self.__callHelpers = self.__callHelpersDict		#@nocy
		self.__rawCallHelpers = self.__rawCallHelpersDict	#@nocy

		self.__clockMemByteOffset = None
		self.specs = S7CPUSpecs(self)
		self.conf = S7CPUConfig(self)
		self.prog = S7Prog(self)
		self.setCycleTimeLimit(5.0)
		self.setMaxCallStackDepth(256)
		self.setCycleExitCallback(None)
		self.setBlockExitCallback(None)
		self.setPostInsnCallback(None)
		self.setPeripheralReadCallback(None)
		self.setPeripheralWriteCallback(None)
		self.setScreenUpdateCallback(None)
		self.udts = {}
		self.dbs = {}
		self.obs = {}
		self.fcs = {}
		self.fbs = {}
		self.activeLStack = None
		self.reset()
		self.enableExtendedInsns(False)
		self.enableObTempPresets(False)
		self.__dateAndTimeWeekdayMap = AwlDataType.dateAndTimeWeekdayMap

	def __setAffinity(self):
		"""Set the host CPU affinity that what is set via AWLSIM_AFFINITY
		environment variable.
		"""
		affinity = AwlSimEnv.getAffinity()
		if affinity:
			if hasattr(os, "sched_setaffinity"):
				try:
					os.sched_setaffinity(0, affinity)
				except (OSError, ValueError) as e:
					raise AwlSimError("Failed to set host CPU "
						"affinity to %s: %s" % (
						affinity, str(e)))
			else:
				printError("Cannot set CPU affinity "
					   "on this version of Python. "
					   "os.sched_setaffinity is not available.")

	def getMnemonics(self):
		return self.conf.getMnemonics()

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

	def setRunTimeLimit(self, timeoutSeconds=-1.0):
		self.__runtimeLimit = timeoutSeconds if timeoutSeconds >= 0.0 else -1.0

	def setMaxCallStackDepth(self, newMaxDepth):
		self.maxCallStackDepth = min(max(int(newMaxDepth), 1), 0xFFFFFFFF)

	# Returns all user defined code blocks (OBs, FBs, FCs)
	def allUserCodeBlocks(self):
		for block in itertools.chain(dictValues(self.obs),
					     dictValues(self.fbs),
					     dictValues(self.fcs)):
			yield block

	# Returns all system code blocks (SFBs, SFCs)
	def allSystemCodeBlocks(self):
		for block in itertools.chain(dictValues(self.sfbs),
					     dictValues(self.sfcs)):
			yield block

	# Returns all user defined code blocks (OBs, FBs, FCs, SFBs, SFCs)
	def allCodeBlocks(self):
		for block in itertools.chain(self.allUserCodeBlocks(),
					     self.allSystemCodeBlocks()):
			yield block

	def allCallInsns(self, block):
		from awlsim.core.datatypes import AwlDataType

		resolver = AwlSymResolver(self)

		for insn in block.insns:
			if insn.insnType != AwlInsn.TYPE_CALL:
				continue

			# Get the DB block, if any.
			if len(insn.ops) == 1:
				dataBlock = None
			elif len(insn.ops) == 2:
				dataBlockOp = insn.ops[1]
				if dataBlockOp.operType == AwlOperatorTypes.SYMBOLIC:
					blockIndex, symbol = resolver.resolveBlockName(
							{AwlDataType.TYPE_FB_X,
							 AwlDataType.TYPE_SFB_X},
							dataBlockOp.offset.identChain.getString())
					dataBlockOp = symbol.operator.dup()
				dataBlockIndex = dataBlockOp.offset.byteOffset
				try:
					if dataBlockOp.operType == AwlOperatorTypes.BLKREF_DB:
						dataBlock = self.dbs[dataBlockIndex]
					else:
						raise AwlSimError("Data block operand "
							"in CALL is not a DB.",
							insn=insn)
				except KeyError as e:
					raise AwlSimError("Data block '%s' referenced "
						"in CALL does not exist." %\
						str(dataBlockOp),
						insn=insn)

			# Get the code block, if any.
			codeBlockOp = insn.ops[0]
			if codeBlockOp.operType == AwlOperatorTypes.SYMBOLIC:
				blockIndex, symbol = resolver.resolveBlockName(
						{AwlDataType.TYPE_FC_X,
						 AwlDataType.TYPE_FB_X,
						 AwlDataType.TYPE_SFC_X,
						 AwlDataType.TYPE_SFB_X},
						codeBlockOp.offset.identChain.getString())
				codeBlockOp = symbol.operator.dup()
			elif codeBlockOp.operType == AwlOperatorTypes.NAMED_LOCAL:
				codeBlockOp = resolver.resolveNamedLocal(block, insn, codeBlockOp)

			if codeBlockOp.operType in {AwlOperatorTypes.MULTI_FB,
						    AwlOperatorTypes.MULTI_SFB}:
				codeBlockIndex = codeBlockOp.offset.fbNumber
			else:
				codeBlockIndex = codeBlockOp.offset.byteOffset
			try:
				if codeBlockOp.operType == AwlOperatorTypes.BLKREF_FC:
					codeBlock = self.fcs[codeBlockIndex]
				elif codeBlockOp.operType in {AwlOperatorTypes.BLKREF_FB,
							      AwlOperatorTypes.MULTI_FB}:
					codeBlock = self.fbs[codeBlockIndex]
				elif codeBlockOp.operType == AwlOperatorTypes.BLKREF_SFC:
					codeBlock = self.sfcs[codeBlockIndex]
				elif codeBlockOp.operType in {AwlOperatorTypes.BLKREF_SFB,
							      AwlOperatorTypes.MULTI_SFB}:
					codeBlock = self.sfbs[codeBlockIndex]
				else:
					raise AwlSimError("Code block operand "
						"in CALL is not a valid code block "
						"(FB, FC, SFB or SFC).",
						insn=insn)
			except KeyError as e:
				raise AwlSimError("Code block '%s' referenced in "
					"CALL does not exist." %\
					str(codeBlockOp),
					insn=insn)

			yield insn, codeBlock, dataBlock

	def build(self):
		"""Translate the loaded sources into their executable forms.
		"""
		self.prog.build()
		self.reallocate(force=True)

	def load(self, parseTree, rebuild = False, sourceManager = None):
		for rawDB in dictValues(parseTree.dbs):
			rawDB.setSourceRef(sourceManager)
			self.prog.addRawDB(rawDB)
		for rawFB in dictValues(parseTree.fbs):
			rawFB.setSourceRef(sourceManager)
			self.prog.addRawFB(rawFB)
		for rawFC in dictValues(parseTree.fcs):
			rawFC.setSourceRef(sourceManager)
			self.prog.addRawFC(rawFC)
		for rawOB in dictValues(parseTree.obs):
			rawOB.setSourceRef(sourceManager)
			self.prog.addRawOB(rawOB)
		for rawUDT in dictValues(parseTree.udts):
			rawUDT.setSourceRef(sourceManager)
			self.prog.addRawUDT(rawUDT)
		if rebuild:
			self.build()

	def loadLibraryBlock(self, libSelection, rebuild = False):
		self.prog.addLibrarySelection(libSelection)
		if rebuild:
			self.build()

	@property
	def symbolTable(self):
		return self.prog.symbolTable

	def loadSymbolTable(self, symbolTable, rebuild = False):
		self.prog.loadSymbolTable(symbolTable)
		if rebuild:
			self.build()

	def getBlockInfos(self, getOBInfo = False, getFCInfo = False,
			  getFBInfo = False, getDBInfo = False):
		"""Returns a list of BlockInfo()."""
		return self.prog.getBlockInfos(getOBInfo = getOBInfo,
					       getFCInfo = getFCInfo,
					       getFBInfo = getFBInfo,
					       getDBInfo = getDBInfo)

	def staticSanityChecks(self):
		"""Run static error checks."""
		self.prog.staticSanityChecks()

	def removeBlock(self, blockInfo, sanityChecks = True):
		"""Remove a block from the CPU."""
		self.prog.removeBlock(blockInfo, sanityChecks)

	def reallocate(self, force=False):
#@cy		cdef OB ob

		if force or (self.specs.nrAccus == 4) != self.is4accu:
			self.accu1, self.accu2, self.accu3, self.accu4 =\
				Accu(), Accu(), Accu(), Accu()
			self.is4accu = (self.specs.nrAccus == 4)
		if force or self.specs.nrTimers != len(self.timers):
			self.timers = [ Timer(self, i)
					for i in range(self.specs.nrTimers) ]
		if force or self.specs.nrCounters != len(self.counters):
			self.counters = [ Counter(self, i)
					  for i in range(self.specs.nrCounters) ]
		if force or self.specs.nrFlags != len(self.flags):
			self.flags = AwlMemory(self.specs.nrFlags)
		if force or self.specs.nrInputs != len(self.inputs):
			self.inputs = AwlMemory(self.specs.nrInputs)
		if force or self.specs.nrOutputs != len(self.outputs):
			self.outputs = AwlMemory(self.specs.nrOutputs)
		for ob in dictValues(self.obs):
			if force or self.specs.nrLocalbytes * 8 != ob.lstack.maxAllocBits:
				ob.lstack.resize(self.specs.nrLocalbytes)

	def reset(self):
		self.prog.reset()
		for block in itertools.chain(dictValues(self.udts),
					     dictValues(self.dbs),
					     dictValues(self.obs),
					     dictValues(self.fcs),
					     dictValues(self.fbs)):
			block.destroySourceRef()
		self.udts = {} # UDTs
		self.dbs = { # DBs
			0 : DB(0, permissions = 0), # read/write-protected system-DB
		}
		self.obs = { # OBs
			1 : OB([], 1), # Empty OB1
		}
		self.obTempPresetHandlers = {
			# OB TEMP-preset handlers
			1 : OBTempPresets_table[1](self), # Default OB1 handler
			# This table is extended as OBs are loaded.
		}
		self.fcs = {} # User FCs
		self.fbs = {} # User FBs
		self.sfcs = {} # System SFCs
		self.sfbs = {} # System SFBs

		self.is4accu = False
		self.reallocate(force=True)
		self.ar1 = Addressregister()
		self.ar2 = Addressregister()
		self.db0 = self.dbs[0]
		self.dbRegister = self.db0
		self.diRegister = self.db0
		self.callStackTop = None
		self.callStackDepth = 0
		self.setMcrActive(False)
		self.mcrStack = [ ]
		self.statusWord = S7StatusWord()
		self.__clockMemByteOffset = None
		self.setRunTimeLimit()

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
		self.__avgCycleTimes = deque()
		self.__avgCycleTimesCount = 0
		self.__avgCycleTimesSum = 0.0
		self.__speedMeasureStartTime = 0
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0

		self.initializeTimestamp()

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
		if cb:
			self.cbPeripheralRead = cb
			self.cbPeripheralReadData = data
		else:
			self.cbPeripheralRead =\
				lambda data, bitWidth, byteOffset: bytearray()
			self.cbPeripheralReadData = None

	def setPeripheralWriteCallback(self, cb, data=None):
		if cb:
			self.cbPeripheralWrite = cb
			self.cbPeripheralWriteData = data
		else:
			self.cbPeripheralWrite =\
				lambda data, bitWidth, byteOffset, value: False
			self.cbPeripheralWriteData = None

	def setScreenUpdateCallback(self, cb, data=None):
		self.cbScreenUpdate = cb
		self.cbScreenUpdateData = data

	def requestScreenUpdate(self):
		if self.cbScreenUpdate is not None:
			self.cbScreenUpdate(self.cbScreenUpdateData)

	def __runOB(self, block): #@nocy
#@cy	cdef __runOB(self, OB block):
#@cy		cdef AwlInsn insn
#@cy		cdef CallStackElem cse
#@cy		cdef CallStackElem exitCse
#@cy		cdef LStackAllocator activeLStack
#@cy		cdef uint32_t insnCount

		# Update timekeeping
		self.updateTimestamp()
		self.cycleStartTime = self.now

		# Initialize the L-stack. A previous block execution might
		# have exited with an exception and left allocation behind.
		# Clear all allocated bits.
		self.activeLStack = activeLStack = block.lstack
		activeLStack.reset()

		# Initialize CPU state
		self.dbRegister = self.diRegister = self.db0
		self.accu1.reset()
		self.accu2.reset()
		self.accu3.reset()
		self.accu4.reset()
		self.ar1.reset()
		self.ar2.reset()
		self.statusWord.reset()

		self.callStackTop, self.callStackDepth = None, 1
		cse = self.callStackTop = make_CallStackElem(self, block, None, None, (), True)

		if self.__obTempPresetsEnabled:
			# Populate the TEMP region
			self.obTempPresetHandlers[block.index].generate(activeLStack.memory.dataBytes)

		# Run the user program cycle
		while cse is not None:
			while cse.ip < cse.nrInsns:
				insn, self.relativeJump = cse.insns[cse.ip], 1
				insn.run()
				if self.cbPostInsn is not None:
					self.cbPostInsn(cse, self.cbPostInsnData)
				cse.ip += self.relativeJump
				cse = self.callStackTop
				self.__insnCount = insnCount = (self.__insnCount + 1) & 0x3FFFFFFF
				if not (insnCount & 0x3F):
					self.updateTimestamp()
					if self.now - self.cycleStartTime > self.cycleTimeLimit:
						self.__cycleTimeExceed()
			if self.cbBlockExit is not None:
				self.cbBlockExit(self.cbBlockExitData)
			cse, exitCse = cse.prevCse, cse
			self.callStackTop = cse
			self.callStackDepth -= 1
			exitCse.handleBlockExit()
		assert(self.callStackDepth == 0) #@nocy

	def initClockMemState(self, force=False):
		"""Reset/initialize the clock memory byte state.
		"""
		if self.conf.clockMemByte >= 0:
			clockMemByteOffset = make_AwlOffset(self.conf.clockMemByte, 0)
		else:
			clockMemByteOffset = None
		if force:
			resetCount = True
		else:
			resetCount = clockMemByteOffset != self.__clockMemByteOffset

		self.__clockMemByteOffset = None
		self.updateTimestamp()
		self.__clockMemByteOffset = clockMemByteOffset

		if resetCount:
			self.__nextClockMemTime = self.now + 0.05
			self.__clockMemCount = 0
			self.__clockMemCountLCM = math_lcm(2, 4, 5, 8, 10, 16, 20)
			if self.__clockMemByteOffset is not None:
				self.flags.store(self.__clockMemByteOffset, 8, 0)

	# Run startup code
	def startup(self):
		# Build (translate) the blocks, if not already done so.
		self.build()

		self.initializeTimestamp()
		self.__speedMeasureStartTime = self.now
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0

		self.initClockMemState(force=True)

		# Run startup OB
		if 102 in self.obs and self.is4accu:
			# Cold start.
			# This is only done on 4xx-series CPUs.
			self.__runOB(self.obs[102])
		elif 100 in self.obs:
			# Warm start.
			# This really is a cold start, because remanent
			# resources were reset. However we could not execute
			# OB 102, so this is a fallback.
			# This is not 100% compliant with real CPUs, but it probably
			# is sane behavior.
			self.__runOB(self.obs[100])

	# Run one cycle of the user program
	def runCycle(self): #+cdef
#@cy		cdef double elapsedTime
#@cy		cdef double cycleTime
#@cy		cdef double avgCycleTime
#@cy		cdef double avgCycleTimesSum
#@cy		cdef double firstSample
#@cy		cdef double avgInsnPerCycle
#@cy		cdef double avgTimePerInsn
#@cy		cdef uint32_t cycleCount
#@cy		cdef uint32_t insnCount

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

			# Get the average cycle time over the measurement period.
			cycleTime = elapsedTime / cycleCount

			# Calculate and store maximum and minimum cycle time.
			self.maxCycleTime = max(self.maxCycleTime, cycleTime)
			self.minCycleTime = min(self.minCycleTime, cycleTime)

			# Calculate and store moving average cycle time.
			avgCycleTimes = self.__avgCycleTimes
			avgCycleTimes.append(cycleTime)
			avgCycleTimesSum = self.__avgCycleTimesSum
			if self.__avgCycleTimesCount >= 3: # 3 samples
				firstSample = avgCycleTimes.popleft()
				avgCycleTimesSum -= firstSample
				avgCycleTimesSum += cycleTime
				self.avgCycleTime = avgCycleTime = avgCycleTimesSum / 3.0 # 3 samples
			else:
				avgCycleTimesSum += cycleTime
				self.__avgCycleTimesCount += 1
				self.avgCycleTime = avgCycleTime = 0.0
			self.__avgCycleTimesSum = avgCycleTimesSum

			# Calculate instruction statistics.
			self.avgInsnPerCycle = avgInsnPerCycle = insnCount / cycleCount
			if avgInsnPerCycle > 0.0:
				avgTimePerInsn = avgCycleTime / avgInsnPerCycle
				if avgTimePerInsn > 0.0:
					self.insnPerSecond = 1.0 / avgTimePerInsn
				else:
					self.insnPerSecond = 0.0
			else:
				self.insnPerSecond = 0.0

			# Reset the counters
			self.__speedMeasureStartTime = self.now
			self.__speedMeasureStartInsnCount = self.__insnCount
			self.__speedMeasureStartCycleCount = self.__cycleCount

		# Call the cycle exit callback, if any.
		if self.cbCycleExit is not None:
			self.cbCycleExit(self.cbCycleExitData)

	# Returns 'self.now' as 31 bit millisecond representation.
	# That is data type 'TIME'.
	# The returned value will always be positive and wrap
	# from 0x7FFFFFFF to 0.
	@property
	def now_TIME(self):
		return int(self.now * 1000.0) & 0x7FFFFFFF

	# Initialize time stamp.
	def initializeTimestamp(self):
		# Initialize the time stamp so that it will
		# overflow 31 bit millisecond count within
		# 100 milliseconds after startup.
		# An 31 bit overflow happens after 0x7FFFFFFF ms,
		# which is 2147483647 ms, which is 2147483.647 s.
		# Create an offset to 'self.now' that is added every
		# time 'self.now' is updated.
		now = perf_monotonic_time()
		self.__nowOffset = -(now) + (2147483.647 - 0.1)
		self.now = now = now + self.__nowOffset
		self.startupTime = now
		self.updateTimestamp()

	# updateTimestamp() updates self.now, which is a
	# floating point count of seconds.
	def updateTimestamp(self, _getTime=perf_monotonic_time): #@nocy
#@cy	cdef updateTimestamp(self):
#@cy		cdef uint32_t value
#@cy		cdef uint32_t count
#@cy		cdef double now

		# Update the system time
		now = _getTime() #@nocy
#@cy		now = perf_monotonic_time()
		self.now = now = now + self.__nowOffset

		# Update the clock memory byte
		if self.__clockMemByteOffset is not None and\
		   now >= self.__nextClockMemTime:
			try:
				self.__nextClockMemTime += 0.05
				value = self.flags.fetch(self.__clockMemByteOffset, 8)
				value ^= 0x01 # 0.1s period
				count = self.__clockMemCount + 1
				self.__clockMemCount = count
				if not count % 2:
					value ^= 0x02 # 0.2s period
				if not count % 4:
					value ^= 0x04 # 0.4s period
				if not count % 5:
					value ^= 0x08 # 0.5s period
				if not count % 8:
					value ^= 0x10 # 0.8s period
				if not count % 10:
					value ^= 0x20 # 1.0s period
				if not count % 16:
					value ^= 0x40 # 1.6s period
				if not count % 20:
					value ^= 0x80 # 2.0s period
				if count >= self.__clockMemCountLCM:
					self.__clockMemCount = 0
				self.flags.store(self.__clockMemByteOffset, 8, value)
			except AwlSimError as e:
				raise AwlSimError("Failed to generate clock "
					"memory signal:\n" + str(e) +\
					"\n\nThe configured clock memory byte "
					"address might be invalid." )

		# Check whether the runtime timeout exceeded
		if self.__runtimeLimit >= 0.0:
			if now - self.startupTime >= self.__runtimeLimit:
				self.__runTimeExceed()

	def __cycleTimeExceed(self): #+cdef
		raise AwlSimError("Cycle time exceed %.3f seconds" % (
				  self.cycleTimeLimit))

	def __runTimeExceed(self): #+cdef
		raise MaintenanceRequest(MaintenanceRequest.TYPE_RTTIMEOUT,
					 "CPU runtime timeout")

	# Make a DATE_AND_TIME for the current wall-time and
	# store it in byteArray, which is a bytearray or compatible.
	# If byteArray is smaller than 8 bytes, an IndexError is raised.
	def makeCurrentDateAndTime(self, byteArray, offset): #@nocy
#@cy	cdef makeCurrentDateAndTime(self, bytearray byteArray, uint32_t offset):
#@cy		cdef uint32_t year
#@cy		cdef uint32_t month
#@cy		cdef uint32_t day
#@cy		cdef uint32_t hour
#@cy		cdef uint32_t minute
#@cy		cdef uint32_t second
#@cy		cdef uint32_t msec

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

	def labelIdxToRelJump(self, labelIndex): #@nocy
#@cy	cdef int32_t labelIdxToRelJump(self, uint32_t labelIndex) except? 0x7FFFFFFF:
#@cy		cdef CallStackElem cse

		# Translate a label index into a relative IP offset.
		cse = self.callStackTop
		label = cse.block.labels[labelIndex]
		return label.insn.ip - cse.ip

	def jumpToLabel(self, labelIndex): #@nocy
#@cy	cdef jumpToLabel(self, uint32_t labelIndex):
		self.relativeJump = self.labelIdxToRelJump(labelIndex)

	def jumpRelative(self, insnOffset): #@nocy
#@cy	cdef jumpRelative(self, int32_t insnOffset):
		self.relativeJump = insnOffset

	def __call_FC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_FC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
		fc = self.fcs[blockOper.offset.byteOffset]
		return make_CallStackElem(self, fc, None, None, parameters, False)

	def __call_RAW_FC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_FC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
		fc = self.fcs[blockOper.offset.byteOffset]
		return make_CallStackElem(self, fc, None, None, (), True)

	def __call_FB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_FB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CallStackElem cse
#@cy		cdef DB db

		fb = self.fbs[blockOper.offset.byteOffset]
		db = self.dbs[dbOper.offset.byteOffset]
		cse = make_CallStackElem(self, fb, db, make_AwlOffset(0, 0), parameters, False)
		self.dbRegister, self.diRegister = self.diRegister, db
		return cse

	def __call_RAW_FB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_FB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
		fb = self.fbs[blockOper.offset.byteOffset]
		return make_CallStackElem(self, fb, self.diRegister, None, (), True)

	def __call_SFC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_SFC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
		sfc = self.sfcs[blockOper.offset.byteOffset]
		return make_CallStackElem(self, sfc, None, None, parameters, False)

	def __call_RAW_SFC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_SFC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
		sfc = self.sfcs[blockOper.offset.byteOffset]
		return make_CallStackElem(self, sfc, None, None, (), True)

	def __call_SFB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_SFB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CallStackElem cse
#@cy		cdef DB db

		sfb = self.sfbs[blockOper.offset.byteOffset]
		db = self.dbs[dbOper.offset.byteOffset]
		cse = make_CallStackElem(self, sfb, db, make_AwlOffset(0, 0), parameters, False)
		self.dbRegister, self.diRegister = self.diRegister, db
		return cse

	def __call_RAW_SFB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_SFB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
		sfb = self.sfbs[blockOper.offset.byteOffset]
		return make_CallStackElem(self, sfb, self.diRegister, None, (), True)

	def __call_INDIRECT(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_INDIRECT(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):

		blockOper = blockOper.resolve()

#@cy		if blockOper.operType == AwlOperatorTypes.BLKREF_FC:
#@cy			return self.__call_RAW_FC(blockOper, dbOper, parameters)
#@cy		elif blockOper.operType == AwlOperatorTypes.BLKREF_FB:
#@cy			return self.__call_RAW_FB(blockOper, dbOper, parameters)
#@cy		elif blockOper.operType == AwlOperatorTypes.BLKREF_SFC:
#@cy			return self.__call_RAW_SFC(blockOper, dbOper, parameters)
#@cy		elif blockOper.operType == AwlOperatorTypes.BLKREF_SFB:
#@cy			return self.__call_RAW_SFB(blockOper, dbOper, parameters)
#@cy		else:
#@cy			raise AwlSimError("Invalid CALL operand")

		callHelper = self.__rawCallHelpers[blockOper.operType]			#@nocy
		try:									#@nocy
			return callHelper(self, blockOper, dbOper, parameters)		#@nocy
		except KeyError as e:							#@nocy
			raise AwlSimError("Code block %d not found in indirect call" %(	#@nocy
					  blockOper.offset.byteOffset))			#@nocy

	def __call_MULTI_FB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_MULTI_FB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
		fb = self.fbs[blockOper.offset.fbNumber]
		base = make_AwlOffset_fromPointerValue(self.ar2.get()) + blockOper.offset
		cse = make_CallStackElem(self, fb, self.diRegister, base, parameters, False)
		self.dbRegister = self.diRegister
		return cse

	def __call_MULTI_SFB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_MULTI_SFB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef AwlOffset base
#@cy		cdef CallStackElem cse

		sfb = self.sfbs[blockOper.offset.fbNumber]
		base = make_AwlOffset_fromPointerValue(self.ar2.get()) + blockOper.offset
		cse = make_CallStackElem(self, sfb, self.diRegister, base, parameters, False)
		self.dbRegister = self.diRegister
		return cse

	__callHelpersDict = {					#@nocy
		AwlOperatorTypes.BLKREF_FC	: __call_FC,		#@nocy
		AwlOperatorTypes.BLKREF_FB	: __call_FB,		#@nocy
		AwlOperatorTypes.BLKREF_SFC	: __call_SFC,		#@nocy
		AwlOperatorTypes.BLKREF_SFB	: __call_SFB,		#@nocy
		AwlOperatorTypes.MULTI_FB	: __call_MULTI_FB,	#@nocy
		AwlOperatorTypes.MULTI_SFB	: __call_MULTI_SFB,	#@nocy
	}							#@nocy

	__rawCallHelpersDict = {				#@nocy
		AwlOperatorTypes.BLKREF_FC	: __call_RAW_FC,	#@nocy
		AwlOperatorTypes.BLKREF_FB	: __call_RAW_FB,	#@nocy
		AwlOperatorTypes.BLKREF_SFC	: __call_RAW_SFC,	#@nocy
		AwlOperatorTypes.BLKREF_SFB	: __call_RAW_SFB,	#@nocy
		AwlOperatorTypes.INDIRECT	: __call_INDIRECT,	#@nocy
	}							#@nocy

	def run_CALL(self, blockOper, dbOper=None, parameters=(), raw=False): #@nocy
#@cy	cdef run_CALL(self, AwlOperator blockOper, AwlOperator dbOper=None,
#@cy		     tuple parameters=(), _Bool raw=False):
#@cy		cdef CallStackElem newCse
#@cy		cdef uint32_t callStackDepth

		callStackDepth = self.callStackDepth
		if callStackDepth >= self.maxCallStackDepth:
			raise AwlSimError("Maximum CALL stack depth of %d CALLs exceed." % (
				self.maxCallStackDepth))

#@cy		if raw:
#@cy			if blockOper.operType == AwlOperatorTypes.BLKREF_FC:
#@cy				newCse = self.__call_RAW_FC(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.BLKREF_FB:
#@cy				newCse = self.__call_RAW_FB(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.BLKREF_SFC:
#@cy				newCse = self.__call_RAW_SFC(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.BLKREF_SFB:
#@cy				newCse = self.__call_RAW_SFB(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.INDIRECT:
#@cy				newCse = self.__call_INDIRECT(blockOper, dbOper, parameters)
#@cy			else:
#@cy				raise AwlSimError("Invalid CALL operand")
#@cy		else:
#@cy			if blockOper.operType == AwlOperatorTypes.BLKREF_FC:
#@cy				newCse = self.__call_FC(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.BLKREF_FB:
#@cy				newCse = self.__call_FB(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.BLKREF_SFC:
#@cy				newCse = self.__call_SFC(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.BLKREF_SFB:
#@cy				newCse = self.__call_SFB(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.MULTI_FB:
#@cy				newCse = self.__call_MULTI_FB(blockOper, dbOper, parameters)
#@cy			elif blockOper.operType == AwlOperatorTypes.MULTI_SFB:
#@cy				newCse = self.__call_MULTI_SFB(blockOper, dbOper, parameters)
#@cy			else:
#@cy				raise AwlSimError("Invalid CALL operand")

		try:									#@nocy
			if raw:								#@nocy
				callHelper = self.__rawCallHelpers[blockOper.operType]	#@nocy
			else:								#@nocy
				callHelper = self.__callHelpers[blockOper.operType]	#@nocy
		except KeyError:							#@nocy
			raise AwlSimError("Invalid CALL operand")			#@nocy
		newCse = callHelper(self, blockOper, dbOper, parameters)		#@nocy

		newCse.prevCse = self.callStackTop
		self.callStackTop, self.callStackDepth = newCse, callStackDepth + 1

	def run_BE(self): #+cdef
#@cy		cdef S7StatusWord s
#@cy		cdef CallStackElem cse

		s = self.statusWord
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
		# Jump beyond end of block
		cse = self.callStackTop
		self.relativeJump = len(cse.insns) - cse.ip

	def openDB(self, dbNumber, openDI): #@nocy
#@cy	cdef openDB(self, int32_t dbNumber, _Bool openDI):
#@cy		cdef DB db

		if dbNumber <= 0:
			if openDI:
				self.diRegister = self.db0
			else:
				self.dbRegister = self.db0
		else:
			try:
				if openDI:
					self.diRegister = self.dbs[dbNumber]
				else:
					self.dbRegister = self.dbs[dbNumber]
			except KeyError:
				raise AwlSimError("Datablock %i does not exist" % dbNumber)

	def run_AUF(self, dbOper): #@nocy
#@cy	cdef run_AUF(self, AwlOperator dbOper):
#@cy		cdef _Bool openDI
#@cy		cdef uint32_t operType

		dbOper = dbOper.resolve()

		operType = dbOper.operType
		if operType == AwlOperatorTypes.BLKREF_DB:
			openDI = False
		elif operType == AwlOperatorTypes.BLKREF_DI:
			openDI = True
		else:
			raise AwlSimError("Invalid DB reference in AUF")

		self.openDB(dbOper.offset.byteOffset, openDI)

	def run_TDB(self): #+cdef
		# Swap global and instance DB
		self.diRegister, self.dbRegister = self.dbRegister, self.diRegister

	def getAccu(self, index): #@nocy
#@cy	cdef Accu getAccu(self, uint32_t index):
		if index < 1 or index > self.specs.nrAccus:
			raise AwlSimError("Invalid ACCU offset")
		return (self.accu1, self.accu2,
			self.accu3, self.accu4)[index - 1]

	def getAR(self, index): #@nocy
#@cy	cdef Addressregister getAR(self, uint32_t index):
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

	def getConf(self):
		return self.conf

	def setMcrActive(self, active): #@nocy
#@cy	cdef void setMcrActive(self, _Bool active):
		self.mcrActive = active

	def mcrIsOn(self): #@nocy
#@cy	cdef _Bool mcrIsOn(self):
		return (not self.mcrActive or all(self.mcrStack))

	def mcrStackAppend(self, statusWord): #@nocy
#@cy	cdef mcrStackAppend(self, S7StatusWord statusWord):
		self.mcrStack.append(statusWord.VKE)
		if len(self.mcrStack) > 8:
			raise AwlSimError("MCR stack overflow")

	def mcrStackPop(self): #+cdef
		try:
			self.mcrStack.pop()
		except IndexError:
			raise AwlSimError("MCR stack underflow")

	def parenStackAppend(self, insnType, statusWord): #@nocy
#@cy	cdef parenStackAppend(self, uint32_t insnType, S7StatusWord statusWord):
#@cy		cdef CallStackElem cse

		cse = self.callStackTop
		cse.parenStack.append(ParenStackElem(self, insnType, statusWord))
		if len(cse.parenStack) > 7:
			raise AwlSimError("Parenthesis stack overflow")

	def __translateFCNamedLocalOper(self, operator, store): #@nocy
#@cy	cdef AwlOperator __translateFCNamedLocalOper(self, AwlOperator operator, _Bool store):
#@cy		cdef uint32_t pointer
#@cy		cdef uint32_t opType
#@cy		cdef uint32_t dbNr
#@cy		cdef AwlOperator interfOp
#@cy		cdef AwlOperator dbPtrOp
#@cy		cdef AwlOperator finalOp
#@cy		cdef AwlOffset subOffset

		# Translate an 'operator' to a named local FC parameter.
		# The returned operator is an operator to the actual data.
		interfOp = self.callStackTop.getInterfIdxOper(operator.interfaceIndex).resolve(store)
		if operator.compound:
			# This is a named local variable with compound data type.
			# The operator (interfOp) points to a DB-pointer in VL.
			# First fetch the DB pointer values from VL.
			dbPtrOp = interfOp.dup()
			dbPtrOp.width = 16
			dbNr = self.fetch(dbPtrOp, AwlOperatorWidths.WIDTH_MASK_16)
			dbPtrOp.offset.byteOffset += 2
			dbPtrOp.width = 32
			pointer = self.fetch(dbPtrOp, AwlOperatorWidths.WIDTH_MASK_32)
			# Open the DB pointed to by the DB-ptr.
			# (This is ok, if dbNr is 0, too)
			self.openDB(dbNr, False)
			# Make an operator from the DB-ptr.
			try:
				opType = AwlIndirectOpConst.area2optype_fetch[
						pointer & PointerConst.AREA_MASK_S]
			except KeyError:
				raise AwlSimError("Corrupt DB pointer in compound "
					"data type FC variable detected "
					"(invalid area).", insn = operator.insn)
			finalOp = make_AwlOperator(opType, operator.width,
					      make_AwlOffset_fromPointerValue(pointer),
					      operator.insn)
		else:
			# Not a compound data type.
			# The translated operand already points to the variable.
			finalOp = interfOp.dup()
			finalOp.width = operator.width
		# Add possible sub-offsets (ARRAY, STRUCT) to the offset.
		subOffset = operator.offset.subOffset
		if subOffset is not None:
			finalOp.offset += subOffset
		# Reparent the operator to the originating instruction.
		# This is especially important for T and Z fetches due
		# to their semantic dependency on the instruction being used.
		finalOp.insn = operator.insn
		return finalOp

	# Fetch a range in the 'output' memory area.
	# 'byteOffset' is the byte offset into the output area.
	# 'byteCount' is the number if bytes to fetch.
	# Returns a bytearray.
	# This raises an AwlSimError, if the access if out of range.
	def fetchOutputRange(self, byteOffset, byteCount): #@nocy
#@cy	cpdef bytearray fetchOutputRange(self, uint32_t byteOffset, uint32_t byteCount):
		if byteOffset + byteCount > len(self.outputs): #@nocy
#@cy		if <uint64_t>byteOffset + <uint64_t>byteCount > <uint64_t>len(self.outputs):
			raise AwlSimError("Fetch from output process image region "
				"is out of range "
				"(imageSize=%d, fetchOffset=%d, fetchSize=%d)." % (
				len(self.outputs), byteOffset, byteCount))
		return self.outputs.dataBytes[byteOffset : byteOffset + byteCount]

	# Fetch a range in the 'input' memory area.
	# 'byteOffset' is the byte offset into the input area.
	# 'byteCount' is the number if bytes to fetch.
	# Returns a bytearray.
	# This raises an AwlSimError, if the access if out of range.
	def fetchInputRange(self, byteOffset, byteCount): #@nocy
#@cy	cpdef bytearray fetchInputRange(self, uint32_t byteOffset, uint32_t byteCount):
		if byteOffset + byteCount > len(self.inputs): #@nocy
#@cy		if <uint64_t>byteOffset + <uint64_t>byteCount > <uint64_t>len(self.inputs):
			raise AwlSimError("Fetch from input process image region "
				"is out of range "
				"(imageSize=%d, fetchOffset=%d, fetchSize=%d)." % (
				len(self.inputs), byteOffset, byteCount))
		return self.inputs.dataBytes[byteOffset : byteOffset + byteCount]

	# Store a range in the 'input' memory area.
	# 'byteOffset' is the byte offset into the input area.
	# 'data' is a bytearray.
	# This raises an AwlSimError, if the access if out of range.
	def storeInputRange(self, byteOffset, data): #@nocy
#@cy	cpdef storeInputRange(self, uint32_t byteOffset, bytearray data):
#@cy		cdef uint32_t dataLen

		dataLen = len(data)
		if byteOffset + dataLen > len(self.inputs): #@nocy
#@cy		if <uint64_t>byteOffset + <uint64_t>dataLen > <uint64_t>len(self.inputs):
			raise AwlSimError("Store to input process image region "
				"is out of range "
				"(imageSize=%d, storeOffset=%d, storeSize=%d)." % (
				len(self.inputs), byteOffset, dataLen))
		self.inputs.dataBytes[byteOffset : byteOffset + dataLen] = data

	def fetch(self, operator, allowedWidths):					#@nocy
		try:									#@nocy
			fetchMethod = self.__fetchTypeMethods[operator.operType]	#@nocy
		except KeyError:							#@nocy
			self.__invalidFetch(operator)					#@nocy
		return fetchMethod(self, operator, allowedWidths)			#@nocy

#@cy	cpdef object fetch(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef uint32_t operType
#@cy
#@cy		operType = operator.operType
#@cy		if operType == AwlOperatorTypes.IMM:
#@cy			return self.__fetchIMM(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_REAL:
#@cy			return self.__fetchIMM(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_S5T:
#@cy			return self.__fetchIMM(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_TIME:
#@cy			return self.__fetchIMM(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_DATE:
#@cy			return self.__fetchIMM(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_DT:
#@cy			return self.__fetchIMM_DT(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_TOD:
#@cy			return self.__fetchIMM(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_PTR:
#@cy			return self.__fetchIMM_PTR(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.IMM_STR:
#@cy			return self.__fetchIMM_STR(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_E:
#@cy			return self.__fetchE(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_A:
#@cy			return self.__fetchA(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_M:
#@cy			return self.__fetchM(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_L:
#@cy			return self.__fetchL(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_VL:
#@cy			return self.__fetchVL(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DB:
#@cy			return self.__fetchDB(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DI:
#@cy			return self.__fetchDI(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_T:
#@cy			return self.__fetchT(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_Z:
#@cy			return self.__fetchZ(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_PE:
#@cy			return self.__fetchPE(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DBLG:
#@cy			return self.__fetchDBLG(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DBNO:
#@cy			return self.__fetchDBNO(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DILG:
#@cy			return self.__fetchDILG(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DINO:
#@cy			return self.__fetchDINO(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_AR2:
#@cy			return self.__fetchAR2(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW:
#@cy			return self.__fetchSTW(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW_Z:
#@cy			return self.__fetchSTW_Z(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW_NZ:
#@cy			return self.__fetchSTW_NZ(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW_POS:
#@cy			return self.__fetchSTW_POS(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW_NEG:
#@cy			return self.__fetchSTW_NEG(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW_POSZ:
#@cy			return self.__fetchSTW_POSZ(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW_NEGZ:
#@cy			return self.__fetchSTW_NEGZ(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW_UO:
#@cy			return self.__fetchSTW_UO(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.NAMED_LOCAL:
#@cy			return self.__fetchNAMED_LOCAL(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.NAMED_LOCAL_PTR:
#@cy			return self.__fetchNAMED_LOCAL_PTR(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.NAMED_DBVAR:
#@cy			return self.__fetchNAMED_DBVAR(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.INDIRECT:
#@cy			return self.__fetchINDIRECT(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.VIRT_ACCU:
#@cy			return self.__fetchVirtACCU(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.VIRT_AR:
#@cy			return self.__fetchVirtAR(operator, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.VIRT_DBR:
#@cy			return self.__fetchVirtDBR(operator, allowedWidths)
#@cy		self.__invalidFetch(operator)

	def __invalidFetch(self, operator):
		raise AwlSimError("Invalid fetch request: %s" % str(operator))

	def __fetchWidthError(self, operator, allowedWidths):
		raise AwlSimError("Data fetch of %d bits, "
			"but only %s bits are allowed." %\
			(operator.width,
			 listToHumanStr(AwlOperatorWidths.maskToList(allowedWidths))))

	def __fetchIMM(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchIMM(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return operator.immediate

	def __fetchIMM_DT(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchIMM_DT(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return operator.immediateBytes

	def __fetchIMM_PTR(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchIMM_PTR(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return operator.pointer.toNativePointerValue()

	def __fetchIMM_STR(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchIMM_STR(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef uint32_t insnType
#@cy		cdef uint32_t value
#@cy		cdef int32_t i

		if operator.width <= 48 and operator.insn is not None:
			insnType = operator.insn.insnType
			if insnType == AwlInsn.TYPE_L or\
			   insnType >= AwlInsn.TYPE_EXTENDED:
				# This is a special 0-4 character fetch (L) that
				# is transparently translated into an integer.
				value, data = 0, operator.immediateBytes
				for i in range(2, operator.width // 8):
					value = (value << 8) | data[i]
				return value

		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return operator.immediateBytes

	def __fetchDBLG(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchDBLG(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.dbRegister.struct.getSize()

	def __fetchDBNO(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchDBNO(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.dbRegister.index

	def __fetchDILG(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchDILG(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.diRegister.struct.getSize()

	def __fetchDINO(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchDINO(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.diRegister.index

	def __fetchAR2(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchAR2(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.getAR(2).get()

	def __fetchSTW(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		if operator.width == 1:
			return self.statusWord.getByBitNumber(operator.offset.bitOffset)
		elif operator.width == 16:
			return self.statusWord.getWord()
		else:
			assert(0)

	def __fetchSTW_Z(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW_Z(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return (self.statusWord.A0 ^ 1) & (self.statusWord.A1 ^ 1)

	def __fetchSTW_NZ(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW_NZ(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.statusWord.A0 | self.statusWord.A1

	def __fetchSTW_POS(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW_POS(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return (self.statusWord.A0 ^ 1) & self.statusWord.A1

	def __fetchSTW_NEG(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW_NEG(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.statusWord.A0 & (self.statusWord.A1 ^ 1)

	def __fetchSTW_POSZ(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW_POSZ(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.statusWord.A0 ^ 1

	def __fetchSTW_NEGZ(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW_NEGZ(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.statusWord.A1 ^ 1

	def __fetchSTW_UO(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchSTW_UO(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.statusWord.A0 & self.statusWord.A1

	def __fetchE(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchE(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.inputs.fetch(operator.offset, operator.width)

	def __fetchA(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchA(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.outputs.fetch(operator.offset, operator.width)

	def __fetchM(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchM(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.flags.fetch(operator.offset, operator.width)

	def __fetchL(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchL(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef LStackAllocator lstack

		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		lstack = self.activeLStack
		return lstack.memory.fetch(lstack.topFrameOffset + operator.offset,
					   operator.width)

	def __fetchVL(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchVL(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef CallStackElem cse
#@cy		cdef LStackAllocator lstack
#@cy		cdef LStackFrame *prevFrame

		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		lstack = self.activeLStack
		prevFrame = lstack.topFrame.prevFrame
		if not prevFrame:
			raise AwlSimError("Fetch of parent localstack, "
				"but no parent present.")
		return lstack.memory.fetch(make_AwlOffset(prevFrame.byteOffset, 0) + operator.offset,
					   operator.width)

	def __fetchDB(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchDB(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef int32_t dbNumber

		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		dbNumber = operator.offset.dbNumber
		if dbNumber >= 0:
			# This is a fully qualified access (DBx.DBx X)
			# Open the data block first.
			self.openDB(dbNumber, False)
		return self.dbRegister.fetch(operator, None)

	def __fetchDI(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchDI(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		if self.callStackTop.block.isFB:
			# Fetch the data using the multi-instance base offset from AR2.
			return self.diRegister.fetch(operator,
						     make_AwlOffset_fromPointerValue(self.ar2.get()))
		# Fetch without base offset.
		return self.diRegister.fetch(operator, None)

	def __fetchPE(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchPE(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef bytearray readBytes
#@cy		cdef uint32_t readValue
#@cy		cdef uint32_t bitWidth
#@cy		cdef AwlOffset operatorOffset

		bitWidth = operator.width
		if not (AwlOperatorWidths.makeMask(bitWidth) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)
		operatorOffset = operator.offset

		# Fetch the data from the peripheral device.
		readBytes = self.cbPeripheralRead(self.cbPeripheralReadData,
						  bitWidth,
						  operatorOffset.byteOffset)
		if not readBytes:
			raise AwlSimError("There is no hardware to handle "
				"the direct peripheral fetch. "
				"(width=%d, offset=%d)" %\
				(bitWidth, operatorOffset.byteOffset))
		readValue = WordPacker.fromBytes(readBytes, bitWidth)

		# Store the data to the process image, if it is within the inputs range.
		if operatorOffset.toLongBitOffset() + bitWidth < self.specs.nrInputs * 8:
			self.inputs.store(operatorOffset, bitWidth, readValue)

		return readValue

	def __fetchT(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchT(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef uint32_t insnType
#@cy		cdef uint32_t width

		insnType = operator.insn.insnType
		if insnType == AwlInsn.TYPE_L or insnType == AwlInsn.TYPE_LC:
			width = 32
		else:
			width = 1
		if not (AwlOperatorWidths.makeMask(width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		timer = self.getTimer(operator.offset.byteOffset)
		if insnType == AwlInsn.TYPE_L:
			return timer.getTimevalBin()
		elif insnType == AwlInsn.TYPE_LC:
			return timer.getTimevalS5T()
		return timer.get()

	def __fetchZ(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchZ(self, AwlOperator operator, uint32_t allowedWidths):
#@cy		cdef uint32_t insnType
#@cy		cdef uint32_t width

		insnType = operator.insn.insnType
		if insnType == AwlInsn.TYPE_L or insnType == AwlInsn.TYPE_LC:
			width = 32
		else:
			width = 1
		if not (AwlOperatorWidths.makeMask(width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		counter = self.getCounter(operator.offset.byteOffset)
		if insnType == AwlInsn.TYPE_L:
			return counter.getValueBin()
		elif insnType == AwlInsn.TYPE_LC:
			return counter.getValueBCD()
		return counter.get()

	def __fetchNAMED_LOCAL(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchNAMED_LOCAL(self, AwlOperator operator, uint32_t allowedWidths):
		# load from an FC interface field.
		return self.fetch(self.__translateFCNamedLocalOper(operator, False),
				  allowedWidths)

	def __fetchNAMED_LOCAL_PTR(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchNAMED_LOCAL_PTR(self, AwlOperator operator, uint32_t allowedWidths):
		assert(operator.offset.subOffset is None) #@nocy
		return self.callStackTop.getInterfIdxOper(operator.interfaceIndex).resolve(False).makePointerValue()

	def __fetchNAMED_DBVAR(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchNAMED_DBVAR(self, AwlOperator operator, uint32_t allowedWidths):
		# All legit accesses will have been translated to absolute addressing already
		raise AwlSimError("Fully qualified load from DB variable "
			"is not supported in this place.")

	def __fetchINDIRECT(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchINDIRECT(self, AwlOperator operator, uint32_t allowedWidths):
		return self.fetch(operator.resolve(False), allowedWidths)

	def __fetchVirtACCU(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchVirtACCU(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.getAccu(operator.offset.byteOffset).get()

	def __fetchVirtAR(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchVirtAR(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.getAR(operator.offset.byteOffset).get()

	def __fetchVirtDBR(self, operator, allowedWidths): #@nocy
#@cy	cdef object __fetchVirtDBR(self, AwlOperator operator, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		if operator.offset.byteOffset == 1:
			if self.dbRegister:
				return self.dbRegister.index
		elif operator.offset.byteOffset == 2:
			if self.diRegister:
				return self.diRegister.index
		else:
			raise AwlSimError("Invalid __DBR %d. "
				"Must be 1 for DB-register or "
				"2 for DI-register." %\
				operator.offset.byteOffset)
		return 0

	__fetchTypeMethodsDict = {							#@nocy
		AwlOperatorTypes.IMM			: __fetchIMM,			#@nocy
		AwlOperatorTypes.IMM_REAL		: __fetchIMM,			#@nocy
		AwlOperatorTypes.IMM_S5T		: __fetchIMM,			#@nocy
		AwlOperatorTypes.IMM_TIME		: __fetchIMM,			#@nocy
		AwlOperatorTypes.IMM_DATE		: __fetchIMM,			#@nocy
		AwlOperatorTypes.IMM_DT			: __fetchIMM_DT,		#@nocy
		AwlOperatorTypes.IMM_TOD		: __fetchIMM,			#@nocy
		AwlOperatorTypes.IMM_PTR		: __fetchIMM_PTR,		#@nocy
		AwlOperatorTypes.IMM_STR		: __fetchIMM_STR,		#@nocy
		AwlOperatorTypes.MEM_E			: __fetchE,			#@nocy
		AwlOperatorTypes.MEM_A			: __fetchA,			#@nocy
		AwlOperatorTypes.MEM_M			: __fetchM,			#@nocy
		AwlOperatorTypes.MEM_L			: __fetchL,			#@nocy
		AwlOperatorTypes.MEM_VL			: __fetchVL,			#@nocy
		AwlOperatorTypes.MEM_DB			: __fetchDB,			#@nocy
		AwlOperatorTypes.MEM_DI			: __fetchDI,			#@nocy
		AwlOperatorTypes.MEM_T			: __fetchT,			#@nocy
		AwlOperatorTypes.MEM_Z			: __fetchZ,			#@nocy
		AwlOperatorTypes.MEM_PE			: __fetchPE,			#@nocy
		AwlOperatorTypes.MEM_DBLG		: __fetchDBLG,			#@nocy
		AwlOperatorTypes.MEM_DBNO		: __fetchDBNO,			#@nocy
		AwlOperatorTypes.MEM_DILG		: __fetchDILG,			#@nocy
		AwlOperatorTypes.MEM_DINO		: __fetchDINO,			#@nocy
		AwlOperatorTypes.MEM_AR2		: __fetchAR2,			#@nocy
		AwlOperatorTypes.MEM_STW		: __fetchSTW,			#@nocy
		AwlOperatorTypes.MEM_STW_Z		: __fetchSTW_Z,			#@nocy
		AwlOperatorTypes.MEM_STW_NZ		: __fetchSTW_NZ,		#@nocy
		AwlOperatorTypes.MEM_STW_POS		: __fetchSTW_POS,		#@nocy
		AwlOperatorTypes.MEM_STW_NEG		: __fetchSTW_NEG,		#@nocy
		AwlOperatorTypes.MEM_STW_POSZ		: __fetchSTW_POSZ,		#@nocy
		AwlOperatorTypes.MEM_STW_NEGZ		: __fetchSTW_NEGZ,		#@nocy
		AwlOperatorTypes.MEM_STW_UO		: __fetchSTW_UO,		#@nocy
		AwlOperatorTypes.NAMED_LOCAL		: __fetchNAMED_LOCAL,		#@nocy
		AwlOperatorTypes.NAMED_LOCAL_PTR	: __fetchNAMED_LOCAL_PTR,	#@nocy
		AwlOperatorTypes.NAMED_DBVAR		: __fetchNAMED_DBVAR,		#@nocy
		AwlOperatorTypes.INDIRECT		: __fetchINDIRECT,		#@nocy
		AwlOperatorTypes.VIRT_ACCU		: __fetchVirtACCU,		#@nocy
		AwlOperatorTypes.VIRT_AR		: __fetchVirtAR,		#@nocy
		AwlOperatorTypes.VIRT_DBR		: __fetchVirtDBR,		#@nocy
	}										#@nocy

	def store(self, operator, value, allowedWidths):				#@nocy
		try:									#@nocy
			storeMethod = self.__storeTypeMethods[operator.operType]	#@nocy
		except KeyError:							#@nocy
			self.__invalidStore(operator)					#@nocy
		storeMethod(self, operator, value, allowedWidths)			#@nocy

#@cy	cpdef store(self, AwlOperator operator, object value, uint32_t allowedWidths):
#@cy		cdef uint32_t operType
#@cy
#@cy		operType = operator.operType
#@cy		if operType == AwlOperatorTypes.MEM_E:
#@cy			self.__storeE(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_A:
#@cy			self.__storeA(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_M:
#@cy			self.__storeM(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_L:
#@cy			self.__storeL(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_VL:
#@cy			self.__storeVL(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DB:
#@cy			self.__storeDB(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DI:
#@cy			self.__storeDI(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_PA:
#@cy			self.__storePA(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_AR2:
#@cy			self.__storeAR2(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW:
#@cy			self.__storeSTW(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.NAMED_LOCAL:
#@cy			self.__storeNAMED_LOCAL(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.NAMED_DBVAR:
#@cy			self.__storeNAMED_DBVAR(operator, value, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.INDIRECT:
#@cy			self.__storeINDIRECT(operator, value, allowedWidths)
#@cy		else:
#@cy			self.__invalidStore(operator)

	def __invalidStore(self, operator):
		raise AwlSimError("Invalid store request: %s" % str(operator))

	def __storeWidthError(self, operator, allowedWidths):
		raise AwlSimError("Data store of %d bits, "
			"but only %s bits are allowed." %\
			(operator.width,
			 listToHumanStr(AwlOperatorWidths.maskToList(allowedWidths))))

	def __storeE(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeE(self, AwlOperator operator, object value, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		self.inputs.store(operator.offset, operator.width, value)

	def __storeA(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeA(self, AwlOperator operator, object value, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		self.outputs.store(operator.offset, operator.width, value)

	def __storeM(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeM(self, AwlOperator operator, object value, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		self.flags.store(operator.offset, operator.width, value)

	def __storeL(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeL(self, AwlOperator operator, object value, uint32_t allowedWidths):
#@cy		cdef LStackAllocator lstack

		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		lstack = self.activeLStack
		lstack.memory.store(lstack.topFrameOffset + operator.offset,
				    operator.width,
				    value)

	def __storeVL(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeVL(self, AwlOperator operator, object value, uint32_t allowedWidths):
#@cy		cdef CallStackElem cse
#@cy		cdef LStackFrame *prevFrame

		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		lstack = self.activeLStack
		prevFrame = lstack.topFrame.prevFrame
		if not prevFrame:
			raise AwlSimError("Store to parent localstack, "
				"but no parent present.")
		lstack.memory.store(make_AwlOffset(prevFrame.byteOffset, 0) + operator.offset,
				    operator.width,
				    value)

	def __storeDB(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeDB(self, AwlOperator operator, object value, uint32_t allowedWidths):
#@cy		cdef DB db
#@cy		cdef int32_t dbNumber

		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		dbNumber = operator.offset.dbNumber
		if dbNumber < 0:
			db = self.dbRegister
		else:
			try:
				db = self.dbs[dbNumber]
			except KeyError:
				raise AwlSimError("Store to DB %d, but DB "
					"does not exist" % dbNumber)
		db.store(operator, value, None)

	def __storeDI(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeDI(self, AwlOperator operator, object value, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		if self.callStackTop.block.isFB:
			# Store the data using the multi-instance base offset from AR2.
			self.diRegister.store(operator, value,
					      make_AwlOffset_fromPointerValue(self.ar2.get()))
		else:
			# Store without base offset.
			self.diRegister.store(operator, value, None)

	def __storePA(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storePA(self, AwlOperator operator, object value, uint32_t allowedWidths):
#@cy		cdef _Bool ok
#@cy		cdef uint32_t bitWidth
#@cy		cdef bytearray valueBytes
#@cy		cdef AwlOffset operatorOffset

		bitWidth = operator.width
		if not (AwlOperatorWidths.makeMask(bitWidth) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)
		operatorOffset = operator.offset

		# Store the data to the process image, if it is within the outputs range.
		if operatorOffset.toLongBitOffset() + bitWidth < self.specs.nrOutputs * 8:
			self.outputs.store(operatorOffset, bitWidth, value)

		# Store the data to the peripheral device.
		valueBytes = bytearray(bitWidth // 8)
		WordPacker.toBytes(valueBytes, bitWidth, 0, value)
		ok = self.cbPeripheralWrite(self.cbPeripheralWriteData,
					    bitWidth,
					    operatorOffset.byteOffset,
					    valueBytes)
		if not ok:
			raise AwlSimError("There is no hardware to handle "
				"the direct peripheral store. "
				"(width=%d, offset=%d, value=0x%X)" %\
				(bitWidth, operatorOffset.byteOffset,
				 value))

	def __storeAR2(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeAR2(self, AwlOperator operator, object value, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		self.getAR(2).set(value)

	def __storeSTW(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeSTW(self, AwlOperator operator, object value, uint32_t allowedWidths):
		if not (AwlOperatorWidths.makeMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		if operator.width == 1:
			raise AwlSimError("Cannot store to individual STW bits")
		elif operator.width == 16:
			self.statusWord.setWord(value)
		else:
			assert(0)

	def __storeNAMED_LOCAL(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeNAMED_LOCAL(self, AwlOperator operator, object value, uint32_t allowedWidths):
		# store to an FC interface field.
		self.store(self.__translateFCNamedLocalOper(operator, True),
			   value, allowedWidths)

	def __storeNAMED_DBVAR(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeNAMED_DBVAR(self, AwlOperator operator, object value, uint32_t allowedWidths):
		# All legit accesses will have been translated to absolute addressing already
		raise AwlSimError("Fully qualified store to DB variable "
			"is not supported in this place.")

	def __storeINDIRECT(self, operator, value, allowedWidths): #@nocy
#@cy	cdef __storeINDIRECT(self, AwlOperator operator, object value, uint32_t allowedWidths):
		self.store(operator.resolve(True), value, allowedWidths)

	__storeTypeMethodsDict = {						#@nocy
		AwlOperatorTypes.MEM_E			: __storeE,		#@nocy
		AwlOperatorTypes.MEM_A			: __storeA,		#@nocy
		AwlOperatorTypes.MEM_M			: __storeM,		#@nocy
		AwlOperatorTypes.MEM_L			: __storeL,		#@nocy
		AwlOperatorTypes.MEM_VL			: __storeVL,		#@nocy
		AwlOperatorTypes.MEM_DB			: __storeDB,		#@nocy
		AwlOperatorTypes.MEM_DI			: __storeDI,		#@nocy
		AwlOperatorTypes.MEM_PA			: __storePA,		#@nocy
		AwlOperatorTypes.MEM_AR2		: __storeAR2,		#@nocy
		AwlOperatorTypes.MEM_STW		: __storeSTW,		#@nocy
		AwlOperatorTypes.NAMED_LOCAL		: __storeNAMED_LOCAL,	#@nocy
		AwlOperatorTypes.NAMED_DBVAR		: __storeNAMED_DBVAR,	#@nocy
		AwlOperatorTypes.INDIRECT		: __storeINDIRECT,	#@nocy
	}									#@nocy

	def __dumpMem(self, prefix, memory, byteOffset, maxLen):
		if not memory or not memory.dataBytes or maxLen <= 0:
			return prefix + "--"
		memArray = memory.dataBytes
		ret, line, first, count, i = [], [], True, 0, byteOffset
		def append(line):
			ret.append((prefix if first else (' ' * len(prefix))) +\
				   ' '.join(line))
		end = maxLen + byteOffset
		while i < end:
			line.append("%02X" % memArray[i])
			count += 1
			if count >= 16:
				append(line)
				line, count, first = [], 0, False
			i += 1
		if count:
			append(line)
		return '\n'.join(ret)

	def __dumpLStackFrame(self, prefix, frame): #@nocy
#@cy	cdef __dumpLStackFrame(self, prefix, LStackFrame *frame):
		if frame:
			memory = self.activeLStack.memory
			byteOffset = frame.byteOffset
			allocBits = frame.allocBits
		else:
			memory, byteOffset, allocBits = None, 0, 0
		return self.__dumpMem(prefix,
				      memory,
				      byteOffset,
				      min(64, intDivRoundUp(allocBits, 8)))

	def dump(self, withTime=True):
#@cy		cdef LStackFrame *frame

		callStackTop = self.callStackTop
		if not callStackTop:
			return ""
		mnemonics = self.getMnemonics()
		isEnglish = (mnemonics == S7CPUConfig.MNEMONICS_EN)
		specs = self.specs
		self.updateTimestamp()
		ret = []
		ret.append("[S7-CPU]  t: %.01fs  %s / py %d compat / %s / v%s" %\
			   ((self.now - self.startupTime) if withTime else 0.0,
			    pythonInterpreter,
			    3 if isPy3Compat else 2,
			    "Win" if osIsWindows else ("Posix" if osIsPosix else "unknown"),
			    VERSION_STRING))
		ret.append("    STW:  " + self.statusWord.getString(mnemonics))
		if self.is4accu:
			accus = ( accu.toHex()
				  for accu in (self.accu1, self.accu2,
					       self.accu3, self.accu4) )
		else:
			accus = ( accu.toHex()
				  for accu in (self.accu1, self.accu2) )
		ret.append("   Accu:  " + "  ".join(accus))
		ars = ( "%s (%s)" % (ar.toHex(), ar.toPointerString())
			for ar in (self.ar1, self.ar2) )
		ret.append("     AR:  " + "  ".join(ars))
		ret.append(self.__dumpMem("      M:  ",
					  self.flags, 0,
					  min(64, specs.nrFlags)))
		prefix = "      I:  " if isEnglish else "      E:  "
		ret.append(self.__dumpMem(prefix,
					  self.inputs, 0,
					  min(64, specs.nrInputs)))
		prefix = "      Q:  " if isEnglish else "      A:  "
		ret.append(self.__dumpMem(prefix,
					  self.outputs, 0,
					  min(64, specs.nrOutputs)))
		pstack = str(callStackTop.parenStack) if callStackTop.parenStack else "--"
		ret.append(" PStack:  " + pstack)
		ret.append("  DBreg:  %s  %s" % (str(self.dbRegister),
						 str(self.diRegister).replace("DB", "DI")))
		if callStackTop:
			elemsMax, elemsCount, elems, cse =\
				8, 0, [], callStackTop
			while cse is not None:
				elemsCount += 1
				elems.insert(0, cse.block)
				cse = cse.prevCse
			assert(elemsCount == self.callStackDepth)
			ret.append("  Calls:  (%d)  %s%s" %\
				   (elemsCount, " -> ".join(str(e) for e in elems[:elemsMax]),
				    " -> ..." if len(elems) > elemsMax else ""))
			frame = self.activeLStack.topFrame
			ret.append(self.__dumpLStackFrame("      L:  ", frame))
			frame = frame.prevFrame if frame else None #@cy-NoneToNULL
			ret.append(self.__dumpLStackFrame("     VL:  ", frame))
		else:
			ret.append("  Calls:  None")
		curInsn = self.getCurrentInsn()
		ret.append("   Stmt:  IP:%s   %s" %\
			   (str(self.getCurrentIP()),
			    str(curInsn) if curInsn else "none"))
		ret.append("  Speed:  %s stmt/s (= %s us/stmt)  %.01f stmt/cycle" % (
			   self.insnPerSecondHR,
			   self.usPerInsnHR,
			   self.avgInsnPerCycle))
		avgCycleTime = self.avgCycleTime
		minCycleTime = self.minCycleTime
		maxCycleTime = self.maxCycleTime
		if maxCycleTime == 0.0:
			avgCycleTimeStr = minCycleTimeStr = maxCycleTimeStr = "-/-"
		else:
			if avgCycleTime == 0.0:
				avgCycleTimeStr = "-/-"
			else:
				avgCycleTimeStr = "%.03f" % (self.avgCycleTime * 1000.0)
			minCycleTimeStr = "%.03f" % (self.minCycleTime * 1000.0)
			maxCycleTimeStr = "%.03f" % (self.maxCycleTime * 1000.0)
		ret.append("OB1time:  avg: %s ms  min: %s ms  max: %s ms" % (
			   avgCycleTimeStr, minCycleTimeStr, maxCycleTimeStr))
		return '\n'.join(ret)

	@property
	def insnPerSecondHR(self):
		"""Get a human readable instructions per seconds string.
		"""
		insnPerSecond = self.insnPerSecond
		if insnPerSecond >= 1000000.0:
			insnPerSecondStr = "%.02f M" % (insnPerSecond / 1000000.0)
		elif insnPerSecond >= 1000.0:
			insnPerSecondStr = "%.02f k" % (insnPerSecond / 1000.0)
		elif insnPerSecond > 0.0:
			insnPerSecondStr = "%.02f" % insnPerSecond
		else:
			insnPerSecondStr = "-/-"
		return insnPerSecondStr

	@property
	def usPerInsnHR(self):
		"""Get a human readable microseconds per instructions string.
		"""
		insnPerSecond = self.insnPerSecond
		if insnPerSecond > 0.0:
			usPerInsnStr = "%.03f" % ((1.0 / insnPerSecond) * 1000000)
		else:
			usPerInsnStr = "-/-"
		return usPerInsnStr

	def __repr__(self):
		return self.dump()
