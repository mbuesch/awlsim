# -*- coding: utf-8 -*-
#
# AWL parser
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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
from awlsim.core.compat import *

import sys
import re

from awlsim.core.util import *


class RawAwlInsn(object):
	def __init__(self, block):
		self.block = block
		self.lineNr = 0
		self.label = None
		self.name = None
		self.ops = []

	__labelRe = re.compile(r'^[_a-zA-Z][_0-9a-zA-Z]{0,3}$')

	@classmethod
	def isValidLabel(cls, labelString):
		# Checks if string is a valid label or
		# label reference (without colons).
		return bool(cls.__labelRe.match(labelString))

	def __repr__(self):
		ret = []
		if self.hasLabel():
			ret.append(self.getLabel() + ':  ')
		ret.append(self.getName())
		ret.extend(self.getOperators())
		return " ".join(ret)

	def setLineNr(self, newLineNr):
		self.lineNr = newLineNr

	def getLineNr(self):
		return self.lineNr

	def setLabel(self, newLabel):
		self.label = newLabel

	def getLabel(self):
		return self.label

	def hasLabel(self):
		return bool(self.getLabel())

	def setName(self, newName):
		self.name = newName

	def getName(self):
		return self.name

	def setOperators(self, newOperators):
		self.ops = newOperators

	def getOperators(self):
		return self.ops

	def hasOperators(self):
		return bool(self.getOperators())

class RawAwlBlock(object):
	def __init__(self, tree, index):
		self.tree = tree
		self.index = index

		self.descriptors = {
			"TITLE"		: None,
			"AUTHOR"	: None,
			"FAMILY"	: None,
			"NAME"		: None,
			"VERSION"	: None,
		}

	def addDescriptor(self, tokens):
		assert(len(tokens) >= 1 and tokens[0].upper())
		name = tokens[0].upper()
		if name == "TITLE":
			expectedSep = "="
		else:
			expectedSep = ":"
		try:
			if tokens[1] != expectedSep:
				raise IndexError
		except IndexError:
			raise AwlParserError("Invalid header format: "
				"Missing '%s' character." % expectedSep)
		if self.descriptors[name] is not None:
			raise AwlParserError("Header '%s' specified multiple times." %\
				name)
		self.descriptors[name] = tokens[2:]

	def hasLabel(self, string):
		return False

class RawAwlCodeBlock(RawAwlBlock):
	def __init__(self, tree, index):
		RawAwlBlock.__init__(self, tree, index)
		self.insns = []
		self.vars_in = []
		self.vars_out = []
		self.vars_inout = []
		self.vars_static = []
		self.vars_temp = []
		self.retTypeTokens = None

	def hasLabel(self, string):
		if RawAwlInsn.isValidLabel(string):
			for insn in self.insns:
				if insn.getLabel() == string:
					return True
		return False

class RawAwlDataField(object):
	def __init__(self, name, valueTokens, typeTokens):
		self.name = name
		self.valueTokens = valueTokens
		self.typeTokens = typeTokens

class RawAwlDB(RawAwlBlock):
	class FBRef(object):
		def __init__(self, fbName, fbNumber, isSFB):
			self.fbName = fbName
			self.fbNumber = fbNumber
			self.isSFB = isSFB

	def __init__(self, tree, index):
		RawAwlBlock.__init__(self, tree, index)
		self.fields = []
		self.fb = None

	def isInstanceDB(self):
		return bool(self.fb)

	def getByName(self, name):
		for field in self.fields:
			if field.name == name:
				return field
		return None

class RawAwlOB(RawAwlCodeBlock):
	def __init__(self, tree, index):
		RawAwlCodeBlock.__init__(self, tree, index)

class RawAwlFB(RawAwlCodeBlock):
	def __init__(self, tree, index):
		RawAwlCodeBlock.__init__(self, tree, index)

class RawAwlFC(RawAwlCodeBlock):
	def __init__(self, tree, index, retTypeTokens):
		RawAwlCodeBlock.__init__(self, tree, index)
		self.retTypeTokens = retTypeTokens

class AwlParseTree(object):
	def __init__(self):
		self.dbs = {}
		self.fbs = {}
		self.fcs = {}
		self.obs = {}

		self.curBlock = None

class AwlParser(object):
	EnumGen.start
	STATE_GLOBAL			= EnumGen.item
	STATE_IN_DB_HDR			= EnumGen.item
	STATE_IN_DB_HDR_STRUCT		= EnumGen.item
	STATE_IN_DB			= EnumGen.item
	STATE_IN_FB_HDR			= EnumGen.item
	STATE_IN_FB_HDR_VAR		= EnumGen.item
	STATE_IN_FB_HDR_VARIN		= EnumGen.item
	STATE_IN_FB_HDR_VAROUT		= EnumGen.item
	STATE_IN_FB_HDR_VARINOUT	= EnumGen.item
	STATE_IN_FB_HDR_VARTEMP		= EnumGen.item
	STATE_IN_FB_HDR_ATTR		= EnumGen.item
	STATE_IN_FB			= EnumGen.item
	STATE_IN_FC_HDR			= EnumGen.item
	STATE_IN_FC_HDR_VARIN		= EnumGen.item
	STATE_IN_FC_HDR_VAROUT		= EnumGen.item
	STATE_IN_FC_HDR_VARINOUT	= EnumGen.item
	STATE_IN_FC_HDR_VARTEMP		= EnumGen.item
	STATE_IN_FC_HDR_ATTR		= EnumGen.item
	STATE_IN_FC			= EnumGen.item
	STATE_IN_OB_HDR			= EnumGen.item
	STATE_IN_OB_HDR_VARTEMP		= EnumGen.item
	STATE_IN_OB_HDR_ATTR		= EnumGen.item
	STATE_IN_OB			= EnumGen.item
	EnumGen.end

	class TokenizerState(object):
		def __init__(self, parser):
			self.parser = parser
			self.tokens = []
			self.tokensLineNr = -1
			self.curToken = ""
			self.inComment = False
			self.inDoubleQuote = False
			self.inSingleQuote = False
			self.inParens = False
			self.inAssignment = False

		def addCharacter(self, c):
			if not self.curToken:
				self.tokensLineNr = self.parser.lineNr
			self.curToken += c

		def addToken(self, t):
			self.tokens.append(t)

		def finishCurToken(self):
			self.curToken = self.curToken.strip()
			if self.curToken:
				self.tokens.append(self.curToken)
			self.curToken = ""

		def finishStatement(self):
			self.tokens = []
			self.tokensLineNr = -1

	def __init__(self):
		self.reset()

	def reset(self):
		self.state = self.STATE_GLOBAL
		self.tree = AwlParseTree()

	def __setState(self, newState):
		self.state = newState

	def __inAnyHeader(self):
		if self.flatLayout:
			return False
		return self.state not in (self.STATE_GLOBAL,
					  self.STATE_IN_DB,
					  self.STATE_IN_FB,
					  self.STATE_IN_FC,
					  self.STATE_IN_OB)

	def __inAnyHeaderOrGlobal(self):
		if self.flatLayout:
			return False
		return self.__inAnyHeader() or\
		       self.state == self.STATE_GLOBAL

	def __tokenize(self, data):
		self.reset()
		self.lineNr = 1

		t = self.TokenizerState(self)
		for i, c in enumerate(data):
			if c == '\n':
				self.lineNr += 1
			if t.inComment:
				# Consume all comment chars up to \n
				if c == '\n':
					t.inComment = False
				continue
			if t.inAssignment:
				if c == '\n':
					t.inAssignment = False
					self.__parseTokens(t)
				else:
					t.addCharacter(c)
				continue
			if c == '"':
				# Double quote begin or end
				t.inDoubleQuote = not t.inDoubleQuote
			if c == "'":
				# Single quote begin or end
				t.inSingleQuote = not t.inSingleQuote
			if t.inSingleQuote or t.inDoubleQuote:
				t.addCharacter(c)
				continue
			if c == '/' and i + 1 < len(data) and\
			   data[i + 1] == '/':
				# A //comment ends the statement, but only if
				# not in parenthesis.
				if not t.inParens:
					self.__parseTokens(t)
				t.inComment = True
				continue
			if c == '=' and len(t.tokens) == 1 and not t.curToken:
				# NAME = VALUE assignment
				t.inAssignment = True
				t.addCharacter(c)
				t.finishCurToken()
				continue
			if t.tokens:
				if (c == '(' and t.tokens[0].endswith(':') and len(t.tokens) >= 2) or\
				   (c == '(' and not t.tokens[0].endswith(':')):
					# Parenthesis begin
					t.inParens = True
					t.addCharacter(c)
					t.finishCurToken()
					continue
				if t.inParens and c == ')':
					# Parenthesis end
					t.inParens = False
					t.finishCurToken()
					t.addToken(c)
					continue
				if (self.__inAnyHeaderOrGlobal() and\
				    c in ('=', ':', '..', '{', '}')) or\
				   c in (',', '[', ']') or\
				   (c == '=' and len(t.tokens) == 1 and not t.curToken):
					# Handle non-space token separators.
					t.finishCurToken()
					t.addToken(c)
					continue
			if not t.inParens:
				if c in ('\n', ';'):
					self.__parseTokens(t)
					continue
			if c.isspace():
				t.finishCurToken()
			else:
				t.addCharacter(c)
		if t.inSingleQuote or t.inDoubleQuote:
			raise AwlParserError("Unterminated quote")
		if t.inParens:
			raise AwlParserError("Unterminated parenthesis pair")
		if t.tokens:
			self.__parseTokens(t)

	def __parseTokens(self, tokenizerState):
		tokenizerState.finishCurToken()
		tokens = tokenizerState.tokens
		if not tokens:
			return

		if self.state == self.STATE_GLOBAL or\
		   self.flatLayout:
			self.__parseTokens_global(tokenizerState)
		elif self.state == self.STATE_IN_DB_HDR:
			self.__parseTokens_db_hdr(tokenizerState)
		elif self.state == self.STATE_IN_DB_HDR_STRUCT:
			self.__parseTokens_db_hdr_struct(tokenizerState)
		elif self.state == self.STATE_IN_DB:
			self.__parseTokens_db(tokenizerState)
		elif self.state == self.STATE_IN_FB_HDR:
			self.__parseTokens_fb_hdr(tokenizerState)
		elif self.state == self.STATE_IN_FB_HDR_VAR:
			self.__parseTokens_fb_hdr_var(tokenizerState)
		elif self.state == self.STATE_IN_FB_HDR_VARIN:
			self.__parseTokens_fb_hdr_varin(tokenizerState)
		elif self.state == self.STATE_IN_FB_HDR_VAROUT:
			self.__parseTokens_fb_hdr_varout(tokenizerState)
		elif self.state == self.STATE_IN_FB_HDR_VARINOUT:
			self.__parseTokens_fb_hdr_varinout(tokenizerState)
		elif self.state == self.STATE_IN_FB_HDR_VARTEMP:
			self.__parseTokens_fb_hdr_vartemp(tokenizerState)
		elif self.state == self.STATE_IN_FB_HDR_ATTR:
			self.__parseTokens_fb_hdr_attr(tokenizerState)
		elif self.state == self.STATE_IN_FB:
			self.__parseTokens_fb(tokenizerState)
		elif self.state == self.STATE_IN_FC_HDR:
			self.__parseTokens_fc_hdr(tokenizerState)
		elif self.state == self.STATE_IN_FC_HDR_VARIN:
			self.__parseTokens_fc_hdr_varin(tokenizerState)
		elif self.state == self.STATE_IN_FC_HDR_VAROUT:
			self.__parseTokens_fc_hdr_varout(tokenizerState)
		elif self.state == self.STATE_IN_FC_HDR_VARINOUT:
			self.__parseTokens_fc_hdr_varinout(tokenizerState)
		elif self.state == self.STATE_IN_FC_HDR_VARTEMP:
			self.__parseTokens_fc_hdr_vartemp(tokenizerState)
		elif self.state == self.STATE_IN_FC_HDR_ATTR:
			self.__parseTokens_fc_hdr_attr(tokenizerState)
		elif self.state == self.STATE_IN_FC:
			self.__parseTokens_fc(tokenizerState)
		elif self.state == self.STATE_IN_OB_HDR:
			self.__parseTokens_ob_hdr(tokenizerState)
		elif self.state == self.STATE_IN_OB_HDR_VARTEMP:
			self.__parseTokens_ob_hdr_vartemp(tokenizerState)
		elif self.state == self.STATE_IN_OB_HDR_ATTR:
			self.__parseTokens_ob_hdr_attr(tokenizerState)
		elif self.state == self.STATE_IN_OB:
			self.__parseTokens_ob(tokenizerState)
		else:
			assert(0)

		tokenizerState.finishStatement()

	def __parseTokens_global(self, t):
		if self.flatLayout:
			if not self.tree.obs:
				self.tree.obs[1] = RawAwlOB(self.tree, 1)
			if not self.tree.curBlock:
				self.tree.curBlock = self.tree.obs[1]
			insn = self.__parseInstruction(t)
			self.tree.obs[1].insns.append(insn)
			return

		try:
			if t.tokens[0].upper() == "DATA_BLOCK":
				self.__setState(self.STATE_IN_DB_HDR)
				if t.tokens[1].startswith('"') and\
				   t.tokens[1].endswith('"'):
					# DB name is symbolic
					dbNumber = t.tokens[1][1:-1]
				else:
					# DB name is absolute
					if t.tokens[1].upper() != "DB":
						raise AwlParserError("Invalid DB name")
					try:
						dbNumber = int(t.tokens[2], 10)
					except ValueError:
						raise AwlParserError("Invalid DB number")
				self.tree.curBlock = RawAwlDB(self.tree, dbNumber)
				self.tree.dbs[dbNumber] = self.tree.curBlock
				return
			if t.tokens[0].upper() == "FUNCTION_BLOCK":
				self.__setState(self.STATE_IN_FB_HDR)
				if t.tokens[1].startswith('"') and\
				   t.tokens[1].endswith('"'):
					# FB name is symbolic
					fbNumber = t.tokens[1][1:-1]
				else:
					# FB name is absolute
					if t.tokens[1].upper() != "FB":
						raise AwlParserError("Invalid FB name")
					try:
						fbNumber = int(t.tokens[2], 10)
					except ValueError:
						raise AwlParserError("Invalid FB number")
				self.tree.curBlock = RawAwlFB(self.tree, fbNumber)
				self.tree.fbs[fbNumber] = self.tree.curBlock
				return
			if t.tokens[0].upper() == "FUNCTION":
				self.__setState(self.STATE_IN_FC_HDR)
				if t.tokens[1].startswith('"') and\
				   t.tokens[1].endswith('"'):
					# FC name is symbolic
					fcNumber = t.tokens[1][1:-1]
					tIdx = 2
				else:
					# FC name is absolute
					if t.tokens[1].upper() != "FC":
						raise AwlParserError("Invalid FC name")
					try:
						fcNumber = int(t.tokens[2], 10)
					except ValueError:
						raise AwlParserError("Invalid FC number")
					tIdx = 3
				if t.tokens[tIdx] != ':':
					raise AwlParserError("Missing colon after FC number")
				retTypeTokens = t.tokens[tIdx + 1 : ]
				if not retTypeTokens:
					raise AwlParserError("Missing FC return type")
				self.tree.curBlock = RawAwlFC(self.tree, fcNumber,
							      retTypeTokens)
				self.tree.fcs[fcNumber] = self.tree.curBlock
				return
			if t.tokens[0].upper() == "ORGANIZATION_BLOCK":
				self.__setState(self.STATE_IN_OB_HDR)
				if t.tokens[1].startswith('"') and\
				   t.tokens[1].endswith('"'):
					# OB name is symbolic
					obNumber = t.tokens[1][1:-1]
				else:
					# OB name is absolute
					if t.tokens[1].upper() != "OB":
						raise AwlParserError("Invalid OB name")
					try:
						obNumber = int(t.tokens[2], 10)
					except ValueError:
						raise AwlParserError("Invalid OB number")
				self.tree.curBlock = RawAwlOB(self.tree, obNumber)
				self.tree.obs[obNumber] = self.tree.curBlock
				return
		except IndexError as e:
			raise AwlParserError("Missing token")
		except ValueError as e:
			raise AwlParserError("Invalid value")
		raise AwlParserError("Unknown statement")

	def __parseInstruction(self, t):
		insn = RawAwlInsn(self.tree.curBlock)
		insn.setLineNr(t.tokensLineNr)
		if t.tokens[0].endswith(":"):
			# First token is a label
			if len(t.tokens) <= 1:
				raise AwlParserError("Invalid standalone label")
			label = t.tokens[0][0:-1]
			if not label or not RawAwlInsn.isValidLabel(label):
				raise AwlParserError("Invalid label")
			insn.setLabel(label)
			t.tokens = t.tokens[1:]
		if not t.tokens:
			raise AwlParserError("No instruction name")
		insn.setName(t.tokens[0])
		t.tokens = t.tokens[1:]
		if t.tokens:
			# Operators to insn are specified
			insn.setOperators(t.tokens)
		return insn

	def __parseTokens_db_hdr(self, t):
		name = t.tokens[0].upper()
		if name == "BEGIN":
			self.__setState(self.STATE_IN_DB)
		elif name in ("TITLE", "AUTHOR", "FAMILY", "NAME", "VERSION"):
			self.tree.curBlock.addDescriptor(t.tokens)
		elif name == "STRUCT":
			self.__setState(self.STATE_IN_DB_HDR_STRUCT)
		elif name in ("FB", "SFB"):
			try:
				if len(t.tokens) != 2:
					raise ValueError
				fbName = name
				fbNumber = int(t.tokens[1], 10)
			except ValueError:
				raise AwlParserError("Invalid FB/SFB binding")
			self.tree.curBlock.fb = RawAwlDB.FBRef(fbName = fbName,
							       fbNumber = fbNumber,
							       isSFB = (name == "SFB"))
		else:
			raise AwlParserError("In DB header: Unknown token: %s" % name)

	def __parse_var_generic(self, t, varList,
				endToken,
				mayHaveInitval=True):
		if t.tokens[0].upper() == endToken:
			return False
		colonIdx = listIndex(t.tokens, ":")
		assignIdx = listIndex(t.tokens, ":=")
		if mayHaveInitval and colonIdx == 1 and assignIdx > colonIdx + 1:
			name = t.tokens[0]
			type = t.tokens[colonIdx+1:assignIdx]
			val = t.tokens[assignIdx+1:]
			field = RawAwlDataField(name, val, type)
			varList.append(field)
		elif colonIdx == 1:
			name = t.tokens[0]
			type = t.tokens[colonIdx+1:]
			field = RawAwlDataField(name, None, type)
			varList.append(field)
		else:
			raise AwlParserError("In variable section: Unknown tokens")
		return True

	def __parseTokens_db_hdr_struct(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.fields,
				endToken = "END_STRUCT",
				mayHaveInitval = False):
			self.__setState(self.STATE_IN_DB_HDR)

	def __parseTokens_db(self, t):
		if t.tokens[0].upper() == "END_DATA_BLOCK":
			self.__setState(self.STATE_GLOBAL)
			return
		if len(t.tokens) >= 3 and t.tokens[1] == ":=":
			name, valueTokens = t.tokens[0], t.tokens[2:]
			db = self.tree.curBlock
			field = db.getByName(name)
			if field:
				field.valueTokens = valueTokens
			else:
				field = RawAwlDataField(name, valueTokens,
							None)
				db.fields.append(field)
		else:
			raise AwlParserError("In DB: Unknown tokens")

	def __parseTokens_fb_hdr(self, t):
		name = t.tokens[0].upper()
		if name == "BEGIN":
			self.__setState(self.STATE_IN_FB)
		elif name in ("TITLE", "AUTHOR", "FAMILY", "NAME", "VERSION"):
			self.tree.curBlock.addDescriptor(t.tokens)
		elif name == "VAR":
			self.__setState(self.STATE_IN_FB_HDR_VAR)
		elif name == "VAR_INPUT":
			self.__setState(self.STATE_IN_FB_HDR_VARIN)
		elif name == "VAR_OUTPUT":
			self.__setState(self.STATE_IN_FB_HDR_VAROUT)
		elif name == "VAR_IN_OUT":
			self.__setState(self.STATE_IN_FB_HDR_VARINOUT)
		elif name == "VAR_TEMP":
			self.__setState(self.STATE_IN_FB_HDR_VARTEMP)
		elif name == "{":
			#TODO: parse attributes
			if "}" not in t.tokens:
				self.__setState(self.STATE_IN_FB_HDR_ATTR)
		else:
			raise AwlParserError("In FB: Unknown token: %s" % name)

	def __parseTokens_fb_hdr_var(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_static,
				endToken = "END_VAR"):
			self.__setState(self.STATE_IN_FB_HDR)

	def __parseTokens_fb_hdr_varin(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_in,
				endToken = "END_VAR"):
			self.__setState(self.STATE_IN_FB_HDR)

	def __parseTokens_fb_hdr_varout(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_out,
				endToken = "END_VAR"):
			self.__setState(self.STATE_IN_FB_HDR)

	def __parseTokens_fb_hdr_varinout(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_inout,
				endToken = "END_VAR"):
			self.__setState(self.STATE_IN_FB_HDR)

	def __parseTokens_fb_hdr_vartemp(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_temp,
				endToken = "END_VAR",
				mayHaveInitval = False):
			self.__setState(self.STATE_IN_FB_HDR)

	def __parseTokens_fb_hdr_attr(self, t):
		#TODO: parse attributes
		if "}" in t.tokens:
			self.__setState(self.STATE_IN_FB_HDR)

	def __parseTokens_fb(self, t):
		name = t.tokens[0].upper()
		if name == "END_FUNCTION_BLOCK":
			self.__setState(self.STATE_GLOBAL)
			return
		if name in ("NETWORK", "TITLE"):
			return # ignore
		insn = self.__parseInstruction(t)
		self.tree.curBlock.insns.append(insn)

	def __parseTokens_fc_hdr(self, t):
		name = t.tokens[0].upper()
		if name == "BEGIN":
			self.__setState(self.STATE_IN_FC)
		elif name in ("TITLE", "AUTHOR", "FAMILY", "NAME", "VERSION"):
			self.tree.curBlock.addDescriptor(t.tokens)
		elif name == "VAR_INPUT":
			self.__setState(self.STATE_IN_FC_HDR_VARIN)
		elif name == "VAR_OUTPUT":
			self.__setState(self.STATE_IN_FC_HDR_VAROUT)
		elif name == "VAR_IN_OUT":
			self.__setState(self.STATE_IN_FC_HDR_VARINOUT)
		elif name == "VAR_TEMP":
			self.__setState(self.STATE_IN_FC_HDR_VARTEMP)
		elif name == "{":
			#TODO: parse attributes
			if "}" not in t.tokens:
				self.__setState(self.STATE_IN_FC_HDR_ATTR)
		else:
			raise AwlParserError("In FC header: Unknown token: %s" % name)

	def __parseTokens_fc_hdr_varin(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_in,
				endToken = "END_VAR",
				mayHaveInitval=False):
			self.__setState(self.STATE_IN_FC_HDR)

	def __parseTokens_fc_hdr_varout(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_out,
				endToken = "END_VAR",
				mayHaveInitval=False):
			self.__setState(self.STATE_IN_FC_HDR)

	def __parseTokens_fc_hdr_varinout(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_inout,
				endToken = "END_VAR",
				mayHaveInitval=False):
			self.__setState(self.STATE_IN_FC_HDR)

	def __parseTokens_fc_hdr_vartemp(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_temp,
				endToken = "END_VAR",
				mayHaveInitval=False):
			self.__setState(self.STATE_IN_FC_HDR)

	def __parseTokens_fc_hdr_attr(self, t):
		#TODO: parse attributes
		if "}" in t.tokens:
			self.__setState(self.STATE_IN_FC_HDR)

	def __parseTokens_fc(self, t):
		name = t.tokens[0].upper()
		if name == "END_FUNCTION":
			self.__setState(self.STATE_GLOBAL)
			return
		if name in ("NETWORK", "TITLE"):
			return # ignore
		insn = self.__parseInstruction(t)
		self.tree.curBlock.insns.append(insn)

	def __parseTokens_ob_hdr(self, t):
		name = t.tokens[0].upper()
		if name == "BEGIN":
			self.__setState(self.STATE_IN_OB)
		elif name == "VAR_TEMP":
			self.__setState(self.STATE_IN_OB_HDR_VARTEMP)
		elif name in ("TITLE", "AUTHOR", "FAMILY", "NAME", "VERSION"):
			self.tree.curBlock.addDescriptor(t.tokens)
		elif name == "{":
			#TODO: parse attributes
			if "}" not in t.tokens:
				self.__setState(self.STATE_IN_OB_HDR_ATTR)
		else:
			raise AwlParserError("In OB header: Unknown token: %s" % name)

	def __parseTokens_ob_hdr_vartemp(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.vars_temp,
				endToken = "END_VAR",
				mayHaveInitval=False):
			self.__setState(self.STATE_IN_OB_HDR)

	def __parseTokens_ob_hdr_attr(self, t):
		#TODO: parse attributes
		if "}" in t.tokens:
			self.__setState(self.STATE_IN_OB_HDR)

	def __parseTokens_ob(self, t):
		name = t.tokens[0].upper()
		if name == "END_ORGANIZATION_BLOCK":
			self.__setState(self.STATE_GLOBAL)
			return
		if name in ("NETWORK", "TITLE"):
			return # ignore
		insn = self.__parseInstruction(t)
		self.tree.curBlock.insns.append(insn)

	def parseFile(self, filename):
		self.parseData(awlFileRead(filename))

	def parseData(self, data):
		self.flatLayout = not re.match(r'.*^\s*ORGANIZATION_BLOCK\s+.*',
					       data, re.DOTALL | re.MULTILINE)
		try:
			self.__tokenize(data)
		except AwlParserError as e:
			e.setLineNr(self.lineNr)
			raise e

	def getParseTree(self):
		return self.tree
