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


class Symbol(object):
	"""One symbol."""

	def __init__(self, name, operator, type, comment=""):
		self.name = name		# The symbol name string
		self.operator = operator	# The symbol address (AwlOperator)
		self.type = type		# The symbol type (AwlDataType)
		self.comment = comment		# The comment string

	def nameIsEqual(self, otherName):
		return self.name.upper() == otherName.upper()

	def __repr__(self):
		return '"%s", "%s", "%s", "%s"' %\
			(str(self.name), str(self.operator),
			 str(self.type), str(self.comment))

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

	def __repr__(self):
		return "\n".join(str(s) for s in self.symbols)

class SymTabParser(object):
	"""Abstract symbol table parser."""

	implementations = []

	@classmethod
	def parseFile(cls, filename,
		      autodetectFormat=True,
		      mnemonics=S7CPUSpecs.MNEMONICS_AUTO):
		data = awlFileRead(filename)
		return cls.parseData(data, autodetectFormat, mnemonics)

	@classmethod
	def parseData(cls, data,
		      autodetectFormat=True,
		      mnemonics=S7CPUSpecs.MNEMONICS_AUTO):
		if autodetectFormat:
			for implCls in cls.implementations:
				if implCls._probe(data):
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
				symTab = instance._parse(data)
			except AwlSimError as e:
				instance = parserClass(S7CPUSpecs.MNEMONICS_DE)
				symTab = instance._parse(data)
		else:
			instance = parserClass(mnemonics)
			symTab = instance._parse(data)
		return symTab

	@classmethod
	def _probe(cls, data):
		raise NotImplementedError

	def __init__(self, mnemonics):
		self.mnemonics = mnemonics

	def _parse(self, data):
		pass

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
		if symAddr.startswith("VAT") and not symType:
			symType = symAddr
		if not symType:
			raise AwlSimError("Symbol table parser: Symbol '%s' lacks "
				"a type (line %d)" % (symName, lineNr))
		try:
			awlType = AwlDataType.makeByName(symType.split())
		except AwlSimError as e:
			raise AwlSimError("Symbol table parser: Can't parse symbol "
				"type '%s' in line %d" % (symType, lineNr))
		try:
			opTrans = AwlOpTranslator(insn = None,
						  mnemonics = self.mnemonics)
			opDesc = opTrans.translateOp(rawInsn = None,
						     rawOps = symAddr.split())
		except AwlSimError as e:
			raise AwlSimError("Symbol table parser: Can't parse symbol "
				"address '%s' in line %d" % (symAddr, lineNr))
		return Symbol(name = symName,
			      operator = opDesc.operator,
			      type = awlType,
			      comment = symComment)

class SymTabParser_ASC(SymTabParser):
	@classmethod
	def _probe(cls, data):
		lines = data.splitlines()
		return lines and\
		       len(lines[0]) == 130 and\
		       lines[0].startswith("126,")

	def _parse(self, data):
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
			table.add(self._parseSym(symName = symName,
						 symAddr = symAddr,
						 symType = symType,
						 symComment = symComment,
						 lineNr = lineNr))
		return table

SymTabParser.implementations.append(SymTabParser_ASC)


if __name__ == "__main__":
	import sys
	try:
		print(SymTabParser.parseFile(sys.argv[1]))
	except AwlSimError as e:
		print(str(e))
