#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# AWL parser
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import sys
import re


class AwlParserError(Exception):
	pass

class RawAwlInsn(object):
	def __init__(self):
		self.lineNr = 0
		self.label = None
		self.name = None
		self.ops = []

	__labelRe = re.compile(r'^[_a-zA-Z][_0-9a-zA-Z]{0,3}$')

	@classmethod
	def isValidLabel(cls, labelString):
		return bool(cls.__labelRe.match(labelString))

	@classmethod
	def parseLine(cls, line, lineNr):
		line = line.strip()
		if not line:
			return None
		fields = []
		curField = ""
		inQuote = False
		for i, c in enumerate(line):
			if c == '"':
				inQuote = not inQuote
			if c == ';' and not inQuote:
				break
			if not inQuote and\
			   c == '/' and i + 1 < len(line) and\
			   line[i + 1] == '/':
				break
			if c == ',' and not inQuote:
				curField = curField.strip()
				if curField:
					fields.append(curField)
				fields.append(',')
				curField = ""
				continue
			if not c.isspace() or inQuote:
				curField += c
			if (c.isspace() and not inQuote) or\
			   i == len(line) - 1:
				curField = curField.strip()
				if curField:
					fields.append(curField)
				curField = ""
		if curField:
			fields.append(curField)
		if inQuote:
			raise AwlParserError("Unterminated quote: " + line)
		return cls.parseFields(line, fields, lineNr)

	@classmethod
	def parseFields(cls, line, fields, lineNr):
		if not fields:
			return None
		insn = cls()
		insn.setLineNr(lineNr)
		if fields[0].upper().startswith("FUNCTION"):
			pass #TODO
			return None
		if fields[0].upper().startswith("TITLE"):
			pass #TODO
			return None
		if fields[0].upper().startswith("VERSION"):
			pass #TODO
			return None
		if fields[0].upper().startswith("BEGIN"):
			pass #TODO
			return None
		if fields[0].upper().startswith("NETWORK"):
			pass #TODO
			return None
		if fields[0].upper().startswith("END_FUNCTION"):
			pass #TODO
			return None
		if fields[0].endswith(":"):
			# First field is a label
			label = fields[0][0:-1]
			if not label or not cls.isValidLabel(label):
				raise AwlParserError("Invalid label: " + line)
			insn.setLabel(label)
			fields = fields[1:]
		if not fields:
			raise AwlParserError("No instruction name: " + line)
		insn.setName(fields[0])
		fields = fields[1:]
		if fields:
			# Operators to insn are specified
			insn.setOperators(fields)
		return insn

	def __repr__(self):
		ret = []
		if self.hasLabel():
			ret.append(self.getLabel() + ':\t')
		else:
			ret.append('\t')
		ret.append(self.getName())
		ret.extend(self.getOperators())
		return "\t".join(ret)

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

class AwlParser(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.insns = []

	def parseFile(self, filename):
		try:
			fd = open(filename, "r")
			data = fd.read()
			fd.close()
		except IOError as e:
			raise AwlParserError("Failed to read '%s': %s" %\
				(filename, str(e)))
		self.parseData(data)

	def parseData(self, data):
		self.reset()
		lineNr = 0
		for line in data.splitlines():
			lineNr += 1
			line = line.strip()
			if not line:
				continue
			insn = RawAwlInsn.parseLine(line, lineNr)
			if not insn:
				continue
			self.insns.append(insn)

	def getRawInsns(self):
		return self.insns

if __name__ == "__main__":
	p = AwlParser()
	p.parseFile(sys.argv[1])
