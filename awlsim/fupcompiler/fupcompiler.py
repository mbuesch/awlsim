# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.sources import *
from awlsim.common.xmlfactory import *
from awlsim.common.cpuconfig import *

from awlsim.core.cpu import * #+cimport
from awlsim.core.operators import * #+cimport
from awlsim.core.operatortypes import * #+cimport

from awlsim.core.instructions.all_insns import * #+cimport

from awlsim.awloptimizer.awloptimizer import *

from awlsim.fupcompiler.fupcompiler_blockdecl import *
from awlsim.fupcompiler.fupcompiler_interf import *
from awlsim.fupcompiler.fupcompiler_grid import *
from awlsim.fupcompiler.fupcompiler_elem import *


class FupFakeCpu(S7CPU):
	def getMnemonics(self):
		return self.fupCompiler.mnemonics

class FupCompilerFactory(XmlFactory):
	FUP_VERSION = 0

	def parser_open(self, tag=None):
		self.inFup = False
		self.inGrids = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if self.inFup:
			if self.inGrids:
				if tag.name == "grid":
					grid = FupCompiler_Grid(self.compiler)
					self.compiler.grids.append(grid)
					self.parser_switchTo(grid.factory(grid=grid))
					return
			else:
				if tag.name == "blockdecl":
					if self.compiler.decl:
						raise self.Error("Multiple <blockdecl>s defined.")
					decl = FupCompiler_BlockDecl(self.compiler)
					self.compiler.decl = decl
					self.parser_switchTo(decl.factory(decl=decl))
					return
				if tag.name == "interface":
					if self.compiler.interf:
						raise self.Error("Multiple <interface>s defined.")
					interf = FupCompiler_Interf(self.compiler)
					self.compiler.interf = interf
					self.parser_switchTo(interf.factory(interf=interf))
					return
				if tag.name == "grids":
					self.inGrids = True
					return
		else:
			if tag.name == "FUP":
				version = tag.getAttrInt("version")
				if version != self.FUP_VERSION:
					raise self.Error("Unsupported FUP version. "
						"Got %d, but expected %d." % (
						version, self.FUP_VERSION))
				self.inFup = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inFup:
			if self.inGrids:
				if tag.name == "grids":
					self.inGrids = False
					return
			else:
				if tag.name == "FUP":
					self.inFup = False
					self.parser_finish()
					return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler(object):

	# Convert U to UN and vice versa.
	invertedInsnClass = {
		AwlInsn_UN	: AwlInsn_U,
		AwlInsn_UNB	: AwlInsn_UB,
		AwlInsn_ON	: AwlInsn_O,
		AwlInsn_ONB	: AwlInsn_OB,
		AwlInsn_XN	: AwlInsn_X,
		AwlInsn_XNB	: AwlInsn_XB,
	}
	invertedInsnClass.update(pivotDict(invertedInsnClass))

	# Convert U to UB and vice versa.
	branchInsnClass = {
		AwlInsn_UB	: AwlInsn_U,
		AwlInsn_UNB	: AwlInsn_UN,
		AwlInsn_OB	: AwlInsn_O,
		AwlInsn_ONB	: AwlInsn_ON,
		AwlInsn_XB	: AwlInsn_X,
		AwlInsn_XNB	: AwlInsn_XN,
	}
	branchInsnClass.update(pivotDict(branchInsnClass))

	def __init__(self):
		self.reset()

	def reset(self):
		self.mnemonics = None
		self.opTrans = None
		self.decl = None	# FupCompiler_BlockDecl
		self.interf = None	# FupCompiler_Interf
		self.grids = []		# FupCompiler_Grid

		self.blockHeaderAwl = []	# Block declaration header AWL code strings
		self.blockFooterAwl = []	# Block declaration footer AWL code strings
		self.blockInterfAwl = []	# Block interface AWL code strings
		self.instanceDBsAwl = []	# Instance DBs AWL code strings
		self.fupSource = None		# FUP source
		self.awlSource = None		# Compiled AWL source
		self.__labelCounter = 0		# Current label name counter

	def getAwlSource(self):
		return self.awlSource

	def newLabel(self):
		"""Generate a new block-unique label.
		A label name string is returned.
		The name does not include the final ':' character.
		"""
		labelMax = 0xFFF
		labelCounter = self.__labelCounter
		if labelCounter > labelMax:
			raise FupCompilerError("Out of jump labels. "
				"Cannot create more than %d labels." % (
				labelMax))
		self.__labelCounter += 1
		return "L%03X" % labelCounter

	def newInsn(self, parentFupElem, insnClass, ops=[]):
		"""Create a new instruction instance.
		parentFupElem: The FUP element that creates this insn.
		insnClass: The class that shall be instantiated.
		ops: Optional list of operators.
		"""
		insn = insnClass(cpu=None, ops=ops)
		if parentFupElem:
			insn.commentStr = str(parentFupElem)
		return insn

	def getOperDataWidth(self, oper):
		"""Helper function to get the data type width (in bits)
		of an operator. This will first attempt to resolve the operator,
		if it is symbolic.
		"""
		from awlsim.core.datatypes import AwlDataType

		if oper.width > 0:
			return oper.width
		if oper.operType == AwlOperatorTypes.NAMED_LOCAL:
			# Get the type of an interface field
			# and return its bit width.
			fieldName = str(oper.offset.identChain)
			field = self.interf.getFieldByName(fieldName)
			if not field:
				raise FupCompilerError("Interface field "
					"'#%s' could not be found in the "
					"declared interface." % (
					fieldName))
			dataType = AwlDataType.makeByName(field.typeStr)
			if dataType:
				return dataType.width
		elif oper.operType == AwlOperatorTypes.SYMBOLIC:
			# Get the type of a classic symbolic operator
			# and return its bit width.
			fieldName = str(oper.offset.identChain)
			pass#TODO
			raise FupCompilerError("The symbolic operator \"%s\" is "
				"not supported, yet." % (
				fieldName))
		return 0

	def __parse(self):
		try:
			return FupCompilerFactory(compiler=self).parse(
				self.fupSource.sourceBytes)
		except FupCompilerFactory.Error as e:
			raise FupCompilerError("Failed to parse FUP source: "
				"%s" % str(e))

	def __genAwlCode(self, insns):
		"""Generate AWL code from a list of instructions.
		Returns bytes encoded as AwlSource.ENCODING.
		"""
		awl = []

		# Create header
		awl.extend(self.blockHeaderAwl)
		awl.extend(self.blockInterfAwl)

		# Create instructions body
		awl.append("BEGIN")
		fakeCpu = FupFakeCpu()
		fakeCpu.fupCompiler = self
		for insn in insns:
			insn.cpu = fakeCpu
			awl.append("\t" + str(insn))

		# Create footer
		awl.extend(self.blockFooterAwl)

		# Create the instance DBs
		awl.extend(self.instanceDBsAwl or [])

		return ('\r\n'.join(awl) + '\r\n').encode(AwlSource.ENCODING)

	def __compileBlockDecl(self, optimize):
		"""Compile block declaration.
		"""
		self.blockHeaderAwl, self.blockFooterAwl, self.instanceDBsAwl =\
			self.decl.compile(self.interf, optimize)

	def __compileInterface(self, optimize):
		"""Compile block interface.
		"""
		self.blockInterfAwl = self.interf.compile(optimize)

	def __compileGrids(self, optimize):
		"""Compile all self.grids
		"""
		# Compile the grids
		insns = []
		for grid in self.grids:
			insns.extend(grid.compile())
		insns.append(AwlInsn_BE(cpu=None))

		if optimize:
			# Optimize the generated instructions
			optimizer = AwlOptimizer()
			insns = optimizer.optimizeInsns(insns)

		return insns

	def __trycompile(self, fupSource, mnemonics, optimize):
		self.reset()
		self.fupSource = fupSource
		self.mnemonics = mnemonics
		self.opTrans = AwlOpTranslator(mnemonics=mnemonics)
		self.awlSource = AwlSource(name=fupSource.name,
					   filepath=fupSource.filepath)
		if self.__parse():
			self.__compileBlockDecl(optimize)
			insns = self.__compileGrids(optimize)
			self.__compileInterface(optimize)

			# Store the AWL code in the AWL source object.
			self.awlSource.sourceBytes = self.__genAwlCode(insns)
		return self.getAwlSource()

	def compile(self, fupSource, mnemonics, optimize=True):
		"""Compile a FupSource.
		mnemonics is either MNEMONICS_EN, MNEMONICS_DE or MNEMONICS_AUTO.
		Returns an AwlSource.
		"""
		if mnemonics == S7CPUConfig.MNEMONICS_AUTO:
			try:
				return self.__trycompile(fupSource, S7CPUConfig.MNEMONICS_EN,
							 optimize=optimize)
			except AwlSimError as e:
				pass
			return self.__trycompile(fupSource, S7CPUConfig.MNEMONICS_DE,
						 optimize=optimize)
		return self.__trycompile(fupSource, mnemonics, optimize=optimize)

	def generateCallTemplate(self):
		"""Generate template AWL code for a CALL operation
		to this block.
		Returns an AwlSource.
		"""
		if not self.fupSource:
			raise FupCompilerError("FUP/FBD source is not compiled.")

		awlLines = []
		awlLines.extend(self.decl.generateCallTemplate())

		paramLines = self.interf.generateCallTemplate()
		if paramLines:
			awlLines[-1] += " ("
			awlLines.extend(paramLines)
			awlLines.append("\t)")

		awlString = "\r\n".join(awlLines)
		awlSource = AwlSource(name=("CALL " + self.fupSource.name))
		awlSource.sourceBytes = awlString.encode(AwlSource.ENCODING)
		return awlSource

	def __repr__(self):
		return "FupCompiler()"

	def __str__(self):
		return "FUP-compiler"
