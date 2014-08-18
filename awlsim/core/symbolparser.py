# -*- coding: utf-8 -*-
#
# AWL simulator - symbol table parser
#
# Copyright 2014 Michael Buesch <m@bues.ch>
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

from awlsim.core.datatypes import *
from awlsim.core.cpuspecs import *
from awlsim.core.optrans import *
from awlsim.core.util import *

import csv


class AwlsimSymTabCSVDialect(csv.Dialect):
	delimiter = str(';')
	quotechar = str('"')
	doublequote = True
	skipinitialspace = True
	lineterminator = str('\r\n')
	quoting = csv.QUOTE_MINIMAL
csv.register_dialect("awlsim_symtab", AwlsimSymTabCSVDialect)

class Symbol(object):
	"""One symbol."""

	def __init__(self, name=None, operator=None, type=None, comment="",
		     mnemonics=S7CPUSpecs.MNEMONICS_AUTO,
		     lineNr=None):
		self.setName(name)		# The symbol name string
		self.setOperator(operator)	# The symbol address (AwlOperator)
		self.setType(type)		# The symbol type (AwlDataType)
		self.setComment(comment)	# The comment string
		self.setMnemonics(mnemonics)
		self.setLineNr(lineNr)

	def isValid(self):
		return self.name and self.operator and self.type

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
		for m in (S7CPUSpecs.MNEMONICS_EN, S7CPUSpecs.MNEMONICS_DE):
			if self.mnemonics != S7CPUSpecs.MNEMONICS_AUTO and\
			   self.mnemonics != m:
				continue
			try:
				opTrans = AwlOpTranslator(insn = None,
							  mnemonics = m)
				opDesc = opTrans.translateOp(rawInsn = None,
							     rawOps = newOperatorString.split())
				self.setOperator(opDesc.operator)
				return
			except AwlSimError as e:
				pass
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
		return self.name.upper() == otherName.upper()

	def __csvRecord(self, value):
		value = str(value).encode(SymTabParser_CSV.ENCODING)
		value = value.replace(b'"', b'""')
		if b';' in value or\
		   b'"' in value or\
		   b'\r' in value or\
		   b'\n' in value:
			value = b'"' + value + b'"'
		return value

	def toCSV(self):
		# Returns compact CSV of this symbol.
		# Return type is bytes.
		if not self.isValid():
			name = self.name if self.name else "<no name>"
			raise AwlSimError("Symbol '%s' is incomplete. "
				"Cannot generate symbol information." % name)
		try:
			name = self.__csvRecord(self.name)
			operator = self.__csvRecord(self.operator)
			type = self.__csvRecord(self.type)
			comment = self.__csvRecord(self.comment)
			return b''.join((name, b';', operator, b';',
					 type, b';', comment, b'\r\n'))
		except UnicodeError as e:
			raise AwlSimError("Unicode error while trying to generate "
				"symbol CSV dump.")

	def toReadableCSV(self):
		# Returns human readable, but also machine processable
		# CSV of this symbol.
		# Return type is bytes.
		if not self.isValid():
			name = self.name if self.name else "<no name>"
			raise AwlSimError("Symbol '%s' is incomplete. "
				"Cannot generate symbol information." % name)
		try:
			name = self.__csvRecord(self.name)
			operator = self.__csvRecord(self.operator)
			type = self.__csvRecord(self.type)
			comment = self.__csvRecord(self.comment)
			namePadding = b" " * (24 - len(name)) + b" "
			operatorPadding = b" " * (11 - len(operator)) + b" "
			if comment:
				typePadding = b" " * (9 - len(type)) + b" "
			else:
				typePadding = b""
			return b''.join((name, b';', namePadding,
					 operator, b';', operatorPadding,
					 type, b';', typePadding,
					 comment, b'\r\n'))
		except UnicodeError as e:
			raise AwlSimError("Unicode error while trying to generate "
				"symbol CSV dump.")

	def toASC(self):
		# Returns ASC format of this symbol.
		# Return type is bytes.
		if not self.isValid():
			name = self.name if self.name else "<no name>"
			raise AwlSimError("Symbol '%s' is incomplete. "
				"Cannot generate symbol information." % name)
		try:
			name = str(self.name).encode(SymTabParser_ASC.ENCODING)
			operator = str(self.operator).encode(SymTabParser_ASC.ENCODING)
			type = str(self.type).encode(SymTabParser_ASC.ENCODING)
			comment = str(self.comment).encode(SymTabParser_ASC.ENCODING)
			name += b" " * (24 - len(name))
			operator += b" " * (11 - len(operator))
			type += b" " * (9 - len(type))
			comment += b" " * (80 - len(comment))
			return b''.join((b'126,', name, operator,
					 b' ', type, b' ', comment, b'\r\n'))
		except UnicodeError as e:
			raise AwlSimError("Unicode error while trying to generate "
				"symbol ASC dump.")

	def __repr__(self):
		return self.toReadableCSV().decode(SymTabParser_CSV.ENCODING)

class SymbolTable(object):
	"""Parsed symbol table."""

	def __init__(self):
		self.clear()

	def clear(self):
		self.symbols = []

	def add(self, symbol):
		if self.findByName(symbol.name):
			raise AwlSimError("Multiple definitions of "
				"symbol '%s'" % symbol.name)
		self.symbols.append(symbol)

	def findByName(self, name):
		for symbol in self.symbols:
			if symbol.nameIsEqual(name):
				return symbol
		return None

	def merge(self, other):
		"""Merge 'other' into 'self'"""
		for symbol in other.symbols:
			self.add(symbol)

	def toCSV(self):
		return b"".join(s.toCSV() for s in self.symbols)

	def toReadableCSV(self):
		return b"".join(s.toReadableCSV() for s in self.symbols)

	def toASC(self):
		return b"".join(s.toASC() for s in self.symbols)

	def __repr__(self):
		return self.toReadableCSV().decode(SymTabParser_CSV.ENCODING)

class SymTabParser(object):
	"""Abstract symbol table parser."""

	ENCODING	= "latin_1"

	implementations = []

	@classmethod
	def parseSource(cls, source,
			autodetectFormat=True,
			mnemonics=S7CPUSpecs.MNEMONICS_AUTO):
		return cls.parseData(source.sourceBytes, autodetectFormat, mnemonics)

	@classmethod
	def parseData(cls, dataBytes,
		      autodetectFormat=True,
		      mnemonics=S7CPUSpecs.MNEMONICS_AUTO):
		try:
			if not dataBytes.strip():
				return SymbolTable()
			if autodetectFormat:
				for implCls in cls.implementations:
					if implCls._probe(dataBytes):
						parserClass = implCls
						break
				else:
					raise AwlSimError("Failed to find a suitable "\
						"symbol table parser")
			else:
				parserClass = cls
			if mnemonics == S7CPUSpecs.MNEMONICS_AUTO:
				instance = parserClass(S7CPUSpecs.MNEMONICS_EN)
				try:
					symTab = instance._parse(dataBytes)
				except AwlSimError as e:
					instance = parserClass(S7CPUSpecs.MNEMONICS_DE)
					symTab = instance._parse(dataBytes)
			else:
				instance = parserClass(mnemonics)
				symTab = instance._parse(dataBytes)
			return symTab
		except UnicodeError as e:
			raise AwlSimError("Encoding error while trying to decode "
				"symbol table.")

	@classmethod
	def _probe(cls, dataBytes):
		try:
			if not dataBytes.decode(cls.ENCODING).strip():
				return False
			p = cls(None)
			p._parse(dataBytes, probeOnly=True)
		except AwlSimError as e:
			return False
		except UnicodeError as e:
			return False
		return True

	def __init__(self, mnemonics):
		self.mnemonics = mnemonics

	def _parse(self, data, probeOnly=False):
		raise NotImplementedError

	def _parseSym(self, symName, symAddr, symType, symComment,
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
	def _parse(self, dataBytes, probeOnly=False):
		data = dataBytes.decode(self.ENCODING)
		table = SymbolTable()
		lines = data.splitlines()
		for i, line in enumerate(lines):
			lineNr = i + 1
			if not line.strip():
				continue
			if len(line) != 130:
				raise AwlSimError("ASC symbol table parser: "\
					"Invalid line length (!= 130 chars) in "\
					"line %d" % lineNr)
			if not line.startswith("126,"):
				raise AwlSimError("ASC symbol table parser: "\
					"Invalid line start (!= '126,') in "\
					"line %d" % lineNr)
			symName = line[4:28]
			symAddr = line[28:40]
			symType = line[40:50]
			symComment = line[50:]
			if not probeOnly:
				table.add(self._parseSym(symName = symName,
							 symAddr = symAddr,
							 symType = symType,
							 symComment = symComment,
							 lineNr = lineNr))
		return table

SymTabParser.implementations.append(SymTabParser_ASC)

class SymTabParser_CSV(SymTabParser):
	def _parse(self, dataBytes, probeOnly=False):
		data = dataBytes.decode(self.ENCODING)
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
				table.add(self._parseSym(symName = row[0],
							 symAddr = row[1],
							 symType = row[2],
							 symComment = row[3],
							 lineNr = lineNr))
		return table

SymTabParser.implementations.append(SymTabParser_CSV)
