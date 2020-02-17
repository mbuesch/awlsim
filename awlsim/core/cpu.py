# -*- coding: utf-8 -*-
#
# AWL simulator - CPU
#
# Copyright 2012-2020 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

#cimport cython #@cy

import time
import datetime
import random

from awlsim.common.util import *
from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.blockinfo import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *
from awlsim.common.env import *
from awlsim.common.version import *
from awlsim.common.monotonic import * #+cimport
from awlsim.common.movingavg import * #+cimport
from awlsim.common.lpfilter import * #+cimport

from awlsim.library.libentry import *

from awlsim.core.symbolparser import *
from awlsim.core.memory import * #+cimport
from awlsim.core.instructions.all_insns import * #+cimport
from awlsim.core.instructions.types import * #+cimport
from awlsim.core.systemblocks.systemblocks import * #+cimport
from awlsim.core.systemblocks.tables import *
from awlsim.core.operatortypes import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.blocks import * #+cimport
from awlsim.core.datablocks import * #+cimport
from awlsim.core.userdefinedtypes import * #+cimport
from awlsim.core.statusword import * #+cimport
from awlsim.core.labels import * #+cimport
from awlsim.core.timers import * #+cimport
from awlsim.core.counters import * #+cimport
from awlsim.core.callstack import * #+cimport
from awlsim.core.lstack import * #+cimport
from awlsim.core.offset import * #+cimport
from awlsim.core.obtemp import * #+cimport
from awlsim.core.insnmeas import * #+cimport

from awlsim.awlcompiler.tokenizer import *
from awlsim.awlcompiler.translator import *
from awlsim.awlcompiler.insntrans import *
from awlsim.awlcompiler.optrans import *

#from libc.string cimport memcpy #@cy


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
		self.sfcsInitialized = False
		self.sfbsInitialized = False
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
#@cy		cdef S7CPU cpu

		cpu = self.cpu
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
				block = libEntryCls(index=effIndex)
				existingFC = cpu.getFC(block.index)
				if existingFC and existingFC.isLibraryBlock:
					raise AwlSimError("Error while loading library "
						"block FC %d: Block FC %d is already "
						"loaded as user defined block." %\
						(block.index, block.index))
				block = translator.translateLibraryCodeBlock(block)
				cpu.addFC(block)
			elif libEntryCls._isFB:
				block = libEntryCls(index=effIndex)
				existingFB = cpu.getFB(block.index)
				if existingFB and existingFB.isLibraryBlock:
					raise AwlSimError("Error while loading library "
						"block FB %d: Block FB %d is already "
						"loaded as user defined block." %\
						(block.index, block.index))
				block = translator.translateLibraryCodeBlock(block)
				cpu.addFB(block)
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
#@cy		cdef S7CPU cpu

		cpu = self.cpu

		# The main cycle expects OB 1 to be present.
		if not cpu.getOB(1):
			raise AwlSimError("OB 1 is not present in the CPU.")
		# Run the user code checks.
		for block in cpu.allUserCodeBlocks():
			self.__staticSanityChecks_block(block)

	def build(self):
		"""Translate the loaded sources into their executable forms.
		"""
#@cy		cdef S7CPU cpu

		from awlsim.core.datatypes import AwlDataType

		cpu = self.cpu

		translator = AwlTranslator(cpu)
		resolver = AwlSymResolver(cpu)

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
			existingUDT = cpu.getUDT(udtNumber)
			if existingUDT:
				existingUDT.destroySourceRef()
			udts[udtNumber] = udt
			cpu.addUDT(udt)
		self.pendingRawUDTs = []

		# Build all UDTs (Resolve sizes of all fields)
		for udt in dictValues(udts):
			udt.buildDataStructure(cpu)

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
			existingOB = cpu.getOB(obNumber)
			if existingOB:
				existingOB.destroySourceRef()
			obs[obNumber] = ob
			cpu.addOB(ob)
			# Create the TEMP-preset handler table
			try:
				presetHandlerClass = OBTempPresets_table[obNumber]
			except KeyError:
				presetHandlerClass = OBTempPresets_dummy
			cpu.obTempPresetHandlers[obNumber] = presetHandlerClass(cpu)
		self.pendingRawOBs = []

		# Translate FBs
		fbs = {}
		for rawFB in self.pendingRawFBs:
			fbNumber, sym = resolver.resolveBlockName({AwlDataType.TYPE_FB_X},
								  rawFB.index)
			if fbNumber in fbs:
				raise AwlSimError("Multiple definitions of "\
					"FB %d." % fbNumber)
			existingFB = cpu.getFB(fbNumber)
			if existingFB and existingFB.isLibraryBlock:
				raise AwlSimError("Multiple definitions of FB %d.\n"
					"FB %d is already defined by an "
					"imported library block (%s)." % (
					fbNumber, fbNumber,
					existingFB.libraryName))
			rawFB.index = fbNumber
			fb = translator.translateCodeBlock(rawFB, FB)
			if existingFB:
				existingFB.destroySourceRef()
			fbs[fbNumber] = fb
			cpu.addFB(fb)
		self.pendingRawFBs = []

		# Translate FCs
		fcs = {}
		for rawFC in self.pendingRawFCs:
			fcNumber, sym = resolver.resolveBlockName({AwlDataType.TYPE_FC_X},
								  rawFC.index)
			if fcNumber in fcs:
				raise AwlSimError("Multiple definitions of "\
					"FC %d." % fcNumber)
			existingFC = cpu.getFC(fcNumber)
			if existingFC and existingFC.isLibraryBlock:
				raise AwlSimError("Multiple definitions of FC %d.\n"
					"FC %d is already defined by an "
					"imported library block (%s)." % (
					fcNumber, fcNumber,
					existingFC.libraryName))
			rawFC.index = fcNumber
			fc = translator.translateCodeBlock(rawFC, FC)
			if existingFC:
				existingFC.destroySourceRef()
			fcs[fcNumber] = fc
			cpu.addFC(fc)
		self.pendingRawFCs = []

		if not self.sfbsInitialized:
			# Create the SFB tables
			for sfbNumber in dictKeys(SFB_table):
				if sfbNumber < 0 and not cpu.extendedInsnsEnabled():
					continue
				sfb = SFB_table[sfbNumber](cpu)
				cpu.addSFB(sfb)
			self.sfbsInitialized = True

		if not self.sfcsInitialized:
			# Create the SFC tables
			for sfcNumber in dictKeys(SFC_table):
				if sfcNumber < 0 and not cpu.extendedInsnsEnabled():
					continue
				sfc = SFC_table[sfcNumber](cpu)
				cpu.addSFC(sfc)
			self.sfcsInitialized = True

		# Build the data structures of code blocks.
		for block in cpu.allCodeBlocks():
			block.interface.buildDataStructure(cpu)

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
			existingDB = cpu.getDB(dbNumber)
			if existingDB:
				existingDB.destroySourceRef()
			dbs[dbNumber] = db
			cpu.addDB(db)
		self.pendingRawDBs = []

		# Resolve symbolic instructions and operators
		self.__resolveSymbols()

		# Do some finalizations
		self.__finalizeCodeBlocks()

		# Run some static sanity checks on the code
		self.staticSanityChecks()

	def getBlockInfos(self,
			  getOBInfo=False,
			  getFCInfo=False,
			  getFBInfo=False,
			  getDBInfo=False,
			  getUDTInfo=False):
		"""Returns a list of BlockInfo().
		"""
		blkInfos = []
		for block in itertools.chain(
				sorted(self.cpu.allOBs() if getOBInfo else [],
				       key=lambda blk: blk.index),
				sorted(self.cpu.allFCs() if getFCInfo else [],
				       key=lambda blk: blk.index),
				sorted(self.cpu.allFBs() if getFBInfo else [],
				       key=lambda blk: blk.index),
				sorted(self.cpu.allDBs() if getDBInfo else [],
				       key=lambda blk: blk.index),
				sorted(self.cpu.allUDTs() if getUDTInfo else [],
				       key=lambda blk: blk.index)):
			blkInfo = block.getBlockInfo()
			assert(blkInfo)
			blkInfos.append(blkInfo)
		return blkInfos

	def removeBlock(self, blockInfo, sanityChecks = True):
		"""Remove a block from the CPU.
		"""
		if blockInfo.blockType == BlockInfo.TYPE_OB:
			block = self.cpu.removeOB(blockInfo.blockIndex)
			self.cpu.obTempPresetHandlers.pop(blockInfo.blockIndex)
		elif blockInfo.blockType == BlockInfo.TYPE_FC:
			block = self.cpu.removeFC(blockInfo.blockIndex)
		elif blockInfo.blockType == BlockInfo.TYPE_FB:
			block = self.cpu.removeFB(blockInfo.blockIndex)
		elif blockInfo.blockType == BlockInfo.TYPE_DB:
			block = self.cpu.getDB(blockInfo.blockIndex)
			if block and (block.permissions & DB.PERM_WRITE) == 0:
				raise AwlSimError("Remove block: Cannot delete "
					"write protected %s." % \
					blockInfo.blockName)
			block = self.cpu.removeDB(blockInfo.blockIndex)
		elif blockInfo.blockType == BlockInfo.TYPE_UDT:
			block = self.cpu.removeUDT(blockInfo.blockIndex)
		else:
			raise AwlSimError("Remove block: Unknown bock type %d." % \
				blockInfo.blockType)
		if not block:
			raise AwlSimError("Remove block: Block %s not found." % \
				blockInfo.blockName)
		block.destroySourceRef()
		if sanityChecks:
			# Re-run sanity checks to detect missing blocks.
			self.staticSanityChecks()

class S7CPU(object): #+cdef
	"STEP 7 CPU"

	def __init__(self):
		from awlsim.core.datatypes import AwlDataType

		self.__fetchTypeMethods = self.__fetchTypeMethodsDict	#@nocy
		self.__storeTypeMethods = self.__storeTypeMethodsDict	#@nocy

		self.__sleep = time.sleep
		self.__insnMeas = None
		self.__clockMemByteOffset = None
		self.specs = S7CPUSpecs(self)
		self.conf = S7CPUConfig(self)
		self.prog = S7Prog(self)
		self.__cycleTimeTarget = 0.0
		self.setCycleTimeLimit(1.0)
		self.setCycleTimeTarget(self.__cycleTimeTarget)
		self.setCycleExitCallback(None)
		self.setBlockExitCallback(None)
		self.setPostInsnCallback(None)
		self.setPeripheralReadCallback(None)
		self.setPeripheralWriteCallback(None)
		self.setScreenUpdateCallback(None)
		self.activeLStack = None
		self.__resetBlockAllocs()
		self.reset()
		self.enableExtendedInsns(False)
		self.enableObTempPresets(False)
		self.__dateAndTimeWeekdayMap = AwlDataType.dateAndTimeWeekdayMap

	@classmethod
	def __addBlock(cls, blockList, block):
		index = block.index
		if index < 0 or index > 0xFFFF:
			raise AwlSimError("Invalid block index. "
					  "Cannot load %s %d to CPU." % (
					  block.BLOCKTYPESTR, index))
		if index >= len(blockList):
			# Re-allocate block list.
			newLen = getMSB(index) << 1
			blockList.extend([None] * (newLen - len(blockList)))
			assert(len(blockList) == newLen)
		blockList[index] = block
		return len(blockList)

	def addUDT(self, udt):
		"""Add a UDT block to the CPU.
		"""
		self.__udtsAlloc = self.__addBlock(self.__udts, udt)

	def addDB(self, db):
		"""Add a DB block to the CPU.
		"""
		self.__dbsAlloc = self.__addBlock(self.__dbs, db)

	def addOB(self, ob):
		"""Add an OB block to the CPU.
		"""
		self.__obsAlloc = self.__addBlock(self.__obs, ob)
		if ob.index == 1:
			self.__ob1 = ob

	def addFC(self, fc):
		"""Add an FC block to the CPU.
		"""
		self.__fcsAlloc = self.__addBlock(self.__fcs, fc)

	def addFB(self, fb):
		"""Add an FB block to the CPU.
		"""
		self.__fbsAlloc = self.__addBlock(self.__fbs, fb)

	def addSFC(self, sfc):
		"""Add an SFC block to the CPU.
		"""
		if sfc.index >= 0:
			self.__sfcsAlloc = self.__addBlock(self.__sfcs, sfc)
		else:
			self.__sfcsExtended[sfc.index] = sfc

	def addSFB(self, sfb):
		"""Add an SFB block to the CPU.
		"""
		if sfb.index >= 0:
			self.__sfbsAlloc = self.__addBlock(self.__sfbs, sfb)
		else:
			self.__sfbsExtended[sfb.index] = sfb

	def getUDT(self, index): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef UDT getUDT(self, uint16_t index):
		"""Get a UDT block.
		"""
		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		if index < self.__udtsAlloc: #+likely
			return self.__udts[index]
		return None

	def getDB(self, index): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef DB getDB(self, uint16_t index):
		"""Get a DB block.
		"""
		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		if index < self.__dbsAlloc: #+likely
			return self.__dbs[index]
		return None

	def getOB(self, index): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef CodeBlock getOB(self, uint16_t index):
		"""Get an OB block.
		"""
		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		if index < self.__obsAlloc: #+likely
			return self.__obs[index]
		return None

	def getFC(self, index): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef CodeBlock getFC(self, uint16_t index):
		"""Get an FC block.
		"""
		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		if index < self.__fcsAlloc: #+likely
			return self.__fcs[index]
		return None

	def getFB(self, index): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef CodeBlock getFB(self, uint16_t index):
		"""Get an FB block.
		"""
		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		if index < self.__fbsAlloc: #+likely
			return self.__fbs[index]
		return None

	def getSFC(self, index): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef CodeBlock getSFC(self, int32_t index):
		"""Get an SFC block.
		"""
#@cy		cdef int32_t sfcsAlloc
#@cy		cdef uint16_t indexU16

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		sfcsAlloc = self.__sfcsAlloc
		if index >= 0 and index < sfcsAlloc: #+likely
			indexU16 = index
			return self.__sfcs[indexU16]
		if index < 0:
			return self.__sfcsExtended.get(index, None)
		return None

	def getSFB(self, index): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef CodeBlock getSFB(self, int32_t index):
		"""Get an SFC block.
		"""
#@cy		cdef int32_t sfbsAlloc
#@cy		cdef uint16_t indexU16

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		sfbsAlloc = self.__sfbsAlloc
		if index >= 0 and index < sfbsAlloc: #+likely
			indexU16 = index
			return self.__sfbs[indexU16]
		if index < 0:
			return self.__sfbsExtended.get(index, None)
		return None

	def removeUDT(self, index):
		"""Remove a UDT block from the CPU.
		"""
		udt = self.getUDT(index)
		if udt:
			self.__udts[index] = None
		return udt

	def removeDB(self, index):
		"""Remove a DB block from the CPU.
		"""
		db = self.getDB(index)
		if db:
			self.__dbs[index] = None
		return db

	def removeOB(self, index):
		"""Remove an OB block from the CPU.
		"""
		ob = self.getOB(index)
		if ob:
			self.__obs[index] = None
		return ob

	def removeFC(self, index):
		"""Remove an FC block from the CPU.
		"""
		fc = self.getFC(index)
		if fc:
			self.__fcs[index] = None
		return fc

	def removeFB(self, index):
		"""Remove an FB block from the CPU.
		"""
		fb = self.getFB(index)
		if fb:
			self.__fbs[index] = None
		return fb

	def removeSFC(self, index):
		"""Remove an SFC block from the CPU.
		"""
		sfc = self.getSFC(index)
		if sfc:
			if index >= 0:
				self.__sfcs[index] = None
			else:
				self.__sfcsExtended.pop(index, None)
		return sfc

	def removeSFB(self, index):
		"""Remove an SFB block from the CPU.
		"""
		sfb = self.getSFB(index)
		if sfb:
			if index >= 0:
				self.__sfbs[index] = None
			else:
				self.__sfbsExtended.pop(index, None)
		return sfb

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
		self.__calcCycleTimeTargetLimited()

	def setCycleTimeTarget(self, newTarget):
		self.__cycleTimeTarget = float(newTarget)
		self.__calcCycleTimeTargetLimited()

	def __calcCycleTimeTargetLimited(self):
		self.__cycleTimeTargetLimited = min(self.__cycleTimeTarget, self.cycleTimeLimit / 2.0)

	def setRunTimeLimit(self, timeoutSeconds=-1.0):
		self.__runtimeLimit = timeoutSeconds if timeoutSeconds >= 0.0 else -1.0

	# Returns all OBs.
	def allOBs(self):
		for ob in self.__obs:
			if ob:
				yield ob

	# Returns all FBs.
	def allFBs(self):
		for fb in self.__fbs:
			if fb:
				yield fb

	# Returns all SFBs.
	def allSFBs(self):
		for sfb in itertools.chain(self.__sfbs,
					   dictValues(self.__sfbsExtended)):
			if sfb:
				yield sfb

	# Returns all FCs.
	def allFCs(self):
		for fc in self.__fcs:
			if fc:
				yield fc

	# Returns all SFCs.
	def allSFCs(self):
		for sfc in itertools.chain(self.__sfcs,
					   dictValues(self.__sfcsExtended)):
			if sfc:
				yield sfc

	# Returns all DBs.
	def allDBs(self):
		for db in self.__dbs:
			if db:
				yield db

	# Returns all UDTs.
	def allUDTs(self):
		for udt in self.__udts:
			if udt:
				yield udt

	# Returns all user defined code blocks (OBs, FBs, FCs)
	def allUserCodeBlocks(self):
		for block in itertools.chain(self.allOBs(),
					     self.allFBs(),
					     self.allFCs()):
			yield block

	# Returns all system code blocks (SFBs, SFCs)
	def allSystemCodeBlocks(self):
		for block in itertools.chain(self.allSFBs(),
					     self.allSFCs()):
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
			if insn.insnType != AwlInsnTypes.TYPE_CALL:
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
				if dataBlockOp.operType == AwlOperatorTypes.BLKREF_DB:
					dataBlock = self.getDB(dataBlockIndex)
				else:
					raise AwlSimError("Data block operand "
						"in CALL is not a DB.",
						insn=insn)
				if not dataBlock:
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

			if codeBlockOp.operType == AwlOperatorTypes.BLKREF_FC:
				codeBlock = self.getFC(codeBlockIndex)
			elif codeBlockOp.operType in {AwlOperatorTypes.BLKREF_FB,
						      AwlOperatorTypes.MULTI_FB}:
				codeBlock = self.getFB(codeBlockIndex)
			elif codeBlockOp.operType == AwlOperatorTypes.BLKREF_SFC:
				codeBlock = self.getSFC(codeBlockIndex)
			elif codeBlockOp.operType in {AwlOperatorTypes.BLKREF_SFB,
						      AwlOperatorTypes.MULTI_SFB}:
				codeBlock = self.getSFB(codeBlockIndex)
			else:
				raise AwlSimError("Code block operand "
					"in CALL is not a valid code block "
					"(FB, FC, SFB or SFC).",
					insn=insn)
			if not codeBlock:
				raise AwlSimError("Code block '%s' referenced in "
					"CALL does not exist." %\
					str(codeBlockOp),
					insn=insn)

			yield insn, codeBlock, dataBlock

	def build(self):
		"""Translate the loaded sources into their executable forms.
		"""
		self.prog.build()
		self.reallocate()

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

	def getBlockInfos(self,
			  getOBInfo=False,
			  getFCInfo=False,
			  getFBInfo=False,
			  getDBInfo=False,
			  getUDTInfo=False):
		"""Returns a list of BlockInfo()."""
		return self.prog.getBlockInfos(getOBInfo=getOBInfo,
					       getFCInfo=getFCInfo,
					       getFBInfo=getFBInfo,
					       getDBInfo=getDBInfo,
					       getUDTInfo=getUDTInfo)

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
		if force or self.specs.nrTimers != len_u32(self.timers):
			self.timers = [ Timer(self, i)
					for i in range(self.specs.nrTimers) ]
		if force or self.specs.nrCounters != len_u32(self.counters):
			self.counters = [ Counter(self, i)
					  for i in range(self.specs.nrCounters) ]
		if force or self.specs.nrFlags != len_u32(self.flags):
			self.flags = AwlMemory(self.specs.nrFlags)
		if force or self.specs.nrInputs != len_u32(self.inputs):
			self.inputs = AwlMemory(self.specs.nrInputs)
		if force or self.specs.nrOutputs != len_u32(self.outputs):
			self.outputs = AwlMemory(self.specs.nrOutputs)
		for ob in self.allOBs():
			if force or self.specs.nrLocalbytes * 8 != ob.lstack.maxAllocBits:
				ob.lstack.resize(self.specs.nrLocalbytes)

	def __resetBlockAllocs(self):
		defaultAlloc = 0x100
		self.__udtsAlloc = defaultAlloc
		self.__dbsAlloc = defaultAlloc
		self.__obsAlloc = defaultAlloc
		self.__fcsAlloc = defaultAlloc
		self.__fbsAlloc = defaultAlloc
		self.__sfcsAlloc = defaultAlloc
		self.__sfbsAlloc = defaultAlloc
		self.__udts = [None] * u32_to_s32(self.__udtsAlloc)
		self.__dbs = [None] * u32_to_s32(self.__dbsAlloc)
		self.__obs = [None] * u32_to_s32(self.__obsAlloc)
		self.__fcs = [None] * u32_to_s32(self.__fcsAlloc)
		self.__fbs = [None] * u32_to_s32(self.__fbsAlloc)
		self.__sfcs = [None] * u32_to_s32(self.__sfcsAlloc)
		self.__sfbs = [None] * u32_to_s32(self.__sfbsAlloc)
		self.__sfcsExtended = {}
		self.__sfbsExtended = {}

	def reset(self):
		self.prog.reset()
		for block in itertools.chain(self.__udts,
					     self.__dbs,
					     self.__obs,
					     self.__fcs,
					     self.__fbs):
			if block:
				block.destroySourceRef()
		self.__resetBlockAllocs()

		self.addDB(DB(0, permissions = 0)) # read/write-protected system-DB
		self.addOB(OB([], 1)) # Empty OB1

		self.obTempPresetHandlers = {
			# OB TEMP-preset handlers
			1 : OBTempPresets_table[1](self), # Default OB1 handler
			# This table is extended as OBs are loaded.
		}

		self.is4accu = False
		self.reallocate(force=True)
		self.ar1 = Addressregister()
		self.ar2 = Addressregister()
		self.db0 = self.getDB(0)
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
		self.padCycleTime = 0.0
		self.__padCycleTimeFilt = LPFilter(6)
		self.__cycleTimeMovAvg = MovingAvg(9)
		self.__speedMeasureStartTime = 0
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0

		self.initializeTimestamp()

	def setupInsnMeas(self, enable=True):
		if enable:
			if not self.__insnMeas:
				self.__insnMeas = InsnMeas()
			insnMeas = self.__insnMeas
		else:
			insnMeas = self.__insnMeas
			self.__insnMeas = None
		return insnMeas

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
#@cy	@cython.boundscheck(False)
#@cy	cdef __runOB(self, OB block):
#@cy		cdef AwlInsn insn
#@cy		cdef CallStackElem cse
#@cy		cdef CallStackElem exitCse
#@cy		cdef LStackAllocator activeLStack
#@cy		cdef uint32_t insnCount
#@cy		cdef OBTempPresets presetHandler
#@cy		cdef _Bool insnMeasEnabled
#@cy		cdef _Bool postInsnCbEnabled
#@cy		cdef _Bool blockExitCbEnabled

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

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
			presetHandler = self.obTempPresetHandlers[block.index]
			presetHandler.generate(activeLStack.memory.getRawDataBytes())

		insnMeasEnabled = self.__insnMeas is not None
		postInsnCbEnabled = self.cbPostInsn is not None
		blockExitCbEnabled = self.cbBlockExit is not None

		# Run the user program cycle
		while cse is not None:
			while cse.ip < cse.nrInsns:
				# Fetch the next instruction.
				insn = cse.insns[cse.ip]
				self.relativeJump = 1

				# Execute the instruction.
				if insnMeasEnabled: #+unlikely
					self.__insnMeas.meas(True, insn.insnType)
					insn.run()
					self.__insnMeas.meas(False, insn.insnType)
				else:
					insn.run()
				if postInsnCbEnabled: #+unlikely
					self.cbPostInsn(cse, self.cbPostInsnData)

				cse.ip += self.relativeJump
				cse = self.callStackTop
				self.__insnCount = insnCount = (self.__insnCount + 1) & 0x3FFFFFFF #+suffix-u

				# Check if a timekeeping update is required.
				if not (insnCount & self.__timestampUpdInterMask):
					self.updateTimestamp()

					# Check if the cycle time is exceeded.
					if self.now - self.cycleStartTime > self.cycleTimeLimit:
						self.__cycleTimeExceed()

					# Check if the runtime limit is enabled and exceeded.
					if self.__runtimeLimit >= 0.0:
						self.__checkRunTimeLimit()

			if blockExitCbEnabled: #+unlikely
				self.cbBlockExit(self.cbBlockExitData)
			cse, exitCse = cse.prevCse, cse
			self.callStackTop = cse
			self.callStackDepth -= 1
			exitCse.handleBlockExit()
		assert(self.callStackDepth == 0) #@nocy

		# Check if the runtime limit is enabled and exceeded.
		if self.__runtimeLimit >= 0.0:
			self.__checkRunTimeLimit()

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
				self.flags.store(self.__clockMemByteOffset,
						 constMemObj_8bit_0)

	# Run startup code
	def startup(self):
		# Build (translate) the blocks, if not already done so.
		self.build()

		self.updateTimestamp()
		self.startupTime = self.now
		self.__speedMeasureStartTime = self.now
		self.__speedMeasureStartInsnCount = 0
		self.__speedMeasureStartCycleCount = 0

		self.initClockMemState(force=True)

		# Run startup OB
		ob102 = self.getOB(102)
		ob100 = self.getOB(100)
		if ob102 and self.is4accu:
			# Cold start.
			# This is only done on 4xx-series CPUs.
			self.__runOB(ob102)
		elif ob100:
			# Warm start.
			# This really is a cold start, because remanent
			# resources were reset. However we could not execute
			# OB 102, so this is a fallback.
			# This is not 100% compliant with real CPUs, but it probably
			# is sane behavior.
			self.__runOB(ob100)

	# Run one cycle of the user program
#@cy	@cython.cdivision(True)
	def runCycle(self): #+cdef
#@cy		cdef double elapsedTime
#@cy		cdef double cycleTime
#@cy		cdef double padCycleTime
#@cy		cdef double cycleTimeDiff
#@cy		cdef double avgInsnPerCycle
#@cy		cdef double avgTimePerInsn
#@cy		cdef double insnPerSecond
#@cy		cdef uint32_t cycleCount
#@cy		cdef uint32_t insnCount
#@cy		cdef double newTimestampUpdInter

		# Run the actual OB1 code
		self.__runOB(self.__ob1)

		# Update timekeeping and statistics
		self.updateTimestamp()
		self.__cycleCount = (self.__cycleCount + 1) & 0x3FFFFFFF #+suffix-u

		# Evaluate speed measurement
		elapsedTime = self.now - self.__speedMeasureStartTime
		if elapsedTime >= 0.2:
			# Calculate instruction and cycle counts.
			cycleCount = ((self.__cycleCount - self.__speedMeasureStartCycleCount) &
				      0x3FFFFFFF) #+suffix-u
			insnCount = ((self.__insnCount - self.__speedMeasureStartInsnCount) &
				     0x3FFFFFFF) #+suffix-u

			if cycleCount > 0: #+likely
				# Get the average cycle time over the measurement period.
				cycleTime = elapsedTime / cycleCount

				# Calculate and store maximum and minimum cycle time.
				self.maxCycleTime = max(self.maxCycleTime, cycleTime)
				self.minCycleTime = min(self.minCycleTime, cycleTime)

				# Calculate and store moving average cycle time.
				self.avgCycleTime = self.__cycleTimeMovAvg.calculate(cycleTime)

				# Calculate the cycle time padding, if enabled.
				padCycleTime = 0.0
				if self.__cycleTimeTargetLimited > 0.0:
					cycleTimeDiff = self.__cycleTimeTargetLimited - cycleTime
					padCycleTime = self.__padCycleTimeFilt.run(self.padCycleTime + cycleTimeDiff)
					if padCycleTime < 0.0:
						padCycleTime = 0.0
						self.__padCycleTimeFilt.reset()
				self.padCycleTime = padCycleTime

				# Calculate instruction statistics.
				self.avgInsnPerCycle = avgInsnPerCycle = insnCount / cycleCount
				if avgInsnPerCycle > 0.0:
					avgTimePerInsn = self.avgCycleTime / avgInsnPerCycle
					if avgTimePerInsn > 0.0:
						self.insnPerSecond = insnPerSecond = 1.0 / avgTimePerInsn
					else:
						self.insnPerSecond = insnPerSecond = 0.0
				else:
					self.insnPerSecond = insnPerSecond = 0.0

				# Re-calculate the timestamp update interval.
				if insnPerSecond > 0.0:
					# The desired timestamp update interval is at least once per millisecond.
					# Reduce the calculated value by 10% to compensate for jitter.
					newTimestampUpdInter = (insnPerSecond / 1000.0) * 0.9
					# Get the average of the current and the new update interval
					newTimestampUpdInter = self.__timestampUpdMovAvg.calculate(newTimestampUpdInter)
					# Limit the update interval
					newTimestampUpdInter = min(max(newTimestampUpdInter, 32.0), 65536.0)
					self.__timestampUpdInter = newTimestampUpdInter
					# Calculate the instruction counter mask that triggers
					# the call to updateTimestamp()
					self.__timestampUpdInterMask = getMSB(int(newTimestampUpdInter)) - 1

				# Reset the counters
				self.__speedMeasureStartTime = self.now
				self.__speedMeasureStartInsnCount = self.__insnCount
				self.__speedMeasureStartCycleCount = self.__cycleCount

		# Call the cycle exit callback, if any.
		if self.cbCycleExit is not None:
			self.cbCycleExit(self.cbCycleExitData)

	# Sleep for the cycle padding duration, if required.
	def sleepCyclePadding(self): #+cdef
		if self.padCycleTime > 0.0:
			self.__sleep(self.padCycleTime)

	# Returns 'self.now' as 31 bit millisecond representation.
	# That is data type 'TIME'.
	# The returned value will always be positive and wrap
	# from 0x7FFFFFFF to 0.
	@property
	def now_TIME(self):
		return int(self.now * 1000.0) & 0x7FFFFFFF

	# Initialize time stamp.
	def initializeTimestamp(self):
		# Initialize the timestamp update interval to a small constant.
		self.__timestampUpdMovAvg = MovingAvg(9)
		self.__timestampUpdInter = 64
		self.__timestampUpdInterMask = getMSB(int(self.__timestampUpdInter)) - 1

		# Initialize the time stamp so that it will
		# overflow 31 bit millisecond count within
		# 100 milliseconds after startup.
		# An 31 bit overflow happens after 0x7FFFFFFF ms,
		# which is 2147483647 ms, which is 2147483.647 s.
		# Create an offset to 'self.now' that is added every
		# time 'self.now' is updated.
		now = monotonic_time()
		self.__nowOffset = -(now) + (2147483.647 - 0.1)
		self.now = now = now + self.__nowOffset
		self.startupTime = now
		self.updateTimestamp()

	# updateTimestamp() updates self.now, which is a
	# floating point count of seconds.
	def updateTimestamp(self, _getTime=monotonic_time): #@nocy
#@cy	cdef updateTimestamp(self):
#@cy		cdef uint32_t value
#@cy		cdef uint32_t count
#@cy		cdef double now

		# Update the system time
		now = _getTime() #@nocy
#@cy		now = monotonic_time()
		self.now = now = now + self.__nowOffset

		# Update the clock memory byte
		if self.__clockMemByteOffset is not None and\
		   now >= self.__nextClockMemTime:
			try:
				self.__nextClockMemTime += 0.05
				value = AwlMemoryObject_asScalar(
					self.flags.fetch(self.__clockMemByteOffset, 8))
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
				self.flags.store(self.__clockMemByteOffset,
						 make_AwlMemoryObject_fromScalar8(value))
			except AwlSimError as e:
				raise AwlSimError("Failed to generate clock "
					"memory signal:\n" + str(e) +\
					"\n\nThe configured clock memory byte "
					"address might be invalid." )

	def __cycleTimeExceed(self): #+cdef
		raise AwlSimError("Cycle time exceed %.3f seconds" % (
				  self.cycleTimeLimit))

	def __checkRunTimeLimit(self): #+cdef
		if (self.__runtimeLimit >= 0.0 and
		    self.now - self.startupTime >= self.__runtimeLimit):
			raise MaintenanceRequest(MaintenanceRequest.TYPE_RTTIMEOUT,
						 "CPU runtime timeout")

	# Make a DATE_AND_TIME for the current wall-time and
	# store it in byteArray, which is a bytearray or compatible.
	# If byteArray is smaller than 8 bytes, an IndexError is raised.
	def makeCurrentDateAndTime(self, byteArray, offset): #@nocy
#@cy	cdef makeCurrentDateAndTime(self, uint8_t *byteArray, uint32_t offset):
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
		cse = self.callStackTop
		if cse is None:
			return None #@nocov
		return cse.ip

	def getCurrentInsn(self):
		try:
			cse = self.callStackTop
			if not cse:
				return None #@nocov
			return cse.insns[cse.ip]
		except IndexError as e: #@nocov
			return None

	# Translate a label index into a relative jump.
	# labelIndex must be within the bounds of self.callStackTop.block.labels
	def labelIdxToRelJump(self, labelIndex): #@nocy
#@cy	@cython.boundscheck(False)
#@cy	cdef int32_t labelIdxToRelJump(self, uint32_t labelIndex):
#@cy		cdef CallStackElem cse
#@cy		cdef AwlLabel label

		# Note: Bounds checking of the indexing operator [] is disabled
		#       by @cython.boundscheck(False) in this method.

		# Translate a label index into a relative IP offset.
		cse = self.callStackTop
		if labelIndex < cse.block.nrLabels: #+likely
			label = cse.block.labels[labelIndex]
			return label.insn.ip - cse.ip

		# labelIndex is invalid.
		# This is an error that must never happen.
		raise AwlSimBug("labelIdxToRelJump: labelIndex out of range.") #@nocy
#@cy		return 1

	# Jump to a label.
	# labelIndex must be within the bounds of self.callStackTop.block.labels
	def jumpToLabel(self, labelIndex): #@nocy
#@cy	cdef void jumpToLabel(self, uint32_t labelIndex):
		self.relativeJump = self.labelIdxToRelJump(labelIndex)

	def jumpRelative(self, insnOffset): #@nocy
#@cy	cdef void jumpRelative(self, int32_t insnOffset):
		self.relativeJump = insnOffset

	def __call_FC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_FC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CodeBlock fc
#@cy		cdef uint16_t fcNumber

		fcNumber = blockOper.offset.byteOffset
		fc = self.getFC(fcNumber)
		if fc is None: #+unlikely
			return None

		return make_CallStackElem(self, fc, None, None, parameters, False)

	def __call_RAW_FC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_FC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CodeBlock fc
#@cy		cdef uint16_t fcNumber

		fcNumber = blockOper.offset.byteOffset
		fc = self.getFC(fcNumber)
		if fc is None: #+unlikely
			return None

		return make_CallStackElem(self, fc, None, None, (), True)

	def __call_FB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_FB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CallStackElem cse
#@cy		cdef CodeBlock fb
#@cy		cdef DB db
#@cy		cdef uint16_t fbNumber
#@cy		cdef uint16_t dbNumber

		fbNumber = blockOper.offset.byteOffset
		fb = self.getFB(fbNumber)
		if fb is None: #+unlikely
			return None
		dbNumber = dbOper.offset.byteOffset
		db = self.getDB(dbNumber)
		if db is None: #+unlikely
			return None

		cse = make_CallStackElem(self, fb, db, make_AwlOffset(0, 0), parameters, False)
		self.dbRegister, self.diRegister = self.diRegister, db

		return cse

	def __call_RAW_FB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_FB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CodeBlock fb
#@cy		cdef uint16_t fbNumber

		fbNumber = blockOper.offset.byteOffset
		fb = self.getFB(fbNumber)
		if fb is None: #+unlikely
			return None

		return make_CallStackElem(self, fb, self.diRegister, None, (), True)

	def __call_SFC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_SFC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CodeBlock sfc
#@cy		cdef int32_t sfcNumber

		sfcNumber = blockOper.offset.byteOffset
		sfc = self.getSFC(sfcNumber)
		if sfc is None: #+unlikely
			return None

		return make_CallStackElem(self, sfc, None, None, parameters, False)

	def __call_RAW_SFC(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_SFC(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CodeBlock sfc
#@cy		cdef int32_t sfcNumber

		sfcNumber = blockOper.offset.byteOffset
		sfc = self.getSFC(sfcNumber)
		if sfc is None: #+unlikely
			return None

		return make_CallStackElem(self, sfc, None, None, (), True)

	def __call_SFB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_SFB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CallStackElem cse
#@cy		cdef CodeBlock sfb
#@cy		cdef DB db
#@cy		cdef int32_t sfbNumber
#@cy		cdef uint16_t dbNumber

		sfbNumber = blockOper.offset.byteOffset
		sfb = self.getSFB(sfbNumber)
		if sfb is None: #+unlikely
			return None
		dbNumber = dbOper.offset.byteOffset
		db = self.getDB(dbNumber)
		if db is None: #+unlikely
			return None

		cse = make_CallStackElem(self, sfb, db, make_AwlOffset(0, 0), parameters, False)
		self.dbRegister, self.diRegister = self.diRegister, db

		return cse

	def __call_RAW_SFB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_RAW_SFB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CodeBlock sfb
#@cy		cdef int32_t sfbNumber

		sfbNumber = blockOper.offset.byteOffset
		sfb = self.getSFB(sfbNumber)
		if sfb is None: #+unlikely
			return None

		return make_CallStackElem(self, sfb, self.diRegister, None, (), True)

	def __call_INDIRECT(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_INDIRECT(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef CallStackElem cse
#@cy		cdef uint32_t operType

		blockOper = blockOper.resolve(True)
		operType = blockOper.operType

		if operType == AwlOperatorTypes.BLKREF_FC:
			cse = self.__call_RAW_FC(blockOper, dbOper, parameters)
		elif operType == AwlOperatorTypes.BLKREF_FB:
			cse = self.__call_RAW_FB(blockOper, dbOper, parameters)
		elif operType == AwlOperatorTypes.BLKREF_SFC:
			cse = self.__call_RAW_SFC(blockOper, dbOper, parameters)
		elif operType == AwlOperatorTypes.BLKREF_SFB:
			cse = self.__call_RAW_SFB(blockOper, dbOper, parameters)
		else:
			raise AwlSimError("Invalid CALL operand")
		if cse is None:
			raise AwlSimError("Code block %d not found in indirect call" % (
					  blockOper.offset.byteOffset))
		return cse

	def __call_MULTI_FB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_MULTI_FB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef AwlOffset base
#@cy		cdef CallStackElem cse
#@cy		cdef CodeBlock fb
#@cy		cdef uint16_t fbNumber

		fbNumber = blockOper.offset.fbNumber
		fb = self.getFB(fbNumber)
		if fb is None: #+unlikely
			return None

		base = make_AwlOffset_fromPointerValue(self.ar2.get())
		base.iadd(blockOper.offset)
		cse = make_CallStackElem(self, fb, self.diRegister, base, parameters, False)
		self.dbRegister = self.diRegister

		return cse

	def __call_MULTI_SFB(self, blockOper, dbOper, parameters): #@nocy
#@cy	cdef CallStackElem __call_MULTI_SFB(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters):
#@cy		cdef AwlOffset base
#@cy		cdef CallStackElem cse
#@cy		cdef CodeBlock sfb
#@cy		cdef int32_t sfbNumber

		sfbNumber = blockOper.offset.fbNumber
		sfb = self.getSFB(sfbNumber)
		if sfb is None: #+unlikely
			return None

		base = make_AwlOffset_fromPointerValue(self.ar2.get())
		base.iadd(blockOper.offset)
		cse = make_CallStackElem(self, sfb, self.diRegister, base, parameters, False)
		self.dbRegister = self.diRegister

		return cse

	def run_CALL(self, blockOper, dbOper, parameters, raw): #@nocy
#@cy	cdef run_CALL(self, AwlOperator blockOper, AwlOperator dbOper, tuple parameters, _Bool raw):
#@cy		cdef CallStackElem newCse
#@cy		cdef uint32_t callStackDepth
#@cy		cdef uint32_t operType

		callStackDepth = self.callStackDepth
		if callStackDepth >= self.specs.callStackSize:
			raise AwlSimError("Maximum CALL stack depth of %d CALLs exceed." % (
				self.specs.callStackSize))

		operType = blockOper.operType
		if raw: #+unlikely
			if operType == AwlOperatorTypes.BLKREF_FC:
				newCse = self.__call_RAW_FC(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.BLKREF_FB:
				newCse = self.__call_RAW_FB(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.BLKREF_SFC:
				newCse = self.__call_RAW_SFC(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.BLKREF_SFB:
				newCse = self.__call_RAW_SFB(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.INDIRECT:
				newCse = self.__call_INDIRECT(blockOper, dbOper, parameters)
			else:
				raise AwlSimError("Invalid CALL operand")
		else:
			if operType == AwlOperatorTypes.BLKREF_FC:
				newCse = self.__call_FC(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.BLKREF_FB:
				newCse = self.__call_FB(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.BLKREF_SFC:
				newCse = self.__call_SFC(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.BLKREF_SFB:
				newCse = self.__call_SFB(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.MULTI_FB:
				newCse = self.__call_MULTI_FB(blockOper, dbOper, parameters)
			elif operType == AwlOperatorTypes.MULTI_SFB:
				newCse = self.__call_MULTI_SFB(blockOper, dbOper, parameters)
			else:
				raise AwlSimError("Invalid CALL operand")
		if newCse is None:
			# This shall never happen.
			raise AwlSimBug("CALL failed to construct call stack element.")

		newCse.prevCse = self.callStackTop
		self.callStackTop = newCse
		self.callStackDepth = callStackDepth + 1 #+suffix-u

	def run_BE(self): #@nocy
#@cy	cdef void run_BE(self):
#@cy		cdef S7StatusWord s

		# This method is declared void and thus must not raise an exception.

		s = self.statusWord
		s.OS, s.OR, s.STA, s.NER = 0, 0, 1, 0
		# Jump beyond end of block
		self.relativeJump = self.callStackTop.nrInsns - self.callStackTop.ip

	def openDB(self, dbNumber, openDI): #@nocy
#@cy	cdef openDB(self, int32_t dbNumber, _Bool openDI):
#@cy		cdef DB db

		if dbNumber <= 0:
			if openDI:
				self.diRegister = self.db0
			else:
				self.dbRegister = self.db0
		else:
			db = self.getDB(dbNumber)
			if db is None:
				raise AwlSimError("Datablock %i does not exist" % dbNumber)
			if openDI:
				self.diRegister = db
			else:
				self.dbRegister = db

	def run_AUF(self, dbOper): #@nocy
#@cy	cdef run_AUF(self, AwlOperator dbOper):
#@cy		cdef _Bool openDI
#@cy		cdef uint32_t operType

		dbOper = dbOper.resolve(True)

		operType = dbOper.operType
		if operType == AwlOperatorTypes.BLKREF_DB:
			openDI = False
		elif operType == AwlOperatorTypes.BLKREF_DI:
			openDI = True
		else:
			raise AwlSimError("Invalid DB reference in AUF")

		self.openDB(dbOper.offset.byteOffset, openDI)

	def run_TDB(self): #@nocy
#@cy	cdef void run_TDB(self):
		# Swap global and instance DB.
		# This method is declared void and thus must not raise an exception.
		self.diRegister, self.dbRegister = self.dbRegister, self.diRegister

	def getAccu(self, index): #@nocy
#@cy	cdef Accu getAccu(self, uint32_t index):
		if index == 1:
			return self.accu1
		elif index == 2:
			return self.accu2
		if self.specs.nrAccus > 2:
			if index == 3:
				return self.accu3
			elif index == 4:
				return self.accu4
		raise AwlSimError("Invalid ACCU offset") #@nocov

	def getAR(self, index): #@nocy
#@cy	cdef Addressregister getAR(self, uint32_t index):
		if index == 1:
			return self.ar1
		elif index == 2:
			return self.ar2
		raise AwlSimError("Invalid AR offset") #@nocov

	def getTimer(self, index): #@nocy
#@cy	cdef Timer getTimer(self, uint32_t index):
		if index >= len_u32(self.timers):
			raise AwlSimError("Fetched invalid timer %d" % index) #@nocov
		return self.timers[index]

	def getCounter(self, index): #@nocy
#@cy	cdef Counter getCounter(self, uint32_t index):
		if index >= len_u32(self.counters):
			raise AwlSimError("Fetched invalid counter %d" % index) #@nocov
		return self.counters[index]

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
		if not self.mcrStack:
			raise AwlSimError("MCR stack underflow")
		self.mcrStack.pop()

	def __translateFCNamedLocalOper(self, operator, store): #@nocy
#@cy	cdef AwlOperator __translateFCNamedLocalOper(self, AwlOperator operator, _Bool store):
#@cy		cdef uint32_t pointer
#@cy		cdef int32_t opType
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
			dbNr = AwlMemoryObject_asScalar(
					self.fetch(dbPtrOp,
						   AwlOperatorWidths.WIDTH_MASK_16))
			dbPtrOp.offset.byteOffset += 2
			dbPtrOp.width = 32
			pointer = AwlMemoryObject_asScalar(
					self.fetch(dbPtrOp,
						   AwlOperatorWidths.WIDTH_MASK_32))
			# Open the DB pointed to by the DB-ptr.
			# (This is ok, if dbNr is 0, too)
			self.openDB(dbNr, False)
			# Make an operator from the DB-ptr.
			opType = AwlIndirectOpConst.area2optype(
					(pointer & PointerConst.AREA_MASK_S),
					False)
			if opType < 0: #+unlikely
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
			finalOp.offset.iadd(subOffset)
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
#@cy	cdef bytearray fetchOutputRange(self, uint32_t byteOffset, uint32_t byteCount):
		if byteOffset + byteCount > self.specs.nrOutputs: #@nocy
#@cy		if <uint64_t>byteOffset + <uint64_t>byteCount > <uint64_t>self.specs.nrOutputs:
			raise AwlSimError("Fetch from output process image region "
				"is out of range "
				"(imageSize=%d, fetchOffset=%d, fetchSize=%d)." % (
				self.specs.nrOutputs, byteOffset, byteCount))
		return self.outputs.getRawDataBytes()[byteOffset : byteOffset + byteCount]

	# Same as fetchOutputRange(), but fetches only a single byte.
	def fetchOutputByte(self, byteOffset): #@nocy
#@cy	cdef uint8_t fetchOutputByte(self, uint32_t byteOffset):
		if byteOffset >= self.specs.nrOutputs:
			raise AwlSimError("Fetch of output process image byte "
				"is out of range "
				"(imageSize=%d, fetchOffset=%d)." % (
				self.specs.nrOutputs, byteOffset))
		return self.outputs.getRawDataBytes()[byteOffset]

	# Fetch a range in the 'input' memory area.
	# 'byteOffset' is the byte offset into the input area.
	# 'byteCount' is the number if bytes to fetch.
	# Returns a bytearray.
	# This raises an AwlSimError, if the access if out of range.
	def fetchInputRange(self, byteOffset, byteCount): #@nocy
#@cy	cdef bytearray fetchInputRange(self, uint32_t byteOffset, uint32_t byteCount):
		if byteOffset + byteCount > self.specs.nrInputs: #@nocy
#@cy		if <uint64_t>byteOffset + <uint64_t>byteCount > <uint64_t>self.specs.nrInputs:
			raise AwlSimError("Fetch from input process image region "
				"is out of range "
				"(imageSize=%d, fetchOffset=%d, fetchSize=%d)." % (
				self.specs.nrInputs, byteOffset, byteCount))
		return self.inputs.getRawDataBytes()[byteOffset : byteOffset + byteCount]

	# Same as fetchInputRange(), but fetches only a single byte.
	def fetchInputByte(self, byteOffset): #@nocy
#@cy	cdef uint8_t fetchInputByte(self, uint32_t byteOffset):
		if byteOffset >= self.specs.nrInputs:
			raise AwlSimError("Fetch of input process image byte "
				"is out of range "
				"(imageSize=%d, fetchOffset=%d)." % (
				self.specs.nrInputs, byteOffset))
		return self.inputs.getRawDataBytes()[byteOffset]

	# Store a range in the 'input' memory area.
	# 'byteOffset' is the byte offset into the input area.
	# 'data' is a bytearray.
	# This raises an AwlSimError, if the access if out of range.
	def storeInputRange(self, byteOffset, data): #@nocy
#@cy	cdef storeInputRange(self, uint32_t byteOffset, bytearray data):
#@cy		cdef uint32_t dataLen
#@cy		cdef uint8_t *dataBytes

		dataLen = len(data)
		if byteOffset + dataLen > self.specs.nrInputs: #@nocy
#@cy		if <uint64_t>byteOffset + <uint64_t>dataLen > <uint64_t>self.specs.nrInputs:
			raise AwlSimError("Store to input process image region "
				"is out of range "
				"(imageSize=%d, storeOffset=%d, storeSize=%d)." % (
				self.specs.nrInputs, byteOffset, dataLen))
		dataBytes = self.inputs.getRawDataBytes()
		dataBytes[byteOffset : byteOffset + dataLen] = data #@nocy
#@cy		memcpy(&dataBytes[byteOffset], <const char *>data, dataLen)

	# Same as storeInputRange(), but stores only a single byte.
	def storeInputByte(self, byteOffset, data): #@nocy
#@cy	cdef storeInputByte(self, uint32_t byteOffset, uint8_t data):
		if byteOffset >= self.specs.nrInputs:
			raise AwlSimError("Store to input process image byte "
				"is out of range "
				"(imageSize=%d, storeOffset=%d)." % (
				self.specs.nrInputs, byteOffset))
		dataBytes = self.inputs.getRawDataBytes()[byteOffset] = data

	def fetch(self, operator, allowedWidths):					#@nocy
		try:									#@nocy
			fetchMethod = self.__fetchTypeMethods[operator.operType]	#@nocy
		except KeyError:							#@nocy #@nocov
			self.__invalidFetch(operator)					#@nocy
		return fetchMethod(self, operator, allowedWidths)			#@nocy

#@cy	cdef AwlMemoryObject fetch(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
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

	def __invalidFetch(self, operator): #@nocov
		raise AwlSimError("Invalid fetch request: %s" % str(operator))

	def __fetchWidthError(self, operator, allowedWidths):
		raise AwlSimError("Data fetch of %d bits, "
			"but only %s bits are allowed." %\
			(operator.width,
			 listToHumanStr(AwlOperatorWidths.maskToList(allowedWidths))))

	def __fetchIMM(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchIMM(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(operator.immediate,
						       operator.width)

	def __fetchIMM_DT(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchIMM_DT(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromBytes(operator.immediateBytes,
						      operator.width)

	def __fetchIMM_PTR(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchIMM_PTR(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromGeneric(
			operator.pointer.toNativePointerValue(),
			operator.pointer.width)

	def __fetchIMM_STR(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchIMM_STR(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
#@cy		cdef uint32_t insnType

		if operator.width <= 48 and operator.insn is not None:
			insnType = operator.insn.insnType
			if insnType == AwlInsnTypes.TYPE_L or\
			   insnType >= AwlInsnTypes.TYPE_EXTENDED:
				# This is a special 0-4 character fetch (L) that
				# is transparently translated into an integer.
				if operator.width <= 16:
					return constMemObj_8bit_0
				return make_AwlMemoryObject_fromBytes(operator.immediateBytes[2:],
								      operator.width - 16)

		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromBytes(operator.immediateBytes,
						      operator.width)

	def __fetchDBLG(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchDBLG(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			self.dbRegister.struct.getSize(),
			operator.width)

	def __fetchDBNO(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchDBNO(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(self.dbRegister.index,
						       operator.width)

	def __fetchDILG(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchDILG(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			self.diRegister.struct.getSize(),
			operator.width)

	def __fetchDINO(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchDINO(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(self.diRegister.index,
						       operator.width)

	def __fetchAR2(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchAR2(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(self.getAR(2).get(),
						       operator.width)

	def __fetchSTW(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		if operator.width == 1:
			return make_AwlMemoryObject_fromScalar1(
				self.statusWord.getByBitNumber(operator.offset.bitOffset))
		elif operator.width == 16:
			return make_AwlMemoryObject_fromScalar16(
				self.statusWord.getWord())
		else:
			assert(0)

	def __fetchSTW_Z(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW_Z(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			((self.statusWord.A0 ^ 1) & (self.statusWord.A1 ^ 1)),
			operator.width)

	def __fetchSTW_NZ(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW_NZ(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			(self.statusWord.A0 | self.statusWord.A1),
			operator.width)

	def __fetchSTW_POS(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW_POS(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			((self.statusWord.A0 ^ 1) & self.statusWord.A1),
			operator.width)

	def __fetchSTW_NEG(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW_NEG(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			(self.statusWord.A0 & (self.statusWord.A1 ^ 1)),
			operator.width)

	def __fetchSTW_POSZ(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW_POSZ(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			(self.statusWord.A0 ^ 1),
			operator.width)

	def __fetchSTW_NEGZ(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW_NEGZ(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			(self.statusWord.A1 ^ 1),
			operator.width)

	def __fetchSTW_UO(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchSTW_UO(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			(self.statusWord.A0 & self.statusWord.A1),
			operator.width)

	def __fetchE(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchE(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.inputs.fetch(operator.offset, operator.width)

	def __fetchA(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchA(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.outputs.fetch(operator.offset, operator.width)

	def __fetchM(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchM(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return self.flags.fetch(operator.offset, operator.width)

	def __fetchL(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchL(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
#@cy		cdef LStackAllocator lstack

		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		lstack = self.activeLStack
		return lstack.memory.fetch(lstack.topFrameOffset.add(operator.offset),
					   operator.width)

	def __fetchVL(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchVL(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
#@cy		cdef CallStackElem cse
#@cy		cdef LStackAllocator lstack
#@cy		cdef LStackFrame *prevFrame

		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		lstack = self.activeLStack
		prevFrame = lstack.topFrame.prevFrame
		if not prevFrame:
			raise AwlSimError("Fetch of parent localstack, "
				"but no parent present.")
		return lstack.memory.fetch(operator.offset.addInt(prevFrame.byteOffset, 0),
					   operator.width)

	def __fetchDB(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchDB(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
#@cy		cdef int32_t dbNumber

		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		dbNumber = operator.offset.dbNumber
		if dbNumber >= 0:
			# This is a fully qualified access (DBx.DBx X)
			# Open the data block first.
			self.openDB(dbNumber, False)
		return self.dbRegister.fetch(operator, None)

	def __fetchDI(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchDI(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		if self.callStackTop.block.isFB:
			# Fetch the data using the multi-instance base offset from AR2.
			return self.diRegister.fetch(operator,
						     make_AwlOffset_fromPointerValue(self.ar2.get()))
		# Fetch without base offset.
		return self.diRegister.fetch(operator, None)

	def __fetchPE(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchPE(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
#@cy		cdef bytearray readBytes
#@cy		cdef uint32_t bitWidth
#@cy		cdef AwlOffset operatorOffset
#@cy		cdef _Bool isInProcImg
#@cy		cdef AwlMemoryObject memObj

		bitWidth = operator.width
		if not (makeAwlOperatorWidthMask(bitWidth) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)
		operatorOffset = operator.offset

		isInProcImg = operatorOffset.toLongBitOffset() + bitWidth < self.specs.nrInputs * 8

		# Fetch the data from the peripheral device.
		readBytes = self.cbPeripheralRead(self.cbPeripheralReadData,
						  bitWidth,
						  operatorOffset.byteOffset)
		if not readBytes:
			printError("There is no hardware to handle "
				"the direct peripheral fetch. "
				"(width=%d, offset=%d)" %\
				(bitWidth, operatorOffset.byteOffset))
			# Read the value from the current process image instead,
			# if it is within the range of the process image.
			# Otherwise return all-zeros.
			if isInProcImg:
				readBytes = self.fetchInputRange(operatorOffset.byteOffset,
								 bitWidth // 8)
			else:
				readBytes = bytearray(bitWidth // 8)
		memObj = make_AwlMemoryObject_fromBytes(readBytes, bitWidth)

		# Store the data to the process image, if it is within the inputs range.
		if isInProcImg:
			self.inputs.store(operatorOffset, memObj)

		return memObj

	def __fetchT(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchT(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
#@cy		cdef uint32_t insnType
#@cy		cdef uint32_t width

		insnType = operator.insn.insnType
		if insnType == AwlInsnTypes.TYPE_L or\
		   insnType == AwlInsnTypes.TYPE_LC:
			width = 32
		else:
			width = 1
		if not (makeAwlOperatorWidthMask(width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		timer = self.getTimer(operator.offset.byteOffset)
		if insnType == AwlInsnTypes.TYPE_L:
			return make_AwlMemoryObject_fromScalar16(timer.getTimevalBin())
		elif insnType == AwlInsnTypes.TYPE_LC:
			return make_AwlMemoryObject_fromScalar16(timer.getTimevalS5T())
		return make_AwlMemoryObject_fromScalar1(timer.get())

	def __fetchZ(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchZ(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
#@cy		cdef uint32_t insnType
#@cy		cdef uint32_t width

		insnType = operator.insn.insnType
		if insnType == AwlInsnTypes.TYPE_L or\
		   insnType == AwlInsnTypes.TYPE_LC:
			width = 32
		else:
			width = 1
		if not (makeAwlOperatorWidthMask(width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		counter = self.getCounter(operator.offset.byteOffset)
		if insnType == AwlInsnTypes.TYPE_L:
			return make_AwlMemoryObject_fromScalar16(counter.getValueBin())
		elif insnType == AwlInsnTypes.TYPE_LC:
			return make_AwlMemoryObject_fromScalar16(counter.getValueBCD())
		return make_AwlMemoryObject_fromScalar1(counter.get())

	def __fetchNAMED_LOCAL(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchNAMED_LOCAL(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		# load from an FC interface field.
		return self.fetch(self.__translateFCNamedLocalOper(operator, False),
				  allowedWidths)

	def __fetchNAMED_LOCAL_PTR(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchNAMED_LOCAL_PTR(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		assert(operator.offset.subOffset is None) #@nocy
		return make_AwlMemoryObject_fromScalar32(
			self.callStackTop.getInterfIdxOper(operator.interfaceIndex).resolve(False).makePointerValue())

	def __fetchNAMED_DBVAR(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchNAMED_DBVAR(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		# All legit accesses will have been translated to absolute addressing already
		raise AwlSimError("Fully qualified load from DB variable "	#@nocov
			"is not supported in this place.")			#@nocov

	def __fetchINDIRECT(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchINDIRECT(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		return self.fetch(operator.resolve(False), allowedWidths)

	def __fetchVirtACCU(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchVirtACCU(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			self.getAccu(operator.offset.byteOffset).get(),
			operator.width)

	def __fetchVirtAR(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchVirtAR(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		return make_AwlMemoryObject_fromScalar(
			self.getAR(operator.offset.byteOffset).get(),
			operator.width)

	def __fetchVirtDBR(self, operator, allowedWidths): #@nocy
#@cy	cdef AwlMemoryObject __fetchVirtDBR(self, AwlOperator operator, uint32_t allowedWidths) except NULL:
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__fetchWidthError(operator, allowedWidths)

		if operator.offset.byteOffset == 1:
			if self.dbRegister:
				return make_AwlMemoryObject_fromScalar(
					self.dbRegister.index,
					operator.width)
		elif operator.offset.byteOffset == 2:
			if self.diRegister:
				return make_AwlMemoryObject_fromScalar(
					self.diRegister.index,
					operator.width)
		else:
			raise AwlSimError("Invalid __DBR %d. "
				"Must be 1 for DB-register or "
				"2 for DI-register." %\
				operator.offset.byteOffset)
		return constMemObj_16bit_0

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

	def store(self, operator, memObj, allowedWidths):				#@nocy
		try:									#@nocy
			storeMethod = self.__storeTypeMethods[operator.operType]	#@nocy
		except KeyError:							#@nocy #@nocov
			self.__invalidStore(operator)					#@nocy
		storeMethod(self, operator, memObj, allowedWidths)			#@nocy

#@cy	cdef store(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
#@cy		cdef uint32_t operType
#@cy
#@cy		operType = operator.operType
#@cy		if operType == AwlOperatorTypes.MEM_E:
#@cy			self.__storeE(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_A:
#@cy			self.__storeA(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_M:
#@cy			self.__storeM(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_L:
#@cy			self.__storeL(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_VL:
#@cy			self.__storeVL(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DB:
#@cy			self.__storeDB(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_DI:
#@cy			self.__storeDI(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_PA:
#@cy			self.__storePA(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_AR2:
#@cy			self.__storeAR2(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.MEM_STW:
#@cy			self.__storeSTW(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.NAMED_LOCAL:
#@cy			self.__storeNAMED_LOCAL(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.NAMED_DBVAR:
#@cy			self.__storeNAMED_DBVAR(operator, memObj, allowedWidths)
#@cy		elif operType == AwlOperatorTypes.INDIRECT:
#@cy			self.__storeINDIRECT(operator, memObj, allowedWidths)
#@cy		else:
#@cy			self.__invalidStore(operator)

	def __invalidStore(self, operator): #@nocov
		raise AwlSimError("Invalid store request: %s" % str(operator))

	def __storeWidthError(self, operator, allowedWidths):
		raise AwlSimError("Data store of %d bits, "
			"but only %s bits are allowed." %\
			(operator.width,
			 listToHumanStr(AwlOperatorWidths.maskToList(allowedWidths))))

	def __storeE(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeE(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		AwlMemoryObject_assertWidth(memObj, operator.width)
		self.inputs.store(operator.offset, memObj)

	def __storeA(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeA(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		AwlMemoryObject_assertWidth(memObj, operator.width)
		self.outputs.store(operator.offset, memObj)

	def __storeM(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeM(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		AwlMemoryObject_assertWidth(memObj, operator.width)
		self.flags.store(operator.offset, memObj)

	def __storeL(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeL(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
#@cy		cdef LStackAllocator lstack

		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		AwlMemoryObject_assertWidth(memObj, operator.width)
		lstack = self.activeLStack
		lstack.memory.store(lstack.topFrameOffset.add(operator.offset),
				    memObj)

	def __storeVL(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeVL(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
#@cy		cdef CallStackElem cse
#@cy		cdef LStackFrame *prevFrame

		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		AwlMemoryObject_assertWidth(memObj, operator.width)
		lstack = self.activeLStack
		prevFrame = lstack.topFrame.prevFrame
		if not prevFrame:
			raise AwlSimError("Store to parent localstack, "
				"but no parent present.")
		lstack.memory.store(operator.offset.addInt(prevFrame.byteOffset, 0),
				    memObj)

	def __storeDB(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeDB(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
#@cy		cdef DB db
#@cy		cdef int32_t dbNumber

		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		dbNumber = operator.offset.dbNumber
		if dbNumber < 0:
			db = self.dbRegister
		else:
			db = self.getDB(dbNumber)
			if db is None:
				raise AwlSimError("Store to DB %d, but DB "
					"does not exist" % dbNumber)
		db.store(operator, memObj, None)

	def __storeDI(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeDI(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		if self.callStackTop.block.isFB:
			# Store the data using the multi-instance base offset from AR2.
			self.diRegister.store(operator, memObj,
					      make_AwlOffset_fromPointerValue(self.ar2.get()))
		else:
			# Store without base offset.
			self.diRegister.store(operator, memObj, None)

	def __storePA(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storePA(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
#@cy		cdef _Bool ok
#@cy		cdef uint32_t bitWidth
#@cy		cdef AwlOffset operatorOffset

		bitWidth = operator.width
		if not (makeAwlOperatorWidthMask(bitWidth) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)
		operatorOffset = operator.offset

		# Store the data to the process image, if it is within the outputs range.
		if operatorOffset.toLongBitOffset() + bitWidth < self.specs.nrOutputs * 8:
			self.outputs.store(operatorOffset, memObj)

		# Store the data to the peripheral device.
		ok = self.cbPeripheralWrite(self.cbPeripheralWriteData,
					    bitWidth,
					    operatorOffset.byteOffset,
					    AwlMemoryObject_asBytes(memObj))
		if not ok:
			printError("There is no hardware to handle "
				"the direct peripheral store. "
				"(width=%d, offset=%d)" %\
				(bitWidth, operatorOffset.byteOffset))

	def __storeAR2(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeAR2(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		self.getAR(2).set(AwlMemoryObject_asScalar(memObj))

	def __storeSTW(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeSTW(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		if not (makeAwlOperatorWidthMask(operator.width) & allowedWidths):
			self.__storeWidthError(operator, allowedWidths)

		if operator.width == 1:
			raise AwlSimError("Cannot store to individual STW bits")
		elif operator.width == 16:
			self.statusWord.setWord(AwlMemoryObject_asScalar(memObj))
		else:
			assert(0)

	def __storeNAMED_LOCAL(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeNAMED_LOCAL(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		# store to an FC interface field.
		self.store(self.__translateFCNamedLocalOper(operator, True),
			   memObj, allowedWidths)

	def __storeNAMED_DBVAR(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeNAMED_DBVAR(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		# All legit accesses will have been translated to absolute addressing already
		raise AwlSimError("Fully qualified store to DB variable "	#@nocov
			"is not supported in this place.")			#@nocov

	def __storeINDIRECT(self, operator, memObj, allowedWidths): #@nocy
#@cy	cdef __storeINDIRECT(self, AwlOperator operator, AwlMemoryObject memObj, uint32_t allowedWidths):
		self.store(operator.resolve(True), memObj, allowedWidths)

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
		if not memory or maxLen <= 0:
			return [ prefix + "--" ]
		memArray = memory.getDataBytes()
		ret, line, first, count, i = [], [], True, 0, byteOffset
		def append(line):
			ret.append((prefix if first else (' ' * len(prefix))) +\
				   ' '.join(line))
		try:
			end = maxLen + byteOffset
			while i < end:
				line.append("%02X" % memArray[i])
				count += 1
				if count >= 16:
					append(line)
					line, count, first = [], 0, False
				i += 1
		except IndexError as e: #@nocov
			pass # memArray out of bounds access.
		if count:
			append(line)
		return ret

	def __dumpLStackFrame(self, prefix, frame): #@nocy
#@cy	cdef __dumpLStackFrame(self, prefix, LStackFrame *frame):
		if frame:
			memory = self.activeLStack.memory
			byteOffset = frame.byteOffset
			allocBits = frame.allocBits
		else: #@nocov
			memory, byteOffset, allocBits = None, 0, 0
		lines = self.__dumpMem(prefix,
				       memory,
				       byteOffset,
				       min(64, intDivRoundUp(allocBits, 8))) #+suffix-u
		lines.extend( [ (" " * len(prefix)) + "--" ] * (4 - len(lines)) )
		return lines

	def dump(self, withTime=True): #@nocov
#@cy		cdef LStackFrame *frame

		callStackTop = self.callStackTop
		if not callStackTop:
			return ""
		mnemonics = self.getMnemonics()
		isEnglish = (mnemonics == S7CPUConfig.MNEMONICS_EN)
		specs = self.specs
		self.updateTimestamp()
		ret = []
		ret.append("[S7-CPU]  t: %.01fs  %s / py%d / %s / v%s" %\
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
		ret.extend(self.__dumpMem("      M:  ",
					  self.flags, 0,
					  min(64, specs.nrFlags))) #+suffix-u
		prefix = "      I:  " if isEnglish else "      E:  "
		ret.extend(self.__dumpMem(prefix,
					  self.inputs, 0,
					  min(64, specs.nrInputs))) #+suffix-u
		prefix = "      Q:  " if isEnglish else "      A:  "
		ret.extend(self.__dumpMem(prefix,
					  self.outputs, 0,
					  min(64, specs.nrOutputs))) #+suffix-u
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
			ret.extend(self.__dumpLStackFrame("      L:  ", frame))
			frame = frame.prevFrame if frame else None #+NoneToNULL
			ret.extend(self.__dumpLStackFrame("     VL:  ", frame))
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
		if Logging.loglevel >= Logging.LOG_VERBOSE:
			ret.append("   time:  update-interval: %.01f/0x%X" % (
				   self.__timestampUpdInter,
				   self.__timestampUpdInterMask))
		avgCycleTime = self.avgCycleTime
		minCycleTime = self.minCycleTime
		maxCycleTime = self.maxCycleTime
		padCycleTime = self.padCycleTime
		if maxCycleTime == 0.0:
			avgCycleTimeStr = minCycleTimeStr = maxCycleTimeStr = padCycleTimeStr = "-/-"
		else:
			if avgCycleTime == 0.0:
				avgCycleTimeStr = "-/-"
			else:
				avgCycleTimeStr = "%.03f" % (avgCycleTime * 1000.0)
			minCycleTimeStr = "%.03f" % (minCycleTime * 1000.0)
			maxCycleTimeStr = "%.03f" % (maxCycleTime * 1000.0)
			padCycleTimeStr = "%.03f" % (padCycleTime * 1000.0)
		ret.append("    OB1:  avg: %s ms  min: %s ms  max: %s ms  pad: %s ms" % (
			   avgCycleTimeStr, minCycleTimeStr, maxCycleTimeStr, padCycleTimeStr))
		return '\n'.join(ret)

	@property
	def insnPerSecondHR(self): #@nocov
		"""Get a human readable instructions per seconds string.
		"""
		insnPerSecond = self.insnPerSecond
		if insnPerSecond > 0.0:
			return floatToHumanReadable(insnPerSecond)
		return "-/-"

	@property
	def usPerInsnHR(self): #@nocov
		"""Get a human readable microseconds per instructions string.
		"""
		insnPerSecond = self.insnPerSecond
		if insnPerSecond > 0.0:
			usPerInsnStr = "%.03f" % ((1.0 / insnPerSecond) * 1000000)
		else:
			usPerInsnStr = "-/-"
		return usPerInsnStr

	def __repr__(self): #@nocov
		return self.dump()
