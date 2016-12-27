# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
#
# Copyright 2012-2016 Michael Buesch <m@bues.ch>
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

#from awlsim.core.cpu cimport * #@cy
#from awlsim.core.dynattrs cimport * #@cy
#from awlsim.core.statusword cimport * #@cy
#from awlsim.core.instructions.all_insns cimport * #@cy

from awlsim.common.cpuspecs import *
from awlsim.common.blockinfo import *

from awlsim.library.libentry import *

from awlsim.core.parser import *
from awlsim.core.symbolparser import *
from awlsim.core.datatypes import *
from awlsim.core.instructions.all_insns import * #@nocy
from awlsim.core.systemblocks.system_sfb import *
from awlsim.core.systemblocks.system_sfc import *
from awlsim.core.operators import *
from awlsim.core.translator import *
from awlsim.core.blocks import *
from awlsim.core.datablocks import *
from awlsim.core.userdefinedtypes import *
from awlsim.core.statusword import * #@nocy
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
		mnemonics = self.cpu.getMnemonics()
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
		specs = self.cpu.getSpecs()
		if specs.getConfiguredMnemonics() != S7CPUSpecs.MNEMONICS_AUTO:
			return

		detected = None
		errorCounts = {}
		rawBlocks = list(itertools.chain(self.pendingRawOBs,
						 self.pendingRawFBs,
						 self.pendingRawFCs))
		if not rawBlocks:
			if specs.getMnemonics() != S7CPUSpecs.MNEMONICS_AUTO:
				# It was already set. We are Ok.
				return
			# There are no blocks and we didn't detect anything, yet.
			# Just set it to EN.
			detected = S7CPUSpecs.MNEMONICS_EN
		if detected is None:
			for mnemonics in (S7CPUSpecs.MNEMONICS_EN,
					  S7CPUSpecs.MNEMONICS_DE):
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
			if errorCounts[S7CPUSpecs.MNEMONICS_EN] <= errorCounts[S7CPUSpecs.MNEMONICS_DE]:
				detected = S7CPUSpecs.MNEMONICS_EN
			else:
				detected = S7CPUSpecs.MNEMONICS_DE
		if specs.getMnemonics() not in {S7CPUSpecs.MNEMONICS_AUTO, detected}:
			# Autodetected mnemonics were already set before
			# to something different.
			raise AwlSimError("Cannot mix multiple AWL files with "\
				"distinct mnemonics. This error may be caused by "\
				"incorrect autodetection. "\
				"Force mnemonics to EN or DE to avoid this error.")
		specs.setDetectedMnemonics(detected)

	def __loadLibraries(self):
		for libSelection in self.pendingLibSelections:
			# Get the block class from the library.
			libEntryCls = AwlLib.getEntryBySelection(libSelection)
			assert(not libEntryCls.isSystemBlock)

			# Get the effective block index.
			effIndex = libSelection.getEffectiveEntryIndex()
			if effIndex < 0:
				effIndex = libSelection.getEntryIndex()

			# Create and translate the block
			translator = AwlTranslator(self.cpu)
			if libEntryCls.isFC:
				block = libEntryCls(index = effIndex)
				if block.index in self.cpu.fcs and\
				   not self.cpu.fcs[block.index].isLibraryBlock:
					raise AwlSimError("Error while loading library "
						"block FC %d: Block FC %d is already "
						"loaded as user defined block." %\
						(block.index, block.index))
				block = translator.translateLibraryCodeBlock(block)
				self.cpu.fcs[block.index] = block
			elif libEntryCls.isFB:
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
					param.interface = calledCodeBlock.interface
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
		self.specs = S7CPUSpecs(self)
		self.prog = S7Prog(self)
		self.setCycleTimeLimit(5.0)
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
		self.reset()
		self.enableExtendedInsns(False)
		self.enableObTempPresets(False)

	def getMnemonics(self):
		return self.specs.getMnemonics()

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

	def setRunTimeLimit(self, timeoutSeconds=0.0):
		self.__runtimeLimit = timeoutSeconds if timeoutSeconds > 0.0 else None

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
		resolver = AwlSymResolver(self)

		for insn in block.insns:
			if insn.insnType != AwlInsn.TYPE_CALL:
				continue

			# Get the DB block, if any.
			if len(insn.ops) == 1:
				dataBlock = None
			elif len(insn.ops) == 2:
				dataBlockOp = insn.ops[1]
				if dataBlockOp.type == AwlOperator.SYMBOLIC:
					blockIndex, symbol = resolver.resolveBlockName(
							{AwlDataType.TYPE_FB_X,
							 AwlDataType.TYPE_SFB_X},
							dataBlockOp.value.identChain.getString())
					dataBlockOp = symbol.operator.dup()
				dataBlockIndex = dataBlockOp.value.byteOffset
				try:
					if dataBlockOp.type == AwlOperator.BLKREF_DB:
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
			if codeBlockOp.type == AwlOperator.SYMBOLIC:
				blockIndex, symbol = resolver.resolveBlockName(
						{AwlDataType.TYPE_FC_X,
						 AwlDataType.TYPE_FB_X,
						 AwlDataType.TYPE_SFC_X,
						 AwlDataType.TYPE_SFB_X},
						codeBlockOp.value.identChain.getString())
				codeBlockOp = symbol.operator.dup()
			elif codeBlockOp.type == AwlOperator.NAMED_LOCAL:
				codeBlockOp = resolver.resolveNamedLocal(block, insn, codeBlockOp)

			if codeBlockOp.type in {AwlOperator.MULTI_FB,
						AwlOperator.MULTI_SFB}:
				codeBlockIndex = codeBlockOp.value.fbNumber
			else:
				codeBlockIndex = codeBlockOp.value.byteOffset
			try:
				if codeBlockOp.type == AwlOperator.BLKREF_FC:
					codeBlock = self.fcs[codeBlockIndex]
				elif codeBlockOp.type in {AwlOperator.BLKREF_FB,
							  AwlOperator.MULTI_FB}:
					codeBlock = self.fbs[codeBlockIndex]
				elif codeBlockOp.type == AwlOperator.BLKREF_SFC:
					codeBlock = self.sfcs[codeBlockIndex]
				elif codeBlockOp.type in {AwlOperator.BLKREF_SFB,
							  AwlOperator.MULTI_SFB}:
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
			self.flags = ByteArray(self.specs.nrFlags)
		if force or self.specs.nrInputs != len(self.inputs):
			self.inputs = ByteArray(self.specs.nrInputs)
		if force or self.specs.nrOutputs != len(self.outputs):
			self.outputs = ByteArray(self.specs.nrOutputs)
		CallStackElem.resetCache()

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
		self.ar1 = Adressregister()
		self.ar2 = Adressregister()
		self.dbRegister = self.dbs[0]
		self.diRegister = self.dbs[0]
		self.callStack = [ ]
		self.callStackTop = None
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
		self.startupTime = perf_monotonic_time()
		self.__speedMeasureStartTime = 0
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0

		self._initializeTimestamp()

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

	def __runOB(self, block):
		# Update timekeeping
		self.updateTimestamp()
		self.cycleStartTime = self.now

		# Initialize CPU state
		self.dbRegister = self.diRegister = self.dbs[0]
		self.accu1.reset()
		self.accu2.reset()
		self.accu3.reset()
		self.accu4.reset()
		self.ar1.reset()
		self.ar2.reset()
		self.statusWord.reset()
		self.callStack = [ CallStackElem(self, block, None, None, (), True) ]
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
					self.cbPostInsn(cse, self.cbPostInsnData)
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

	def _initClockMemState(self):
		"""Reset/initialize the clock memory byte state.
		"""
		self.__clockMemByteOffset = None
		self.updateTimestamp()
		if self.specs.clockMemByte >= 0:
			self.__clockMemByteOffset = AwlOffset(self.specs.clockMemByte)
		self.__nextClockMemTime = self.now + 0.05
		self.__clockMemCount = 0
		self.__clockMemCountLCM = math_lcm(2, 4, 5, 8, 10, 16, 20)
		if self.__clockMemByteOffset:
			self.flags.store(self.__clockMemByteOffset, 8, 0)

	# Run startup code
	def startup(self):
		# Build (translate) the blocks, if not already done so.
		self.build()

		self._initializeTimestamp()
		self.__speedMeasureStartTime = self.now
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0
		self.startupTime = self.now

		self._initClockMemState()

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

		# Call the cycle exit callback, if any.
		if self.cbCycleExit:
			self.cbCycleExit(self.cbCycleExitData)

	# Returns 'self.now' as 31 bit millisecond representation.
	# That is data type 'TIME'.
	# The returned value will always be positive and wrap
	# from 0x7FFFFFFF to 0.
	@property
	def now_TIME(self):
		return int(self.now * 1000.0) & 0x7FFFFFFF

	# Initialize time stamp.
	def _initializeTimestamp(self):
		# Initialize the time stamp so that it will
		# overflow 31 bit millisecond count within
		# 100 milliseconds after startup.
		# An 31 bit overflow happens after 0x7FFFFFFF ms,
		# which is 2147483647 ms, which is 2147483.647 s.
		# Create an offset to 'self.now' that is added every
		# time 'self.now' is updated.
		now = perf_monotonic_time()
		self.__nowOffset = -(now) + (2147483.647 - 0.1)
		self.updateTimestamp()

	# updateTimestamp() updates self.now, which is a
	# floating point count of seconds.
	def updateTimestamp(self, _getTime=perf_monotonic_time):
		# Update the system time
		self.now = _getTime() + self.__nowOffset
		# Update the clock memory byte
		if self.__clockMemByteOffset:
			try:
				if self.now >= self.__nextClockMemTime:
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
		if self.__runtimeLimit is not None:
			if self.now - self.startupTime >= self.__runtimeLimit:
				raise MaintenanceRequest(MaintenanceRequest.TYPE_RTTIMEOUT,
					"CPU runtime timeout")

	# Make a DATE_AND_TIME for the current wall-time and
	# store it in byteArray, which is a ByteArray or bytearray or compatible.
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
					AwlDataType.dateAndTimeWeekdayMap[dt.weekday()]

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
		# Translate a label index into a relative IP offset.
		cse = self.callStackTop
		label = cse.block.labels[labelIndex]
		return label.getInsn().getIP() - cse.ip

	def jumpToLabel(self, labelIndex):
		self.relativeJump = self.labelIdxToRelJump(labelIndex)

	def jumpRelative(self, insnOffset):
		self.relativeJump = insnOffset

	def __call_FC(self, blockOper, dbOper, parameters):
		fc = self.fcs[blockOper.value.byteOffset]
		return CallStackElem(self, fc, None, None, parameters)

	def __call_RAW_FC(self, blockOper, dbOper, parameters):
		fc = self.fcs[blockOper.value.byteOffset]
		return CallStackElem(self, fc, None, None, (), True)

	def __call_FB(self, blockOper, dbOper, parameters):
		fb = self.fbs[blockOper.value.byteOffset]
		db = self.dbs[dbOper.value.byteOffset]
		cse = CallStackElem(self, fb, db, AwlOffset(), parameters)
		self.dbRegister, self.diRegister = self.diRegister, db
		return cse

	def __call_RAW_FB(self, blockOper, dbOper, parameters):
		fb = self.fbs[blockOper.value.byteOffset]
		return CallStackElem(self, fb, self.diRegister, None, (), True)

	def __call_SFC(self, blockOper, dbOper, parameters):
		sfc = self.sfcs[blockOper.value.byteOffset]
		return CallStackElem(self, sfc, None, None, parameters)

	def __call_RAW_SFC(self, blockOper, dbOper, parameters):
		sfc = self.sfcs[blockOper.value.byteOffset]
		return CallStackElem(self, sfc, None, None, (), True)

	def __call_SFB(self, blockOper, dbOper, parameters):
		sfb = self.sfbs[blockOper.value.byteOffset]
		db = self.dbs[dbOper.value.byteOffset]
		cse = CallStackElem(self, sfb, db, AwlOffset(), parameters)
		self.dbRegister, self.diRegister = self.diRegister, db
		return cse

	def __call_RAW_SFB(self, blockOper, dbOper, parameters):
		sfb = self.sfbs[blockOper.value.byteOffset]
		return CallStackElem(self, sfb, self.diRegister, None, (), True)

	def __call_INDIRECT(self, blockOper, dbOper, parameters):
		blockOper = blockOper.resolve()
		callHelper = self.__rawCallHelpers[blockOper.type]
		try:
			return callHelper(self, blockOper, dbOper, parameters)
		except KeyError as e:
			raise AwlSimError("Code block %d not found in indirect call" %\
					  blockOper.value.byteOffset)

	def __call_MULTI_FB(self, blockOper, dbOper, parameters):
		fb = self.fbs[blockOper.value.fbNumber]
		base = AwlOffset.fromPointerValue(self.ar2.get()) + blockOper.value
		cse = CallStackElem(self, fb, self.diRegister, base, parameters)
		self.dbRegister = self.diRegister
		return cse

	def __call_MULTI_SFB(self, blockOper, dbOper, parameters):
		sfb = self.sfbs[blockOper.value.fbNumber]
		base = AwlOffset.fromPointerValue(self.ar2.get()) + blockOper.value
		cse = CallStackElem(self, sfb, self.diRegister, base, parameters)
		self.dbRegister = self.diRegister
		return cse

	__callHelpers = {
		AwlOperator.BLKREF_FC	: __call_FC,
		AwlOperator.BLKREF_FB	: __call_FB,
		AwlOperator.BLKREF_SFC	: __call_SFC,
		AwlOperator.BLKREF_SFB	: __call_SFB,
		AwlOperator.MULTI_FB	: __call_MULTI_FB,
		AwlOperator.MULTI_SFB	: __call_MULTI_SFB,
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

	def __translateFCNamedLocalOper(self, operator, store):
		# Translate an 'operator' to a named local FC parameter.
		# The returned operator is an operator to the actual data.
		interfOp = self.callStackTop.interfRefs[operator.interfaceIndex].resolve(store)
		if operator.compound:
			# This is a named local variable with compound data type.
			# The operator (interfOp) points to a DB-pointer in VL.
			# First fetch the DB pointer values from VL.
			dbPtrOp = interfOp.dup()
			dbPtrOp.width = 16
			dbNr = self.fetch(dbPtrOp)
			dbPtrOp.value += AwlOffset(2)
			dbPtrOp.width = 32
			pointer = self.fetch(dbPtrOp)
			# Open the DB pointed to by the DB-ptr.
			# (This is ok, if dbNr is 0, too)
			self.run_AUF(AwlOperator(AwlOperator.BLKREF_DB, 16,
						 AwlOffset(dbNr),
						 operator.insn))
			# Make an operator from the DB-ptr.
			try:
				opType = AwlIndirectOp.area2optype_fetch[
						pointer & AwlIndirectOp.AREA_MASK]
			except KeyError:
				raise AwlSimError("Corrupt DB pointer in compound "
					"data type FC variable detected "
					"(invalid area).", insn = operator.insn)
			finalOp = AwlOperator(opType, operator.width,
					      AwlOffset.fromPointerValue(pointer),
					      operator.insn)
		else:
			# Not a compound data type.
			# The translated operand already points to the variable.
			finalOp = interfOp.dup()
			finalOp.width = operator.width
		# Add possible sub-offsets (ARRAY, STRUCT) to the offset.
		finalOp.value += operator.value.subOffset
		# Reparent the operator to the originating instruction.
		# This is especially important for T and Z fetches due
		# to their semantic dependency on the instruction being used.
		finalOp.insn = operator.insn
		return finalOp

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

	def fetch(self, operator, enforceWidth=set()): #@nocy
#@cy	cpdef object fetch(self, object operator, set enforceWidth=set()):
		try:
			fetchMethod = self.fetchTypeMethods[operator.type]
		except KeyError:
			raise AwlSimError("Invalid fetch request: %s" %\
				str(operator))
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

	def fetchIMM_PTR(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		return operator.value.toNativePointerValue()

	def fetchIMM_STR(self, operator, enforceWidth):
		if operator.width <= 48 and operator.insn:
			insnType = operator.insn.insnType
			if insnType == AwlInsn.TYPE_L or\
			   insnType >= AwlInsn.TYPE_EXTENDED:
				# This is a special 0-4 character fetch (L) that
				# is transparently translated into an integer.
				value, data = 0, operator.value
				for i in range(2, operator.width // 8):
					value = (value << 8) | data[i]
				return value

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
		return self.dbRegister.fetch(operator)

	def fetchDI(self, operator, enforceWidth):
		if operator.width not in enforceWidth and enforceWidth:
			self.__fetchWidthError(operator, enforceWidth)

		if self.callStackTop.block.isFB:
			# Fetch the data using the multi-instance base offset from AR2.
			return self.diRegister.fetch(operator,
						     AwlOffset.fromPointerValue(self.ar2.get()))
		# Fetch without base offset.
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
		insnType = operator.insn.insnType
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
		insnType = operator.insn.insnType
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
		return self.fetch(self.__translateFCNamedLocalOper(operator, False),
				  enforceWidth)

	def fetchNAMED_LOCAL_PTR(self, operator, enforceWidth):
		assert(operator.value.subOffset.byteOffset == 0)
		return self.callStackTop.interfRefs[operator.interfaceIndex].resolve(False).makePointerValue()

	def fetchNAMED_DBVAR(self, operator, enforceWidth):
		# All legit accesses will have been translated to absolute addressing already
		raise AwlSimError("Fully qualified load from DB variable "
			"is not supported in this place.")

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
		AwlOperator.IMM_DT		: fetchIMM,
		AwlOperator.IMM_TOD		: fetchIMM,
		AwlOperator.IMM_PTR		: fetchIMM_PTR,
		AwlOperator.IMM_STR		: fetchIMM_STR,
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
		AwlOperator.NAMED_DBVAR		: fetchNAMED_DBVAR,
		AwlOperator.INDIRECT		: fetchINDIRECT,
		AwlOperator.VIRT_ACCU		: fetchVirtACCU,
		AwlOperator.VIRT_AR		: fetchVirtAR,
		AwlOperator.VIRT_DBR		: fetchVirtDBR,
	}

	def store(self, operator, value, enforceWidth=set()): #@nocy
#@cy	cpdef store(self, object operator, object value, set enforceWidth=set()):
		try:
			storeMethod = self.storeTypeMethods[operator.type]
		except KeyError:
			raise AwlSimError("Invalid store request: %s" %\
				str(operator))
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

		if self.callStackTop.block.isFB:
			# Store the data using the multi-instance base offset from AR2.
			self.diRegister.store(operator, value,
					      AwlOffset.fromPointerValue(self.ar2.get()))
		else:
			# Store without base offset.
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
		self.store(self.__translateFCNamedLocalOper(operator, True),
			   value, enforceWidth)

	def storeNAMED_DBVAR(self, operator, value, enforceWidth):
		# All legit accesses will have been translated to absolute addressing already
		raise AwlSimError("Fully qualified store to DB variable "
			"is not supported in this place.")

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
		AwlOperator.NAMED_DBVAR		: storeNAMED_DBVAR,
		AwlOperator.INDIRECT		: storeINDIRECT,
	}

	def __dumpMem(self, prefix, memArray, maxLen):
		if not memArray:
			return prefix + "--"
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
		mnemonics = self.getMnemonics()
		isEnglish = (mnemonics == S7CPUSpecs.MNEMONICS_EN)
		self.updateTimestamp()
		ret = []
		ret.append("[S7-CPU]  t: %.01fs  py: %d / %s / %s" %\
			   (self.now - self.startupTime,
			    3 if isPy3Compat else 2,
			    pythonInterpreter,
			    "Win" if osIsWindows else ("Posix" if osIsPosix else "unknown")))
		ret.append("    STW:  " + self.statusWord.getString(mnemonics))
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
		prefix = "      I:  " if isEnglish else "      E:  "
		ret.append(self.__dumpMem(prefix,
					  self.inputs,
					  min(64, self.specs.nrInputs)))
		prefix = "      Q:  " if isEnglish else "      A:  "
		ret.append(self.__dumpMem(prefix,
					  self.outputs,
					  min(64, self.specs.nrOutputs)))
		pstack = str(self.callStackTop.parenStack) if self.callStackTop.parenStack else "Empty"
		ret.append(" PStack:  " + pstack)
		ret.append("     DB:  %s" % str(self.dbRegister))
		ret.append("     DI:  %s" % str(self.diRegister))
		if self.callStack:
			elems = [ str(cse) for cse in self.callStack ]
			elems = " => ".join(elems)
			ret.append("  Calls:  %d:  %s" %\
				   (len(self.callStack), elems))
			localdata = self.callStack[-1].localdata
			ret.append(self.__dumpMem("      L:  ",
						  localdata,
						  min(16, self.specs.nrLocalbytes)))
			try:
				localdata = self.callStack[-2].localdata
			except IndexError:
				localdata = None
			ret.append(self.__dumpMem("     VL:  ",
						  localdata,
						  min(16, self.specs.nrLocalbytes)))
		else:
			ret.append("  Calls:  None")
		curInsn = self.getCurrentInsn()
		ret.append("   Stmt:  IP:%s   %s" %\
			   (str(self.getCurrentIP()),
			    str(curInsn) if curInsn else ""))
		if self.insnPerSecond:
			usPerInsn = "%.03f" % ((1.0 / self.insnPerSecond) * 1000000)
		else:
			usPerInsn = "-/-"
		ret.append("  Speed:  %d stmt/s (= %s us/stmt)  %.01f stmt/cycle" %\
			   (int(round(self.insnPerSecond)),
			    usPerInsn,
			    self.avgInsnPerCycle))
		ret.append(" CycleT:  avg: %.06f s  min: %.06f s  max: %.06f s" %\
			   (self.avgCycleTime, self.minCycleTime,
			    self.maxCycleTime))
		return '\n'.join(ret)
