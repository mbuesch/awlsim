# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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
from awlsim.common.cpuspecs import *

#from awlsim.core.cpu cimport * #@cy
from awlsim.core.cpu import * #@nocy

from awlsim.fupcompiler.fupcompiler_blockdecl import *
from awlsim.fupcompiler.fupcompiler_interf import *
from awlsim.fupcompiler.fupcompiler_grid import *
from awlsim.fupcompiler.fupcompiler_elem import *

#from awlsim.core.instructions.all_insns cimport * #@cy
from awlsim.core.instructions.all_insns import * #@nocy


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
	AWL_ENCODING = "latin_1"

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

	def getAwlSource(self):
		return self.awlSource

	def __parse(self):
		try:
			return FupCompilerFactory(compiler=self).parse(
				self.fupSource.sourceBytes)
		except FupCompilerFactory.Error as e:
			raise AwlSimError("Failed to parse FUP source: "
				"%s" % str(e))

	def __genAwlCode(self, insns):
		"""Generate AWL code from a list of instructions.
		Returns bytes encoded as self.AWL_ENCODING.
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

		return ('\r\n'.join(awl) + '\r\n').encode(self.AWL_ENCODING)

	def __compileBlockDecl(self):
		"""Compile block declaration.
		"""
		self.blockHeaderAwl, self.blockFooterAwl, self.instanceDBsAwl =\
			self.decl.compile(self.interf)

	def __compileInterface(self):
		"""Compile block interface.
		"""
		self.blockInterfAwl = self.interf.compile()

	def __compileGrids(self):
		"""Compile all self.grids
		"""
		# Compile the grids
		insns = []
		for grid in self.grids:
			insns.extend(grid.compile())
		insns.append(AwlInsn_BE(cpu=None))

		# Optimize the generated instructions
		pass#TODO

		# Store the AWL code in the AWL source object.
		self.awlSource.sourceBytes = self.__genAwlCode(insns)

	def __trycompile(self, fupSource, mnemonics):
		self.reset()
		self.fupSource = fupSource
		self.mnemonics = mnemonics
		self.opTrans = AwlOpTranslator(mnemonics=mnemonics)
		self.awlSource = AwlSource(name=fupSource.name,
					   filepath=fupSource.filepath)
		if self.__parse():
			self.__compileBlockDecl()
			self.__compileInterface()
			self.__compileGrids()
		return self.getAwlSource()

	def compile(self, fupSource, mnemonics):
		"""Compile a FupSource.
		mnemonics is either MNEMONICS_EN, MNEMONICS_DE or MNEMONICS_AUTO.
		Returns an AwlSource.
		"""
		if mnemonics == S7CPUSpecs.MNEMONICS_AUTO:
			try:
				return self.__trycompile(fupSource, S7CPUSpecs.MNEMONICS_EN)
			except AwlSimError as e:
				pass
			return self.__trycompile(fupSource, S7CPUSpecs.MNEMONICS_DE)
		return self.__trycompile(fupSource, mnemonics)
