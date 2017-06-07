# -*- coding: utf-8 -*-
#
# AWL simulator - symbol table parser
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.exceptions import *
from awlsim.common.cpuconfig import *

from awlsim.core.memory import * #+cimport
from awlsim.core.util import *

from awlsim.awlcompiler.optrans import *

import csv


__all__ = [
	"Symbol",
	"SymbolTable",
	"SymTabParser",
	"SymTabParser_ASC",
	"SymTabParser_CSV",
]


class AwlsimSymTabCSVDialect(csv.Dialect):
	delimiter = str(';')
	quotechar = str('"')
	doublequote = True
	skipinitialspace = True
	lineterminator = str('\r\n')
	quoting = csv.QUOTE_MINIMAL
	escapechar = None
csv.register_dialect("awlsim_symtab", AwlsimSymTabCSVDialect)

class Symbol(object):
	"""One symbol.
	"""

	def __init__(self, name="", operator=None, type=None, comment="",
		     mnemonics=S7CPUConfig.MNEMONICS_AUTO,
		     lineNr=None, symTab=None):
		self.setSymTab(symTab)
		self.setName(name)		# The symbol name string
		self.setOperator(operator)	# The symbol address (AwlOperator)
		self.setType(type)		# The symbol type (AwlDataType)
		self.setComment(comment)	# The comment string
		self.setMnemonics(mnemonics)
		self.setLineNr(lineNr)

	def isValid(self):
		return self.name and self.operator and self.type

	def validate(self):
		name = self.name if self.name else "<no name>"
		if not self.isValid():
			raise AwlSimError("Symbol '%s' is incomplete. "
				"Cannot generate symbol information." % name)

	def setSymTab(self, symTab):
		self.symTab = symTab

	def getSymTab(self):
		return self.symTab

	def setName(self, newName):
		if newName is not None and len(newName) > 24:
			raise AwlSimError("Symbol table parser: Symbol name '%s' is "
				"too long. Maximum is 24 characters." % newName)
		self.name = newName

	def getName(self):
		return self.name

	def setOperator(self, newOperator):
		self.operator = newOperator

	def setOperatorString(self, newOperatorString):
		if not newOperatorString.strip():
			self.setOperator(None)
			return
		for m in (S7CPUConfig.MNEMONICS_EN, S7CPUConfig.MNEMONICS_DE):
			if self.mnemonics != S7CPUConfig.MNEMONICS_AUTO and\
			   self.mnemonics != m:
				continue
			with contextlib.suppress(AwlSimError):
				opTrans = AwlOpTranslator(mnemonics=m)
				opDesc = opTrans.translateFromString(newOperatorString)
				self.setOperator(opDesc.operator)
				return
		raise AwlSimError("Symbol table parser: Can't parse symbol "
			"address '%s' in line %s" %\
			(newOperatorString, self.getLineNrString()))

	def getOperator(self):
		return self.operator

	def getOperatorString(self):
		operator = self.getOperator()
		if operator:
			return str(operator)
		return ""

	def setType(self, newType):
		self.type = newType

	def setTypeString(self, newTypeString):
		if not newTypeString:
			self.setType(None)
			return
		try:
			from awlsim.core.datatypes import AwlDataType
			awlType = AwlDataType.makeByName(newTypeString.split())
		except AwlSimError as e:
			raise AwlSimError("Symbol table parser: Can't parse symbol "
				"type '%s' in line %s" %\
				(newTypeString, self.getLineNrString()))
		self.setType(awlType)

	def getType(self):
		return self.type

	def getTypeString(self):
		type = self.getType()
		if type:
			return str(type)
		return ""

	def setComment(self, newComment):
		if newComment is not None and len(newComment) > 80:
			raise AwlSimError("Symbol table parser: Symbol comment string of symbol '%s' is "
				"too long. Maximum is 80 characters." % self.name)
		self.comment = newComment

	def getComment(self):
		return self.comment

	def setMnemonics(self, newMnemonics):
		self.mnemonics = newMnemonics

	def setLineNr(self, newLineNr):
		self.lineNr = newLineNr

	def getLineNrString(self):
		return self.lineNr if self.lineNr is not None else "<unknown>"

	def nameIsEqual(self, otherName):
		if self.name is None or otherName is None:
			return False
		return self.name.lower() == otherName.lower()

	def __csvRecord(self, value):
		value = str(value)
		value = value.replace('"', '""')
		if ';' in value or\
		   '"' in value or\
		   '\r' in value or\
		   '\n' in value:
			value = '"' + value + '"'
		return value

	def toCSV(self):
		# Returns compact CSV of this symbol.
		self.validate()
		try:
			name = self.__csvRecord(self.name)
			operator = self.__csvRecord(self.operator)
			type = self.__csvRecord(self.type)
			comment = self.__csvRecord(self.comment)
			return ''.join((name, ';', operator, ';',
					 type, ';', comment, '\r\n'))
		except UnicodeError as e:
			raise AwlSimError("Unicode error while trying to generate "
				"symbol CSV dump.")

	def toReadableCSV(self):
		# Returns human readable, but also machine processable
		# CSV of this symbol.
		self.validate()
		try:
			name = self.__csvRecord(self.name)
			operator = self.__csvRecord(self.operator)
			type = self.__csvRecord(self.type)
			comment = self.__csvRecord(self.comment)
			namePadding = " " * (24 - len(name)) + " "
			operatorPadding = " " * (11 - len(operator)) + " "
			if comment:
				typePadding = " " * (9 - len(type)) + " "
			else:
				typePadding = ""
			return ''.join((name, ';', namePadding,
					operator, ';', operatorPadding,
					type, ';', typePadding,
					comment, '\r\n'))
		except UnicodeError as e:
			raise AwlSimError("Unicode error while trying to generate "
				"symbol CSV dump.")

	def toASC(self, stripWhitespace=False):
		# Returns ASC format of this symbol.
		self.validate()
		try:
			name = str(self.name)
			operator = str(self.operator)
			type = str(self.type)
			comment = str(self.comment)
			name += " " * (24 - len(name))
			operator += " " * (11 - len(operator))
			type += " " * (9 - len(type))
			comment += " " * (80 - len(comment))
			line = ''.join(('126,', name, operator,
					' ', type, ' ', comment))
			if stripWhitespace:
				# Strip the right hand white space.
				# This does not produce compliant ASC format.
				# But the Awlsim parser supports this as
				# an editing convenience.
				# See SymTabParser_ASC.
				# This is an Awlsim extension.
				line = line.rstrip()
				minLen = SymTabParser_ASC.LEN_LEN +\
					 SymTabParser_ASC.LEN_NAME +\
					 SymTabParser_ASC.LEN_ADDR + 1
				if len(line) < minLen:
					line += " " * (minLen - len(line))
			line += '\r\n'
		except UnicodeError as e:
			raise AwlSimError("Unicode error while trying to generate "
				"symbol ASC dump.")
		return line

	def __repr__(self):
		return self.toReadableCSV()

class SymbolTable(object):
	"""Parsed symbol table.
	"""

	def __init__(self):
		self.clear()

	def clear(self):
		self.__symbolsList = []
 
	def toCSV(self):
		return "".join(s.toCSV()\
			       for s in self.__symbolsList)

	def toReadableCSV(self):
		return "".join(s.toReadableCSV()\
			       for s in self.__symbolsList)

	def toASC(self, stripWhitespace=False):
		return "".join(s.toASC(stripWhitespace=stripWhitespace)\
			       for s in self.__symbolsList)

	def __repr__(self):
		return self.toReadableCSV()

	def __len__(self):
		return len(self.__symbolsList)

	def __iter__(self):
		for symbol in self.__symbolsList:
			yield symbol

	def __reversed__(self):
		for symbol in reversed(self.__symbolsList):
			yield symbol

	def __getitem__(self, index):
		return self.__symbolsList[index]

	def __setitem__(self, index, symbol):
		self.pop(index)
		self.insert(index, symbol)

	def __delitem__(self, index):
		self.pop(index)

	def __contains__(self, value):
		if value is None:
			return False
		elif isString(value):
			index, symbol = self.__findByName(value)
			return symbol is not None
		elif isinstance(value, Symbol):
			name = value.getName()
			if name is None:
				return False
			index, symbol = self.__findByName(name)
			return symbol is not None
		raise TypeError

	def pop(self, index):
		"""Get symbol by index and remove it from the table."""
		symbol = self.__symbolsList.pop(index)
		symbol.setSymTab(None)
		return symbol

	def insert(self, index, symbol):
		"""Insert a symbol before index."""
		if symbol in self:
			raise AwlSimError("Multiple definitions of "
				"symbol '%s'" % symbol.getName())
		self.__symbolsList.insert(index, symbol)
		symbol.setSymTab(self)

	def add(self, symbol, overrideExisting = False):
		if symbol in self:
			if overrideExisting:
				i = self.findIndexByName(symbol.getName())
				assert(i is not None)
				self[i] = symbol
			else:
				raise AwlSimError("Multiple definitions of "
					"symbol '%s'" % symbol.getName())
		self.__symbolsList.append(symbol)
		symbol.setSymTab(self)

	def __findByName(self, name):
		name = name.lower()
		for i, symbol in enumerate(self.__symbolsList):
			if name == symbol.getName().lower():
				return i, symbol
		return None, None

	def findByName(self, name):
		index, symbol = self.__findByName(name)
		return symbol

	def findIndexByName(self, name):
		index, symbol = self.__findByName(name)
		return index

	def getByDataType(self, dataType):
		"""Get all symbols with the given AwlDataType.
		Returns a generator.
		"""
		return (symbol for symbol in self.__symbolsList\
			if symbol.getType() == dataType)

	def merge(self, other, overrideExisting = False):
		"""Merge 'other' into 'self'"""
		for symbol in other.__symbolsList:
			self.add(symbol, overrideExisting)

class SymTabParser(object):
	"""Abstract symbol table parser.
	"""

	implementations = []

	@classmethod
	def parseSource(cls, source,
			autodetectFormat=True,
			mnemonics=S7CPUConfig.MNEMONICS_AUTO):
		return cls.parseText(source.sourceText, autodetectFormat, mnemonics)

	@classmethod
	def parseText(cls, sourceText,
		      autodetectFormat=True,
		      mnemonics=S7CPUConfig.MNEMONICS_AUTO):
		try:
			if not sourceText.strip():
				return SymbolTable()
			if autodetectFormat:
				for implCls in cls.implementations:
					if implCls._probe(sourceText):
						parserClass = implCls
						break
				else:
					raise AwlSimError("Failed to find a suitable "\
						"symbol table parser")
			else:
				parserClass = cls
			if mnemonics == S7CPUConfig.MNEMONICS_AUTO:
				instance = parserClass(S7CPUConfig.MNEMONICS_EN)
				try:
					symTab = instance._parse(sourceText)
				except AwlSimError as e:
					instance = parserClass(S7CPUConfig.MNEMONICS_DE)
					symTab = instance._parse(sourceText)
			else:
				instance = parserClass(mnemonics)
				symTab = instance._parse(sourceText)
			return symTab
		except UnicodeError as e:
			raise AwlSimError("Encoding error while trying to decode "
				"symbol table.")

	@classmethod
	def _probe(cls, sourceText):
		try:
			if not sourceText.strip():
				return False
			p = cls(None)
			p._parse(sourceText, probeOnly=True)
		except AwlSimError as e:
			return False
		except UnicodeError as e:
			return False
		return True

	def __init__(self, mnemonics):
		self.mnemonics = mnemonics

	def _parse(self, data, probeOnly=False):
		raise NotImplementedError

	def parseSym(self, symName, symAddr, symType, symComment,
		     lineNr):
		symName = symName.strip()
		symAddr = symAddr.strip().upper()
		symType = symType.strip().upper()
		symComment = symComment.strip()
		if not symName:
			raise AwlSimError("Symbol table parser: Unnamed symbol "
				"in line %d" % lineNr)
		if not symAddr:
			raise AwlSimError("Symbol table parser: Symbol '%s' lacks "
				"an address (line %d)" % (symName, lineNr))
		if len(symAddr) > 11:
			raise AwlSimError("Symbol table parser: Symbol address string of symbol '%s' is "
				"too long. Maximum is 11 characters." % symName)
		if len(symType) > 9:
			raise AwlSimError("Symbol table parser: Symbol type string of symbol '%s' is "
				"too long. Maximum is 9 characters." % symName)
		if symAddr.startswith("VAT") and not symType:
			symType = symAddr
		if not symType:
			raise AwlSimError("Symbol table parser: Symbol '%s' lacks "
				"a type (line %d)" % (symName, lineNr))
		sym = Symbol(name = symName,
			     comment = symComment,
			     mnemonics = self.mnemonics,
			     lineNr = lineNr)
		sym.setOperatorString(symAddr)
		sym.setTypeString(symType)
		return sym

class SymTabParser_ASC(SymTabParser):
	"""ASC symbol table file parser.
	"""

	# Character lengths of the fields.
	# (The length field being restricted to 4 characters
	#  is an Awlsim restriction.)
	LEN_LEN		= 4
	LEN_NAME	= 24
	LEN_ADDR	= 12
	LEN_TYPE	= 10
	LEN_COMMENT	= 80

	def _parse(self, data, probeOnly=False):
		table = SymbolTable()
		lines = data.splitlines()
		for i, line in enumerate(lines):
			lineNr = i + 1
			if not line.strip():
				continue
			if not line.startswith("126,"):
				# Technically it is allowed to have a different length
				# prefix, but we do not support that.
				# S7 and Awlsim do only generate entries with
				# 126 characters, so we restrict the parser to that.
				raise AwlSimError("ASC symbol table parser: "\
					"Invalid line start (!= '126,') in "\
					"line %d" % lineNr)
			if len(line) >= self.LEN_LEN + self.LEN_NAME + self.LEN_ADDR + 1 and\
			   len(line) < 130:
				# As a convenience we support entries with the trailing
				# whitespace after the data type being stripped.
				# (We assume a data type length of at least 1 character here)
				# Just add some white space to fill the 130 characters.
				# This is an Awlsim extension.
				line += " " * (130 - len(line))
			if len(line) != 130:
				raise AwlSimError("ASC symbol table parser: "\
					"Invalid line length (!= 130 chars) in "\
					"line %d" % lineNr)
			offs = self.LEN_LEN
			symName = line[offs : offs + self.LEN_NAME]
			offs += self.LEN_NAME
			symAddr = line[offs : offs + self.LEN_ADDR]
			offs += self.LEN_ADDR
			symType = line[offs : offs + self.LEN_TYPE]
			offs += self.LEN_TYPE
			symComment = line[offs : ]
			if not probeOnly:
				table.add(self.parseSym(symName = symName,
							symAddr = symAddr,
							symType = symType,
							symComment = symComment,
							lineNr = lineNr))
		return table

SymTabParser.implementations.append(SymTabParser_ASC)

class SymTabParser_CSV(SymTabParser):
	"""CSV symbol table file parser.
	"""

	def _parse(self, data, probeOnly=False):
		table = SymbolTable()
		csvReader = csv.reader(data.splitlines(),
				       dialect="awlsim_symtab")
		for i, row in enumerate(csvReader):
			lineNr = i + 1
			if len(row) != 4:
				raise AwlSimError("Wrong record count in "
					"line %d. Expected 4, but got %d records." %\
					(lineNr, len(row)))
			if not probeOnly:
				table.add(self.parseSym(symName = row[0],
							symAddr = row[1],
							symType = row[2],
							symComment = row[3],
							lineNr = lineNr))
		return table

SymTabParser.implementations.append(SymTabParser_CSV)
