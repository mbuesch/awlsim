# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Block declaration
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

from awlsim.common.xmlfactory import *

from awlsim.fupcompiler.fupcompiler_base import *


class FupCompiler_BlockDeclFactory(XmlFactory):
	def parser_open(self, tag=None):
		if tag:
			blockType = tag.getAttr("type", "FC")
			blockIndex = tag.getAttrInt("index", 0)
			self.decl.set(blockType=blockType,
				      blockIndex=blockIndex)
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "blockdecl":
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_BlockDecl(FupCompiler_BaseObj):
	factory = FupCompiler_BlockDeclFactory

	def __init__(self, compiler):
		FupCompiler_BaseObj.__init__(self)
		self.compiler = compiler	# FupCompiler
		self.set()

	def set(self, blockType="FC", blockIndex=0):
		self.blockType = blockType.upper().strip()
		if self.blockType not in {"FC", "FB", "OB"}:
			raise AwlSimError("FupCompiler_BlockDecl: Invalid block "
				"type: %s" % self.blockType)
		self.blockIndex = blockIndex
		if self.blockIndex < 0 or self.blockIndex > 0xFFFF:
			raise AwlSimError("FupCompiler_BlockDecl: Invalid block "
				"index: %d" % self.blockIndex)
