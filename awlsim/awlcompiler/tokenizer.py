# -*- coding: utf-8 -*-
#
# AWL parser
#
# Copyright 2012-2017 Michael Buesch <m@bues.ch>
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

import sys
import re

from awlsim.common.enumeration import *
from awlsim.common.project import *
from awlsim.common.refmanager import *
from awlsim.common.namevalidation import *
from awlsim.common.sources import AwlSource

from awlsim.core.util import *
from awlsim.core.datatypes import *
from awlsim.core.memory import * #@nocy
#from awlsim.core.memory cimport * #@cy
from awlsim.core.identifier import *


class RawAwlInsn(object):
	"""Raw representation of an AWL instruction."""

	__slots__ = (
		"block",
		"sourceId",
		"lineNr",
		"label",
		"name",
		"ops",
	)

	def __init__(self, block):
		self.block = block
		self.sourceId = None
		self.lineNr = 0
		self.label = None
		self.name = None
		self.ops = []

	def __repr__(self):
		ret = []
		if self.hasLabel():
			ret.append(self.getLabel() + ':  ')
		ret.append(self.getName())
		ret.extend(self.getOperators())
		return " ".join(ret)

	def setSourceId(self, sourceId):
		self.sourceId = sourceId

	def getSourceId(self):
		return self.sourceId

	def setLineNr(self, newLineNr):
		self.lineNr = newLineNr

	def getLineNr(self):
		return self.lineNr

	def setLabel(self, newLabel):
		self.label = newLabel

	def getLabel(self):
		return self.label

	def hasLabel(self):
		return bool(self.label)

	def setName(self, newName):
		self.name = newName

	def getName(self):
		return self.name

	def setOperators(self, newOperators):
		self.ops = newOperators

	def getOperators(self):
		return self.ops

	def hasOperators(self):
		return bool(self.ops)

class RawAwlBlock(object):
	"""Raw representation of an AWL block."""

	__slots__ = (
		"tree",
		"index",
		"descriptors",
		"sourceRef",
	)

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
		self.sourceRef = None

	def setSourceRef(self, sourceManagerOrRef, inheritRef = False):
		self.sourceRef = ObjRef.make(
			name = lambda ref: str(ref.obj),
			managerOrRef = sourceManagerOrRef,
			obj = self,
			inheritRef = inheritRef)

	def destroySourceRef(self):
		if self.sourceRef:
			self.sourceRef.destroy()
			self.sourceRef = None

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
	"""Raw representation of an AWL code block (OB, FC, FB)."""

	__slots__ = (
		"insns",
		"vars_in",
		"vars_out",
		"vars_inout",
		"vars_static",
		"vars_temp",
		"retTypeTokens",
	)

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
		if AwlName.isValidLabel(string):
			for insn in self.insns:
				if insn.getLabel() == string:
					return True
		return False

class RawAwlDataInit(object):
	"""Raw representation of a data initialization."""

	__slots__ = (
		"identChain",
		"valueTokens",
	)

	def __init__(self, identChain, valueTokens):
		"""identChain -> The identifications for the data field.
		valueTokens -> List of tokens for the value.
		"""
		#TODO use AwlDataIdentChain
		self.identChain = toList(identChain)
		self.valueTokens = valueTokens

	def getIdentString(self):
		return ".".join(str(ident) for ident in self.identChain)

	def __repr__(self):
		return self.getIdentString() + " := " + str(self.valueTokens)

class RawAwlDataField(object):
	"""Raw representation of a data field."""

	__slots__ = (
		"ident",
		"typeTokens",
		"dimensions",
		"defaultInits",
		"parent",
		"children",
	)

	def __init__(self, ident, typeTokens, dimensions=None, defaultInits=None,
		     parent=None, children=None):
		"""ident -> The AwlDataIdent for this data field.
		            Note that the full ident depends on 'parent', too.
		typeTokens -> List of tokens for the data type.
		dimensions -> List of array dimensions, where each dimension is a
		              tuple of (start, end). Or None, if this is not an array.
		defaultInits -> List of RawAwlDataInit()s for use as 'startvalues'"""
		self.ident = ident
		self.typeTokens = typeTokens
		self.dimensions = dimensions
		self.defaultInits = defaultInits or [] # List of RawAwlDataInit()s
		self.parent = parent
		self.children = children or []

	def getIdentChain(self):
		identChain = []
		field = self
		while field:
			identChain.insert(0, field.ident)
			field = field.parent
		return identChain

	def getIdentString(self, fullChain=True):
		if fullChain:
			return ".".join(str(ident) for ident in self.getIdentChain())
		return str(self.ident)

	def getChild(self, identChain):
		try:
			field = [f for f in self.children if f.ident == identChain[0]][0]
			if len(identChain) > 1:
				return field.getChild(identChain[1:])
			return field
		except IndexError as e:
			return None
	def __repr__(self):
		return self.getIdentString()

class RawAwlDB(RawAwlBlock):
	"""Raw representation of an AWL data block (DB)."""

	__slots__ = (
		"fb",
		"fields",
		"fieldInits",
	)

	class FBRef(object):
		__slots__ = (
			"fbNumber",
			"isSFB",
			"fbSymbol",
		)

		def __init__(self, fbNumber=None, isSFB=None, fbSymbol=None):
			self.fbNumber = fbNumber
			self.isSFB = isSFB
			self.fbSymbol = fbSymbol

	def __init__(self, tree, index):
		RawAwlBlock.__init__(self, tree, index)
		self.fb = None

		# Data fields (RawAwlDataField) and initializations (RawAwlDataInit)
		# fieldInits are the inits from the DB init section (_not_ declaration).
		# The startup inits from the DB declaration section are in fields[x].inits.
		self.fields = []	# List of RawAwlDataField()s
		self.fieldInits = []	# List of RawAwlDataInit()s

	def getField(self, identChain):
		try:
			field = [f for f in self.fields if f.ident == identChain[0]][0]
			if len(identChain) > 1:
				return field.getChild(identChain[1:])
			return field
		except IndexError as e:
			return None

	def addFieldInit(self, fieldInit):
		self.fieldInits.append(fieldInit)

	def allFieldInits(self):
		"""Returns a list (generator) of all 'actual-value' RawAwlDataInits()"""
		for init in self.fieldInits:
			yield self.getField(init.identChain), init

	def isInstanceDB(self):
		return bool(self.fb)

class RawAwlUDT(RawAwlBlock):
	"""Raw representation of an AWL UDT."""

	__slots__ = (
		"fields",
	)

	def __init__(self, tree, index):
		RawAwlBlock.__init__(self, tree, index)

		# The data fields of this UDT
		self.fields = []	# List of RawAwlDataField()s

class RawAwlOB(RawAwlCodeBlock):
	"""Raw representation of an AWL Organization Block (OB)."""

	__slots__ = ()

	def __init__(self, tree, index):
		RawAwlCodeBlock.__init__(self, tree, index)

class RawAwlFB(RawAwlCodeBlock):
	"""Raw representation of an AWL Function Block (FB)."""

	__slots__ = ()

	def __init__(self, tree, index):
		RawAwlCodeBlock.__init__(self, tree, index)

class RawAwlFC(RawAwlCodeBlock):
	"""Raw representation of an AWL Function (FC)."""

	__slots__ = ()

	def __init__(self, tree, index, retTypeTokens):
		RawAwlCodeBlock.__init__(self, tree, index)
		self.retTypeTokens = retTypeTokens

class AwlParseTree(object):
	def __init__(self):
		self.sourceId = None
		self.sourceName = None

		self.dbs = {}	# DBs (dict of 'OB-name : RawAwlDB()')
		self.fbs = {}	# FBs (dict of 'FB-name : RawAwlFB()')
		self.fcs = {}	# FCs (dict of 'FC-name : RawAwlFC()')
		self.obs = {}	# OBs (dict of 'OB-name : RawAwlOB()')
		self.udts = {}	# UDTs (dict of 'UDT-name : RawAwlUDT()')

		self.curBlock = None
		self.curDataField = None

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
	STATE_IN_UDT_HDR		= EnumGen.item
	STATE_IN_UDT_HDR_STRUCT		= EnumGen.item
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
			curToken = self.curToken.strip()
			if curToken:
				self.addToken(curToken)
			self.curToken = ""

		def finishStatement(self):
			self.tokens = []
			self.tokensLineNr = -1

		def haveLabelToken(self):
			return self.tokens and\
			       self.tokens[0].endswith(':')

	def __init__(self):
		self.reset()

	def reset(self):
		self.state = self.STATE_GLOBAL
		self.tree = AwlParseTree()

	def __setState(self, newState):
		self.state = newState

	__nonHeaderStates = {
		STATE_GLOBAL,
		STATE_IN_DB,
		STATE_IN_FB,
		STATE_IN_FC,
		STATE_IN_OB,
	}

	def __inAnyHeader(self):
		return not self.flatLayout and\
		       self.state not in self.__nonHeaderStates

	def __inAnyHeaderOrGlobal(self):
		return not self.flatLayout and\
		       (self.__inAnyHeader() or\
		        self.state == self.STATE_GLOBAL)

	__varSectionStates = {
		STATE_IN_DB_HDR_STRUCT,
		STATE_IN_DB,
		STATE_IN_FB_HDR_VAR,
		STATE_IN_FB_HDR_VARIN,
		STATE_IN_FB_HDR_VAROUT,
		STATE_IN_FB_HDR_VARINOUT,
		STATE_IN_FB_HDR_VARTEMP,
		STATE_IN_FC_HDR_VARIN,
		STATE_IN_FC_HDR_VAROUT,
		STATE_IN_FC_HDR_VARINOUT,
		STATE_IN_FC_HDR_VARTEMP,
		STATE_IN_OB_HDR_VARTEMP,
		STATE_IN_UDT_HDR_STRUCT,
	}

	def __inVariableSection(self):
		return not self.flatLayout and\
		       self.state in self.__varSectionStates

	def __tokenize(self, data, sourceId, sourceName):
		self.reset()
		self.tree.sourceId = sourceId
		self.tree.sourceName = sourceName
		self.lineNr = 1

		def cont():
			if c == '\n':
				self.lineNr += 1

		t = self.TokenizerState(self)
		for i, c in enumerate(data):
			cNext = data[i + 1] if i + 1 < len(data) else None
			if t.inComment:
				# Consume all comment chars up to \n
				if c == '\n':
					t.inComment = False
				cont(); continue
			if t.inAssignment:
				if c == '\n':
					t.inAssignment = False
					self.__parseTokens(t)
				else:
					t.addCharacter(c)
				cont(); continue
			if c == '"':
				# Double quote begin or end
				t.inDoubleQuote = not t.inDoubleQuote
			elif c == "'":
				# Single quote begin or end
				t.inSingleQuote = not t.inSingleQuote
			if t.inSingleQuote or t.inDoubleQuote:
				t.addCharacter(c)
				cont(); continue
			if c == '/' and i + 1 < len(data) and\
			   data[i + 1] == '/':
				# A //comment ends the statement, but only if
				# not in parenthesis.
				if not t.inParens:
					self.__parseTokens(t)
				t.inComment = True
				cont(); continue
			if c == '=' and len(t.tokens) == 1 and\
			   not t.haveLabelToken() and not t.curToken and\
			   cNext != '=':
				# NAME = VALUE assignment
				t.inAssignment = True
				t.addCharacter(c)
				t.finishCurToken()
				cont(); continue
			if t.tokens or self.__inVariableSection():
				# This is not the first token of the statement.
				# or we are in variable declaration.
				if (c == '(' and t.haveLabelToken() and len(t.tokens) >= 2) or\
				   (c == '(' and not t.haveLabelToken()):
					# Parenthesis begin
					t.inParens = True
					t.addCharacter(c)
					t.finishCurToken()
					cont(); continue
				if t.inParens and c == ')':
					# Parenthesis end
					t.inParens = False
					t.finishCurToken()
					t.addToken(c)
					cont(); continue
				if ((self.__inAnyHeaderOrGlobal() or self.__inVariableSection()) and\
				    c in {'=', ':', '{', '}', '.'}) or\
				   c in {',', '[', ']'} or\
				   (c == '=' and len(t.tokens) == 1 and not t.curToken):
					# Handle non-space token separators.
					if (c == ':' and cNext == '=') or\
					   (c == '.' and cNext == '.'):
						# We are at the 'colon' character of a ':=' assignment
						# or the first '.' or a '..'
						t.finishCurToken()
						t.addCharacter(c)
					elif (c == '=' and t.curToken == ':') or\
					     (c == '.' and t.curToken == '.'):
						# We are at the 'equal' character of a ':=' assignment
						# or the second '.' or a '..'
						t.addCharacter(c)
						t.finishCurToken()
					elif c == '.':
						# This is only a single '.'
						t.addCharacter(c)
					elif c == '=':
						# '=' is not a separator here.
						# (e.g. might be a '==0' operator)
						t.addCharacter(c)
					else:
						# Any other non-space token separator.
						t.finishCurToken()
						t.addToken(c)
					cont(); continue
			else:
				# This is the first token of the statement.
				if c == '[':
					# This is the start of an array subscript.
					# Handle it as separator.
					t.finishCurToken()
					t.addToken(c)
					cont(); continue
			if not t.inParens:
				# Check whether we have tokenized a whole statement.
				# In variable sections, this is if we hit a semicolon or
				# END_STRUCT, END_VAR or END_DATA_BLOCK.
				# In code, this is if we hit a semicolon or newline (for convenience).
				wholeStatementOk = False
				if self.__inVariableSection():
					if c.isspace() and\
					   t.curToken.upper() in ("END_STRUCT", "END_VAR", "END_DATA_BLOCK"):
						wholeStatementOk = True
					if c == ';':
						wholeStatementOk = True
				elif c in {';', '\n'}:
					wholeStatementOk = True
				if wholeStatementOk:
					self.__parseTokens(t)
					cont(); continue
			if c.isspace():
				t.finishCurToken()
			else:
				t.addCharacter(c)
			cont(); continue
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
		elif self.state == self.STATE_IN_UDT_HDR:
			self.__parseTokens_udt_hdr(tokenizerState)
		elif self.state == self.STATE_IN_UDT_HDR_STRUCT:
			self.__parseTokens_udt_hdr_struct(tokenizerState)
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
				if dbNumber in self.tree.dbs:
					raise AwlParserError("Multiple definitions "
						"of DB %s" % str(dbNumber))
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
				if fbNumber in self.tree.fbs:
					raise AwlParserError("Multiple definitions "
						"of FB %s" % str(fbNumber))
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
				if fcNumber in self.tree.fcs:
					raise AwlParserError("Multiple definitions "
						"of FC %s" % str(fcNumber))
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
				if obNumber in self.tree.obs:
					raise AwlParserError("Multiple definitions "
						"of OB %s" % str(obNumber))
				self.tree.obs[obNumber] = self.tree.curBlock
				return
			if t.tokens[0].upper() == "TYPE":
				self.__setState(self.STATE_IN_UDT_HDR)
				if t.tokens[1].startswith('"') and\
				   t.tokens[1].endswith('"'):
					# UDT name is symbolic
					udtNumber = t.tokens[1][1:-1]
				else:
					# UDT name is absolute
					if t.tokens[1].upper() != "UDT":
						raise AwlParserError("Invalid UDT name")
					try:
						udtNumber = int(t.tokens[2], 10)
					except ValueError:
						raise AwlParserError("Invalid UDT number")
				self.tree.curBlock = RawAwlUDT(self.tree, udtNumber)
				if udtNumber in self.tree.udts:
					raise AwlParserError("Multiple definitions "
						"of UDT %s" % str(udtNumber))
				self.tree.udts[udtNumber] = self.tree.curBlock
				return
		except IndexError as e:
			raise AwlParserError("Missing token")
		except ValueError as e:
			raise AwlParserError("Invalid value")
		raise AwlParserError("Unknown statement: %s" % " ".join(t.tokens))

	def __parseInstruction(self, t):
		insn = RawAwlInsn(self.tree.curBlock)
		insn.setLineNr(t.tokensLineNr)
		insn.setSourceId(self.tree.sourceId)
		if t.tokens[0].endswith(":"):
			# First token is a label
			if len(t.tokens) <= 1:
				raise AwlParserError("Invalid standalone label")
			label = t.tokens[0][0:-1]
			if not label or not AwlName.isValidLabel(label):
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
		elif name == "STANDARD":
			# This is a standard block. Do nothing for now.
			pass
		elif name == "KNOW_HOW_PROTECT":
			# Nice try.
			pass
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
			self.tree.curBlock.fb = RawAwlDB.FBRef(fbNumber = fbNumber,
							       isSFB = (name == "SFB"))
		elif name.startswith('"') and name.endswith('"'):
			fbSymbol = name[1:-1]
			self.tree.curBlock.fb = RawAwlDB.FBRef(fbSymbol = fbSymbol)
		else:
			raise AwlParserError("In DB header: Unknown token: %s\n"\
					     "Maybe missing semicolon in preceding lines?"\
					     % name)

	def __parseArrayInitializer(self, baseIdents, dimensions, initsList, tokens):
		"""Parse an ARRAY initializer. That is either of:
		1, 2, 3, 4
		4 (1, 2, 3, 4)
		or similar.
		baseIdents -> The identifiers of the array base.
		dimensions -> The array dimensions.
		initsList -> The result list. Each element is a RawAwlDataInit().
		tokens -> The tokens to parse."""

		# Make an identifier chain that points to the first array index.
		identChain = [ ident.dup() for ident in baseIdents ]
		identChain[-1].indices = [dim[0] for dim in dimensions]

		repeatCount = None
		repeatValues = []
		valueTokens = []

		def addInit(valTokens):
			#FIXME only need to dup the last element
			init = RawAwlDataInit([ ident.dup() for ident in identChain ],
					      valTokens)
			initsList.append(init)
			identChain[-1].advanceToNextArrayElement(dimensions)

		while tokens:
			if tokens[0] == ',':
				if repeatCount is None:
					addInit(valueTokens)
				else:
					repeatValues.append(valueTokens)
				valueTokens = []
			elif tokens[0] == '(':
				if repeatCount is not None:
					raise AwlParserError("Nested data initialization "
						"repetitions are not allowed.")
				# Starting a repetition. The current valueTokens
				# is the repeat count.
				try:
					if len(valueTokens) != 1:
						raise ValueError
					repeatCount = int(valueTokens[0])
				except ValueError:
					raise AwlParserError("Invalid repeat count.")
				if repeatCount <= 0 or repeatCount > 0x7FFF:
					raise AwlParserError("Repeat count is out of range. "
						"Count must be between 1 and 32767.")
				valueTokens = []
			elif tokens[0] == ')':
				repeatValues.append(valueTokens)
				valueTokens = []
				if repeatCount is None:
					raise AwlParserError("Too many closing parenthesis.")
				# Add the repeated values to the init list.
				for i in range(repeatCount):
					for valToks in repeatValues:
						addInit(valToks)
				repeatCount = None
				repeatValues = []
			else:
				valueTokens.append(tokens[0])
			tokens = tokens[1:]
		if valueTokens:
			addInit(valueTokens)

	def __parse_var_generic(self, t, varList,
				endToken,
				mayHaveInitval=True):
		if len(t.tokens) >= 1 and\
		   t.tokens[0].upper() == "END_STRUCT" and\
		   self.tree.curDataField:
			if len(t.tokens) > 1:
				raise AwlParserError("Unknown trailing tokens.")
			# This is the STRUCT end.
			# Revert to our parent (might be None).
			self.tree.curDataField = self.tree.curDataField.parent
			return True
		if t.tokens[0].upper() == endToken:
			return False
		colonIdx = listIndex(t.tokens, ":")
		assignIdx = listIndex(t.tokens, ":=")
		initsList = []
		isStructDecl = False
		if len(t.tokens) >= 10 and\
		   colonIdx == 1 and t.tokens[colonIdx+1].upper() == "ARRAY":
			# This is an array variable.
			ofIdx = listIndex(t.tokens, "OF",
					  translate=lambda i, v: v.upper())
			if len(t.tokens) > ofIdx + 1 and\
			   t.tokens[ofIdx + 1].upper() == "STRUCT":
				# The data type is a STRUCT declaration.
				isStructDecl = True
			if assignIdx >= 0 and not isStructDecl:
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
			if assignIdx >= 0 and not isStructDecl:
				type = t.tokens[ofIdx+1:assignIdx]
			else:
				type = t.tokens[ofIdx+1:]
			if assignIdx >= 0 and not isStructDecl:
				# Parse the ARRAY initializer (:= ...)
				identChain = (self.tree.curDataField.getIdentChain() if\
					      self.tree.curDataField else []) +\
					     [ AwlDataIdent(name), ]
				initTokens = t.tokens[assignIdx+1:]
				self.__parseArrayInitializer(identChain,
							     dimensions,
							     initsList,
							     initTokens)
		else:
			# This is a normal non-array variable.
			dimensions = None
			if len(t.tokens) > colonIdx + 1 and\
			   t.tokens[colonIdx + 1].upper() == "STRUCT":
				# The data type is a STRUCT declaration.
				isStructDecl = True
			if mayHaveInitval and not isStructDecl and\
			   colonIdx == 1 and assignIdx > colonIdx + 1:
				name = t.tokens[0]
				type = t.tokens[colonIdx+1:assignIdx]
				initTokens = t.tokens[assignIdx+1:]
			elif colonIdx == 1:
				name = t.tokens[0]
				type = t.tokens[colonIdx+1:]
				initTokens = None
			else:
				raise AwlParserError("In variable section: Unknown tokens.\n"\
						     "Maybe missing semicolon in preceding lines?")

			if initTokens:
				identChain = (self.tree.curDataField.getIdentChain() if\
					      self.tree.curDataField else []) +\
					     [ AwlDataIdent(name), ]
				initsList.append(RawAwlDataInit(identChain, initTokens))

		trailing = None
		if isStructDecl:
			# The type is just 'STRUCT' and the trailing tokens
			# are the first sub-variable declaration.
			trailing = type[1:]
			type = type[0:1]

		# Make the raw data field and add it to the variable list.
		field = RawAwlDataField(ident = AwlDataIdent(name),
					typeTokens = type,
					dimensions = dimensions,
					defaultInits = initsList)
		if self.tree.curDataField:
			self.tree.curDataField.children.append(field)
			field.parent = self.tree.curDataField
		else:
			varList.append(field)
		if isStructDecl:
			self.tree.curDataField = field

		if trailing:
			# There were trailing tokens (STRUCT declaration).
			# Parse and add these to the variable list, too.
			t.tokens = trailing
			return self.__parse_var_generic(t,
							varList, endToken,
							mayHaveInitval)
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

		# Variable assignment (data initialization)

		assignIdx = listIndex(t.tokens, ":=")

		# Extract identifier tokens and value tokens.
		# Split identifier tokens by '.'
		identTokens = listExpand(t.tokens[:assignIdx],
			lambda e: strPartitionFull(e, '.', keepEmpty=False))
		valueTokens = t.tokens[assignIdx+1:]

		# Create the identifier chain.
		identChain = AwlDataIdentChain.parseTokens(identTokens)
		if not identChain:
			raise AwlParserError("Invalid variable assignment")
		dataInit = RawAwlDataInit(identChain.idents, valueTokens)
		db = self.tree.curBlock
		db.addFieldInit(dataInit)

	def __parseTokens_fb_hdr(self, t):
		name = t.tokens[0].upper()
		if name == "BEGIN":
			self.__setState(self.STATE_IN_FB)
		elif name in ("TITLE", "AUTHOR", "FAMILY", "NAME", "VERSION"):
			self.tree.curBlock.addDescriptor(t.tokens)
		elif name == "STANDARD":
			# This is a standard block. Do nothing for now.
			pass
		elif name == "KNOW_HOW_PROTECT":
			# Nice try.
			pass
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
			raise AwlParserError("In FB: Unknown token: %s\n"\
					     "Maybe missing semicolon in preceding lines?"\
					     % name)

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
		elif name == "STANDARD":
			# This is a standard block. Do nothing for now.
			pass
		elif name == "KNOW_HOW_PROTECT":
			# Nice try.
			pass
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
			raise AwlParserError("In FC header: Unknown token: %s\n"\
					     "Maybe missing semicolon in preceding lines?"\
					     % name)

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
		elif name == "STANDARD":
			# This is a standard block. Do nothing for now.
			pass
		elif name == "KNOW_HOW_PROTECT":
			# Nice try.
			pass
		elif name == "{":
			#TODO: parse attributes
			if "}" not in t.tokens:
				self.__setState(self.STATE_IN_OB_HDR_ATTR)
		else:
			raise AwlParserError("In OB header: Unknown token: %s\n"\
					     "Maybe missing semicolon in preceding lines?"\
					     % name)

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

	def __parseTokens_udt_hdr(self, t):
		name = t.tokens[0].upper()
		if name == "END_TYPE":
			self.__setState(self.STATE_GLOBAL)
		elif name in ("TITLE", "AUTHOR", "FAMILY", "NAME", "VERSION"):
			self.tree.curBlock.addDescriptor(t.tokens)
		elif name == "STANDARD":
			# This is a standard block. Do nothing for now.
			pass
		elif name == "KNOW_HOW_PROTECT":
			# Nice try.
			pass
		elif name == "STRUCT":
			self.__setState(self.STATE_IN_UDT_HDR_STRUCT)
		else:
			raise AwlParserError("In UDT: Unknown token: %s\n"\
					     "Maybe missing semicolon in preceding lines?"\
					     % name)

	def __parseTokens_udt_hdr_struct(self, t):
		if not self.__parse_var_generic(t,
				varList = self.tree.curBlock.fields,
				endToken = "END_STRUCT"):
			self.__setState(self.STATE_IN_UDT_HDR)

	def parseSource(self, awlSource):
		"""Parse an AWL source.
		awlSource is an AwlSource instance."""
		self.parseData(awlSource.sourceBytes,
			       sourceId = awlSource.identHash,
			       sourceName = awlSource.name)

	@classmethod
	def sourceIsFlat(cls, sourceText):
		"""Returns whether the source is 'flat'.
		A flat source is one without block definitions and
		just plain AWL code."""
		haveDB = re.match(r'.*^\s*DATA_BLOCK\s+.*', sourceText,
				  re.DOTALL | re.MULTILINE)
		haveFB = re.match(r'.*^\s*FUNCTION_BLOCK\s+.*', sourceText,
				  re.DOTALL | re.MULTILINE)
		haveFC = re.match(r'.*^\s*FUNCTION\s+.*', sourceText,
				  re.DOTALL | re.MULTILINE)
		haveOB = re.match(r'.*^\s*ORGANIZATION_BLOCK\s+.*', sourceText,
				  re.DOTALL | re.MULTILINE)
		haveUDT = re.match(r'.*^\s*TYPE\s+.*', sourceText,
				   re.DOTALL | re.MULTILINE)
		return not bool(haveDB) and not bool(haveFB) and\
		       not bool(haveFC) and not bool(haveOB) and\
		       not bool(haveUDT)

	def parseText(self, sourceText, sourceId=None, sourceName=None):
		self.flatLayout = self.sourceIsFlat(sourceText)
		try:
			self.__tokenize(sourceText, sourceId, sourceName)
		except AwlParserError as e:
			e.setLineNr(self.lineNr)
			e.setSourceId(sourceId)
			e.setSourceName(sourceName)
			raise e

	def parseData(self, sourceBytes, sourceId=None, sourceName=None):
		try:
			return self.parseText(sourceBytes.decode(AwlSource.ENCODING),
					      sourceId, sourceName)
		except UnicodeError as e:
			raise AwlParserError("Could not decode the AWL/STL "
				"source code. It contains invalid characters. "
				"The text encoding should be '%s'." %\
				AwlSource.ENCODING)

	def getParseTree(self):
		return self.tree
