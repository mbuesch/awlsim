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

class AwlParseTree(object):
	def __init__(self):
		pass#TODO

class AwlParser(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.insns = []

	def __parseLine(self, line, lineNr):
		line = line.strip()
		if not line:
			return None
		tokens = []
		curToken = ""
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
			if tokens and not inQuote and\
			   c in (',', '=', ':'):
				curToken = curToken.strip()
				if curToken:
					tokens.append(curToken)
				tokens.append(c)
				curToken = ""
				continue
			if not c.isspace() or inQuote:
				curToken += c
			if (c.isspace() and not inQuote) or\
			   i == len(line) - 1:
				curToken = curToken.strip()
				if curToken:
					tokens.append(curToken)
				curToken = ""
		if curToken:
			tokens.append(curToken)
		if inQuote:
			raise AwlParserError("Unterminated quote: " + line)
		return self.__parseTokens(line, tokens, lineNr)

	def __parseTokens(self, line, tokens, lineNr):
		if not tokens:
			return None
		insn = RawAwlInsn()
		insn.setLineNr(lineNr)
		if tokens[0].upper() == "FAMILY":
			pass #TODO
			return None
		if tokens[0].upper() == "AUTHOR":
			pass #TODO
			return None
		if tokens[0].upper() == "DATA_BLOCK":
			pass #TODO
			return None
		if tokens[0].upper() == "FUNCTION":
			pass #TODO
			return None
		if tokens[0].upper() == "TITLE":
			pass #TODO
			return None
		if tokens[0].upper() == "VERSION":
			pass #TODO
			return None
		if tokens[0].upper() == "BEGIN":
			pass #TODO
			return None
		if tokens[0].upper() == "NETWORK":
			pass #TODO
			return None
		if tokens[0].upper() == "END_FUNCTION":
			pass #TODO
			return None
		if tokens[0].endswith(":"):
			# First token is a label
			label = tokens[0][0:-1]
			if not label or not RawAwlInsn.isValidLabel(label):
				raise AwlParserError("Invalid label: " + line)
			insn.setLabel(label)
			tokens = tokens[1:]
		if not tokens:
			raise AwlParserError("No instruction name: " + line)
		insn.setName(tokens[0])
		tokens = tokens[1:]
		if tokens:
			# Operators to insn are specified
			insn.setOperators(tokens)
		return insn

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
			insn = self.__parseLine(line, lineNr)
			if not insn:
				continue
			self.insns.append(insn)

	def getRawInsns(self):
		return self.insns

if __name__ == "__main__":
	p = AwlParser()
	p.parseFile(sys.argv[1])
