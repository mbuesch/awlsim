# -*- coding: utf-8 -*-
#
# AWL parser
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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
from awlsim.core.datatypes import *
from awlsim.core.project import *


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
		self.insns = []		# List of RawAwlInsn()s
		# The block interface
		self.vars_in = []	# List of RawAwlDataField()s for IN vars
		self.vars_out = []	# List of RawAwlDataField()s for OUT vars
		self.vars_inout = []	# List of RawAwlDataField()s for IN_OUT vars
		self.vars_static = []	# List of RawAwlDataField()s for STATIC vars
		self.vars_temp = []	# List of RawAwlDataField()s for TEMP vars
		self.retTypeTokens = None

	def hasLabel(self, string):
		if RawAwlInsn.isValidLabel(string):
			for insn in self.insns:
				if insn.getLabel() == string:
					return True
		return False

class RawAwlDataIdent(object):
	def __init__(self, name, indices=None):
		self.name = name	# Name string of the variable
		self.indices = indices	# Possible array indices (or None)

	def __eq__(self, other):
		if self.name != other.name:
			return False
		if self.indices and other.indices:
			if self.indices != other.indices:
				return False
		return True

	def __ne__(self, other):
		return not self.__eq__(other)

	def __repr__(self):
		if self.indices:
			return "%s[%s]" % (self.name,
					   ",".join(str(i) for i in self.indices))
		return self.name

class RawAwlDataInit(object):
	def __init__(self, idents, valueTokens):
		"""idents -> The identifications for the data field.
		valueTokens -> List of tokens for the value.
		"""
		self.idents = toList(idents)
		self.valueTokens = valueTokens

	def getIdentString(self):
		return ".".join(str(ident) for ident in self.idents)

	def __repr__(self):
		return self.getIdentString() + " := " + str(self.valueTokens)

class RawAwlDataField(object):
	def __init__(self, idents, typeTokens, dimensions=None, inits=None):
		"""idents -> The identifications for the data field.
		typeTokens -> List of tokens for the data type.
		dimensions -> List of array dimensions, where each dimension is a
		              tuple of (start, end). Or None, if this is not an array.
		inits -> List of RawAwlDataInit()s"""
		self.idents = toList(idents)
		self.typeTokens = typeTokens
		self.dimensions = dimensions
		self.inits = inits if inits else []	# List of RawAwlDataInit()s

	def getIdentString(self):
		return ".".join(str(ident) for ident in self.idents)

	def __repr__(self):
		return self.getIdentString()

class RawAwlDB(RawAwlBlock):
	class FBRef(object):
		def __init__(self, fbName, fbNumber, isSFB):
			self.fbName = fbName
			self.fbNumber = fbNumber
			self.isSFB = isSFB

	def __init__(self, tree, index):
		RawAwlBlock.__init__(self, tree, index)
		self.fb = None

		# Data fields and initializations.
		# fieldInits are the inits from the DB init section.
		# The inits from the DB declaration section are in fields[x].inits.
		self.fields = []
		self.fieldInits = []	# List of RawAwlDataInit()s

	def getField(self, idents):
		try:
			return [f for f in self.fields if f.idents == idents][0]
		except IndexError as e:
			return None

	def addFieldInit(self, fieldInit):
		self.fieldInits.append(fieldInit)

	def getFieldInit(self, field):
		"""Returns the RawAwlDataInit() for the specified RawAwlDataField()"""
		for otherField, init in self.allFieldInits():
			if field.idents == init.idents:
				return init
		return None

	def allFieldInits(self):
		"""Returns a list (generator) of all RawAwlDataInits()"""
		# First all explicit field initializations
		for init in self.fieldInits:
			yield self.getField(init.idents), init
		# Then all field initializations from the declaration,
		# that we did not initialize, yet.
		for field in self.fields:
			for init in field.inits:
				for otherInit in self.fieldInits:
					if init.idents == otherInit.idents:
						# We already had an init for this field.
						break
				else:
					# We did not have this init, yet.
					yield field, init

	def isInstanceDB(self):
		return bool(self.fb)

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

		self.fileId = ""

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

	TEXT_ENCODING = "latin_1"

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

	def __tokenize(self, data, fileId):
		self.reset()
		self.tree.fileId = fileId
		self.lineNr = 1

		t = self.TokenizerState(self)
		for i, c in enumerate(data):
			cNext = data[i + 1] if i + 1 < len(data) else None
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
				# This is not the first token of the statement.
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
					if c == ':' and cNext == '=':
						# We are at the 'colon' character of a ':=' assignment.
						t.finishCurToken()
						t.addCharacter(c)
					elif c == '=' and t.curToken == ':':
						# We are at the 'equal' character of a ':=' assignment.
						t.addCharacter(c)
						t.finishCurToken()
					else:
						# Any other non-space token separator.
						t.finishCurToken()
						t.addToken(c)
					continue
			else:
				# This is the first token of the statement.
				if c == '[':
					# This is the start of an array subscript.
					# Handle it as separator.
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

	def __parseArrayInitializer(self, name, initsList, tokens):
		"""Parse an ARRAY initializer. That is either of:
		1, 2, 3, 4
		4 (1, 2, 3, 4)
		or similar.
		name -> The name string of the variable.
		initsList -> The result list. Each element is a RawAwlDataInit().
		tokens -> The tokens to parse."""
		pass#TODO

	def __parse_var_generic(self, t, varList,
				endToken,
				mayHaveInitval=True):
		if t.tokens[0].upper() == endToken:
			return False
		colonIdx = listIndex(t.tokens, ":")
		assignIdx = listIndex(t.tokens, ":=")
		initsList = []
		if len(t.tokens) >= 10 and\
		   colonIdx == 1 and t.tokens[colonIdx+1].upper() == "ARRAY":
			# This is an array variable.
			ofIdx = listIndex(t.tokens, "OF",
					  translate=lambda i, v: v.upper())
			if assignIdx >= 0:
				# We have an array initializer.
				if not mayHaveInitval:
					raise AwlParserError("In variable section: "
						"Invalid ARRAY initializer")
				if assignIdx < ofIdx + 2:
					raise AwlParserError("In variable section: "
						"Invalid ARRAY initializer placement")
			if t.tokens[colonIdx+2] != "[":
				raise AwlParserError("In variable section: "
					"Invalid ARRAY definition")
			closeIdx = listIndex(t.tokens, "]")
			if closeIdx < colonIdx + 6 or\
			   ofIdx < colonIdx + 7 or\
			   closeIdx + 1 != ofIdx:
				raise AwlParserError("In variable section: "
					"Invalid ARRAY definition")
			dimTokens = t.tokens[colonIdx+3 : closeIdx]
			dimensions = []
			while dimTokens:
				if len(dimTokens) < 3:
					raise AwlParserError("In variable section: "
						"Invalid ARRAY dimensions")
				if dimTokens[1] != "..":
					raise AwlParserError("In variable section: "
						"Invalid ARRAY dimensions")
				try:
					dimensions.append( (int(dimTokens[0]),
							    int(dimTokens[2])) )
				except ValueError as e:
					raise AwlParserError("In variable section: "
						"Invalid ARRAY dimensions")
				if dimensions[-1][0] > dimensions[-1][1]:
					raise AwlParserError("In variable section: "
						"ARRAY dimension error. "
						"Start bigger than end.")
				if len(dimensions) > 6:
					raise AwlParserError("In variable section: "
						"Too many dimensions in ARRAY (max 6)")
				dimTokens = dimTokens[3:]
				if dimTokens and dimTokens[0] == ",":
					dimTokens = dimTokens[1:]
			name = t.tokens[0]
			if assignIdx >= 0:
				type = t.tokens[ofIdx+1:assignIdx]
			else:
				type = t.tokens[ofIdx+1:]
			nrElems = AwlDataType.arrayDimensionsToNrElements(dimensions)
			if assignIdx >= 0:
				# Parse the ARRAY initializer (:= ...)
				initTokens = t.tokens[assignIdx+1:]
				self.__parseArrayInitializer(name,
							     initsList,
							     initTokens)
		else:
			# This is a normal non-array variable.
			dimensions = None
			if mayHaveInitval and colonIdx == 1 and assignIdx > colonIdx + 1:
				name = t.tokens[0]
				type = t.tokens[colonIdx+1:assignIdx]
				initTokens = t.tokens[assignIdx+1:]
				initsList.append(RawAwlDataInit(RawAwlDataIdent(name),
								initTokens))
			elif colonIdx == 1:
				name = t.tokens[0]
				type = t.tokens[colonIdx+1:]
			else:
				raise AwlParserError("In variable section: Unknown tokens")
		field = RawAwlDataField(idents = RawAwlDataIdent(name),
					typeTokens = type,
					dimensions = dimensions,
					inits = initsList)
		varList.append(field)

		return True

	def __parseTokens_db_hdr_struct(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.fields,
				endToken = "END_STRUCT"):
			self.__setState(self.STATE_IN_DB_HDR)

	def __parseTokens_db(self, t):
		if t.tokens[0].upper() == "END_DATA_BLOCK":
			self.__setState(self.STATE_GLOBAL)
			return
		if len(t.tokens) >= 6 and t.tokens[1] == "[":
			# Array subscript assignment
			name = t.tokens[0]
			db = self.tree.curBlock
			closeIdx = listIndex(t.tokens, "]", 2)
			assignIdx = listIndex(t.tokens, ":=", closeIdx + 1)
			if closeIdx < 0:
				raise AwlParserError("Array assignment: "
					"Missing closing braces")
			if assignIdx < 0 or\
			   assignIdx != closeIdx + 1:
				raise AwlParserError("Array assignment: "
					"Invalid value assignment")
			indexTokens = t.tokens[2:closeIdx]
			valueTokens = t.tokens[assignIdx+1:]
			# Parse the array indices
			indices = []
			while indexTokens:
				try:
					indices.append(int(indexTokens[0]))
				except ValueError as e:
					raise AwlParserError("Array assignment: "
						"Invalid index value")
				indexTokens = indexTokens[1:]
				if indexTokens:
					if indexTokens[0] != ",":
						raise AwlParserError("Array assignment: "
							"Expected comma")
					indexTokens = indexTokens[1:]
			if not indices:
				raise AwlParserError("Array assignment: "
					"Invalid indices")
			if len(indices) > 6:
				raise AwlParserError("Array assignment: "
					"More than 6 indices specified")
			db.addFieldInit(RawAwlDataInit(RawAwlDataIdent(name, indices),
						       valueTokens))
		elif len(t.tokens) >= 3 and t.tokens[1] == ":=":
			# Variable assignment
			name, valueTokens = t.tokens[0], t.tokens[2:]
			db = self.tree.curBlock
			db.addFieldInit(RawAwlDataInit(RawAwlDataIdent(name),
						       valueTokens))
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

	def parseSource(self, awlSource):
		"""Parse an AWL source.
		awlSource is an AwlSource instance."""
		self.parseData(awlSource.sourceBytes, str(awlSource))

	def parseData(self, dataBytes, fileId=""):
		try:
			data = dataBytes.decode(self.TEXT_ENCODING)
		except UnicodeError as e:
			raise AwlParserError("Could not decode AWL/STL charset.")
		#FIXME: This check will trigger, if there is no OB, which may happen
		#       for projects with multiple awl files.
		self.flatLayout = not re.match(r'.*^\s*ORGANIZATION_BLOCK\s+.*',
					       data, re.DOTALL | re.MULTILINE)
		try:
			self.__tokenize(data, fileId)
		except AwlParserError as e:
			e.setLineNr(self.lineNr)
			e.setFileId(fileId)
			raise e

	def getParseTree(self):
		return self.tree
