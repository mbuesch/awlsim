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

	def compile(self, interf):
		"""Compile this FUP block declaration to AWL.
		interf => FupCompiler_Interf
		Returns a tuple: (list of AWL header lines, list of AWL footer lines).
		"""
		self.compileState = self.COMPILE_RUNNING
		awlHeader = []
		awlFooter = []

		if self.blockType == "FC":
			if not interf.retValField:
				raise AwlSimError("FupCompiler_BlockDecl: RET_VAL "
					"is not defined for FC %d." %\
					 self.blockIndex)
			retVal = interf.retValField.typeStr
			awlHeader.append("FUNCTION FC %d : %s" %(
					 self.blockIndex, retVal))
			awlFooter.append("END_FUNCTION")
		elif self.blockType == "FB":
			awlHeader.append("FUNCTION_BLOCK FB %d" %\
					 self.blockIndex)
			awlFooter.append("END_FUNCTION_BLOCK")
		elif self.blockType == "OB":
			awlHeader.append("ORGANIZATION_BLOCK OBC %d" %\
					 self.blockIndex)
			awlFooter.append("END_ORGANIZATION_BLOCK")
		else:
			raise AwlSimError("FupCompiler_BlockDecl: Unknown block "
				"type: %s" % self.blockType)

		self.compileState = self.COMPILE_DONE
		return awlHeader, awlFooter
