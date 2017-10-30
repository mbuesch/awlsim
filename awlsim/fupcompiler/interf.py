# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Interface
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

from awlsim.fupcompiler.base import *


class FupCompiler_InterfFactory(XmlFactory):
	def parser_open(self, tag=None):
		self.inSection = "interface"
		self.interf.reset()
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		interf = self.interf

		def mkField(tag):
			return FupCompiler_InterfField(
				name=tag.getAttr("name", ""),
				typeStr=tag.getAttr("type", ""),
				initValueStr=tag.getAttr("init", ""),
				comment=tag.getAttr("comment", ""),
				uuid=tag.getAttr("uuid", None))

		if self.inSection == "interface":
			if tag.name in {"inputs", "outputs", "inouts",
					"stats", "temps", "retval"}:
				self.inSection = tag.name
				return
		elif self.inSection == "inputs":
			if tag.name == "field":
				interf.inFields.append(mkField(tag))
				return
		elif self.inSection == "outputs":
			if tag.name == "field":
				interf.outFields.append(mkField(tag))
				return
		elif self.inSection == "inouts":
			if tag.name == "field":
				interf.inOutFields.append(mkField(tag))
				return
		elif self.inSection == "stats":
			if tag.name == "field":
				interf.statFields.append(mkField(tag))
				return
		elif self.inSection == "temps":
			if tag.name == "field":
				interf.tempFields.append(mkField(tag))
				return
		elif self.inSection == "retval":
			if tag.name == "field":
				interf.retValField = mkField(tag)
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inSection == "interface":
			if tag.name == self.inSection:
				self.parser_finish()
				return
		else:
			if tag.name == self.inSection:
				self.inSection = "interface"
				return
			if tag.name == "field":
				return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_InterfField(object):
	def __init__(self, name="", typeStr="", initValueStr="", comment="", uuid=None, enableNameCheck=True):
		self.name = name
		self.typeStr = typeStr
		self.initValueStr = initValueStr
		self.comment = comment
		self.uuid = uuid or "00000000-0000-0000-0000-000000000000"
		self.enableNameCheck = enableNameCheck

class FupCompiler_Interf(FupCompiler_BaseObj):
	factory			= FupCompiler_InterfFactory
	noPreprocessing		= True

	def __init__(self, compiler):
		FupCompiler_BaseObj.__init__(self)
		self.compiler = compiler	# FupCompiler
		self.reset()

	def reset(self):
		self.inFields = []
		self.outFields = []
		self.inOutFields = []
		self.statFields = []
		self.tempFields = []
		self.retValField = None

	@property
	def allFields(self):
		for field in itertools.chain(self.inFields,
					     self.outFields,
					     self.inOutFields,
					     self.statFields,
					     self.tempFields,
					     [ self.retValField ]):
			if field:
				yield field

	def getFieldByName(self, fieldName):
		"""Get an interface field by name.
		Returns an FupCompiler_InterfField instance
		or None, if there is no such field.
		"""
		for field in self.allFields:
			if field.name == fieldName:
				return field
		return None

	def allocTEMP(self, dataTypeName="BOOL", name=None, elem=None):
		"""Allocate an additional TEMP field.
		'dataTypeName' is the data type to create.
		'name' is the optional name of the new field.
		'elem' is the optional element that allocates the field.
		Returns the name string of the allocated field.
		"""
		comment = "Allocated by FUP compiler"
		if elem:
			comment += " for %s" % str(elem)
		field = FupCompiler_InterfField(
			name=name or ("_FUP_COMP_temp_%d" % len(self.tempFields)),
			typeStr=dataTypeName,
			initValueStr="",
			comment=comment,
			uuid=None,
			enableNameCheck=False)
		self.tempFields.append(field)
		return field.name

	def __compileFields(self, declStr, fields):
		if not fields:
			return []
		awlLines = [ "\t" + declStr, ]
		for field in fields:
			varName = field.name
			typeStr = field.typeStr
			comment = field.comment
			if not AwlName.isValidVarName(varName) and\
			   field.enableNameCheck:
				raise FupInterfError("Variable name "
					"'%s' contains invalid characters." % (
					varName),
					self)
			if not AwlName.mayBeValidType(typeStr):
				raise FupInterfError("Variable type "
					"'%s' contains invalid characters." % (
					typeStr),
					self)
			if not AwlName.isValidComment(comment):
				raise FupInterfError("Comment "
					"'%s' contains invalid characters." % (
					comment),
					self)
			awlLines.append("\t\t%s : %s;%s" %(
				varName, typeStr,
				("  // " + comment) if comment else ""))
		awlLines.append("\tEND_VAR")
		return awlLines

	def compile(self):
		"""Compile this FUP interface declaration to AWL.
		Returns a list of AWL lines.
		"""
		self.compileState = self.COMPILE_RUNNING
		awlLines = []

		awlLines.extend(self.__compileFields("VAR_INPUT", self.inFields))
		awlLines.extend(self.__compileFields("VAR_OUTPUT", self.outFields))
		awlLines.extend(self.__compileFields("VAR_IN_OUT", self.inOutFields))
		awlLines.extend(self.__compileFields("VAR", self.statFields))
		awlLines.extend(self.__compileFields("VAR_TEMP", self.tempFields))

		self.compileState = self.COMPILE_DONE
		return awlLines

	def __generateAssigns(self, fields):
		awlLines = []
		for field in fields:
			typeStr = field.typeStr.strip()
			comment = []
			if typeStr:
				comment.append(typeStr)
			fieldComment = field.comment.strip()
			if fieldComment:
				comment.append(fieldComment)
			fieldName = field.name.strip()
			if len(fieldName) >= 16:
				indent = " "
			elif len(fieldName) >= 8:
				indent = "\t"
			else:
				indent = "\t\t"
			awlLines.append("\t\t%s%s:= ... ,%s" % (
				fieldName,
				indent,
				("  // %s" % "; ".join(comment)) if comment else ""))
		return awlLines

	def generateCallTemplate(self):
		"""Generate template AWL code for a CALL operation
		to this block.
		Returns a list of AWL lines.
		"""
		awlLines = []

		if self.inFields:
			awlLines.append("\t\t// VAR_INPUT")
			awlLines.extend(self.__generateAssigns(self.inFields))
		if self.outFields:
			awlLines.append("\t\t// VAR_OUTPUT")
			awlLines.extend(self.__generateAssigns(self.outFields))
		if self.inOutFields:
			awlLines.append("\t\t// VAR_IN_OUT")
			awlLines.extend(self.__generateAssigns(self.inOutFields))

		return awlLines

	def __repr__(self):
		return "FupCompiler_Interf(compiler)"

	def __str__(self):
		return "FUP-block-interface"
