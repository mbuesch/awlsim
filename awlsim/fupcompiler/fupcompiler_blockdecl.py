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

from awlsim.common.namevalidation import *
from awlsim.common.xmlfactory import *

from awlsim.fupcompiler.fupcompiler_base import *


class FupCompiler_BlockDeclFactory(XmlFactory):
	def parser_open(self, tag=None):
		self.inInstanceDBs = False
		self.inDB = False
		if tag:
			self.decl.setBlockType(tag.getAttr("type", "FC"))
			self.decl.setBlockIndex(tag.getAttrInt("index", 0))
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if self.inInstanceDBs:
			if tag.name == "db":
				self.decl.addInstanceDB(tag.getAttrInt("index"))
				self.inDB = True
				return
		else:
			if tag.name == "instance_dbs":
				self.inInstanceDBs = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inInstanceDBs:
			if self.inDB:
				if tag.name == "db":
					self.inDB = False
					return
			else:
				if tag.name == "instance_dbs":
					self.inInstanceDBs = False
					return
		else:
			if tag.name == "blockdecl":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_BlockDecl(FupCompiler_BaseObj):
	factory = FupCompiler_BlockDeclFactory

	def __init__(self, compiler):
		FupCompiler_BaseObj.__init__(self)
		self.compiler = compiler	# FupCompiler
		self.setBlockType("FC")
		self.setBlockIndex(1)
		self.instanceDBs = []

	def setBlockType(self, blockType):
		self.blockType = blockType.upper().strip()
		if self.blockType not in {"FC", "FB", "OB"}:
			raise AwlSimError("FupCompiler_BlockDecl: Invalid block "
				"type: %s" % self.blockType)

	def setBlockIndex(self, blockIndex):
		self.blockIndex = blockIndex
		if self.blockIndex < 0 or self.blockIndex > 0xFFFF:
			raise AwlSimError("FupCompiler_BlockDecl: Invalid block "
				"index: %d" % self.blockIndex)

	def addInstanceDB(self, dbIndex):
		self.instanceDBs.append(dbIndex)
		if dbIndex < 0 or dbIndex > 0xFFFF:
			raise AwlSimError("FupCompiler_BlockDecl: Invalid instance "
				"DB index: %d" % dbIndex)

	def compile(self, interf):
		"""Compile this FUP block declaration to AWL.
		interf => FupCompiler_Interf
		Returns a tuple: (list of AWL header lines,
				  list of AWL footer lines,
				  list of AWL lines for instance DBs).
		"""
		self.compileState = self.COMPILE_RUNNING
		blockHeader = []
		blockFooter = []
		instDBs = []

		if self.blockType == "FC":
			if not interf.retValField:
				raise AwlSimError("FupCompiler_BlockDecl: RET_VAL "
					"is not defined for FC %d." %\
					 self.blockIndex)
			retVal = interf.retValField.typeStr
			if not AwlName.mayBeValidType(retVal):
				raise AwlSimError("FupCompiler_BlockDecl: RET_VAL "
					"data type contains invalid characters.")
			blockHeader.append("FUNCTION FC %d : %s" %(
					   self.blockIndex, retVal))
			blockFooter.append("END_FUNCTION")
		elif self.blockType == "FB":
			blockHeader.append("FUNCTION_BLOCK FB %d" %\
					   self.blockIndex)
			blockFooter.append("END_FUNCTION_BLOCK")
		elif self.blockType == "OB":
			blockHeader.append("ORGANIZATION_BLOCK OBC %d" %\
					   self.blockIndex)
			blockFooter.append("END_ORGANIZATION_BLOCK")
		else:
			raise AwlSimError("FupCompiler_BlockDecl: Unknown block "
				"type: %s" % self.blockType)

		for dbIndex in self.instanceDBs:
			instDBs.append("")
			instDBs.append("")
			instDBs.append("DATA_BLOCK DB %d" % dbIndex)
			instDBs.append("\tFB %d" % self.blockIndex)
			instDBs.append("BEGIN")
			for field in interf.allFields:
				fieldName = field.name
				initValueStr = field.initValueStr.strip()
				comment = field.comment
				if not initValueStr:
					continue
				if not AwlName.isValidVarName(fieldName):
					raise AwlSimError("FupCompiler_BlockDecl: Variable name "
						"'%s' contains invalid characters." %\
						fieldName)
				if not AwlName.mayBeValidValue(initValueStr):
					raise AwlSimError("FupCompiler_BlockDecl: Variable value "
						"'%s' contains invalid characters." %\
						initValueStr)
				if not AwlName.isValidComment(comment):
					raise AwlSimError("FupCompiler_BlockDecl: Comment "
						"'%s' contains invalid characters." %\
						comment)
				instDBs.append("\t%s := %s;%s" %(
					fieldName, initValueStr,
					("  // " + comment) if comment else ""))
			instDBs.append("END_DATA_BLOCK")

		self.compileState = self.COMPILE_DONE
		return blockHeader, blockFooter, instDBs
