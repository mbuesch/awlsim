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

from awlsim.fupcompiler.fupcompiler_grid import *
from awlsim.fupcompiler.fupcompiler_elem import *


class FupCompilerFactory(XmlFactory):
	FUP_VERSION = 0

	def parser_open(self):
		self.inFup = False
		XmlFactory.parser_open(self)

	def parser_beginTag(self, tag):
		if self.inFup:
			if tag.name == "grid":
				grid = FupCompiler_Grid(self.compiler)
				self.compiler.grids.append(grid)
				self.parser_switchTo(grid.factory(grid=grid))
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
		if tag.name == "FUP":
			self.inFup = False
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.opTrans = None
		self.awlSource = None
		self.awlBytesList = []
		self.grids = []

	def getAwlSource(self):
		return self.awlSource

	def __parse(self, fupSource):
		try:
			FupCompilerFactory(compiler=self).parse(fupSource.sourceBytes)
		except FupCompilerFactory.Error as e:
			raise AwlSimError("Failed to parse FUP source: "
				"%s" % str(e))

	def __compile(self):
		insns = []
		for grid in self.grids:
			insns.extend(grid.compile())
		#TODO
		print("FINAL", insns)

	def __trycompile(self, fupSource, mnemonics):
		self.reset()
		self.opTrans = AwlOpTranslator(mnemonics=mnemonics)
		self.awlSource = AwlSource(name=fupSource.name,
					   filepath=fupSource.filepath)
		self.__parse(fupSource)
		self.__compile()
		self.awlSource.sourceBytes = b''.join(self.awlBytesList)
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
