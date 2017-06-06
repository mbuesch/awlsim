# -*- coding: utf-8 -*-
#
# AWL data field identifier
#
# Copyright 2012-2015 Michael Buesch <m@bues.ch>
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

from awlsim.core.util import *


class AwlDataIdent(object):
	"""Data field identifier.
	Identifies a data field within its direct parent container."""

	UPPERCASE	= 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	LOWERCASE	= 'abcdefghijklmnopqrstuvwxyz'
	NUMBERS		= '0123456789'

	VALID_CHARS	= UPPERCASE + LOWERCASE + NUMBERS + '_'

	__slots__ = (
		"name",
		"indices",
	)

	@classmethod
	def validateName(cls, name):
		"""Check variable name against AWL naming rules.
		Raises an exception in case of invalid name."""
		# Check string length
		if len(name) < 1:
			raise AwlParserError("The variable name is too short")
		if len(name) > 24:
			raise AwlParserError("The variable name '%s' is "
				"too long (max 24 characters)." %\
				name)
		# Only alphanumeric characters and underscores.
		for c in name:
			if c not in cls.VALID_CHARS:
				raise AwlParserError("The variable name '%s' "
					"contains invalid characters. "
					"Only alphanumeric characters (a-z, A-Z, 0-9) "
					"and underscores (_) are allowed." %\
					name)
		# First character must not be a number.
		if name[0] in cls.NUMBERS:
			raise AwlParserError("The first character of the "
				"variable name '%s' must not be a number." %\
				name)
		# Last character must not be an underscore.
		if name[-1] == '_':
			raise AwlParserError("The last character of the "
				"variable name '%s' must not be an underscore." %\
				name)
		# Consecutive underscores are not allowed.
		if '__' in name:
			raise AwlParserError("Consecutive underscores in "
				"the variable name '%s' are not allowed." %\
				name)
		return name

	def __init__(self, name, indices=None, doValidateName=True):
		self.name = name		# Name string of the variable
		self.indices = indices or None	# Possible array indices (or None)
		if doValidateName:
			self.validateName(self.name)

	# Duplicate this ident
	def dup(self, withIndices=True):
		if withIndices and self.indices:
			indices = self.indices[:]
		else:
			indices = None
		return AwlDataIdent(self.name, indices)

	# Increment the array indices of this ident by one.
	# 'dimensions' is the array dimensions.
	def advanceToNextArrayElement(self, dimensions):
		assert(self.indices)
		assert(len(self.indices) == len(dimensions))
		self.indices[-1] += 1
		for i in range(len(self.indices) - 1, -1, -1):
			if self.indices[i] > dimensions[i][1]:
				if i <= 0:
					self.indices = [dim[0] for dim in dimensions]
					break
				self.indices[i] = dimensions[i][0]
				self.indices[i - 1] += 1
			else:
				break

	# == operator
	def __eq__(self, other):
		if other is None:
			return False
		if self.name != other.name:
			return False
		if self.indices and other.indices:
			if self.indices != other.indices:
				return False
		return True

	# != operator
	def __ne__(self, other):
		return not self.__eq__(other)

	# Get the sanitized identifier string.
	def getString(self):
		if self.indices:
			return "%s[%s]" % (self.name,
					   ",".join(str(i) for i in self.indices))
		return self.name

	def __repr__(self):
		return self.getString()

	def __str__(self):
		return self.__repr__()

class AwlDataIdentChain(object):
	"""Data field identifier chain.
	Fully identifies a data field in an identifier
	chain that is nested STRUCTs, UDTs or such."""

	__slots__ = (
		"idents",
	)

	# Create an AwlDataIdentChain from a string.
	@classmethod
	def parseString(cls, string):
		tokens = []
		curTok = []
		for c in string:
			if c in ('.', ',', '[', ']'):
				if curTok:
					curTok = ''.join(curTok).strip()
					if curTok:
						tokens.append(curTok)
					curTok = []
				tokens.append(c)
			curTok.append(c)
		if curTok:
			curTok = ''.join(curTok).strip()
			if curTok:
				tokens.append(curTok)
		return cls.parseTokens(tokens)

	# Create an AwlDataIdentChain from a list of token strings.
	@classmethod
	def parseTokens(cls, tokenList):
		identChain = cls()
		while tokenList:
			dotIdx = listIndex(tokenList, '.')
			if dotIdx < 0:
				dotIdx = len(tokenList)
			tokens = tokenList[:dotIdx]
			tokenList = tokenList[dotIdx+1:]

			# Parse possible array indices.
			openIdx = listIndex(tokens, '[')
			closeIdx = listIndex(tokens, ']')
			indices = []
			if openIdx >= 0:
				if closeIdx < openIdx + 2:
					raise AwlParserError("Invalid array brackets.")
				indexTokens = tokens[openIdx+1:closeIdx]
				while indexTokens:
					try:
						indices.append(int(indexTokens[0]))
					except ValueError as e:
						raise AwlParserError(
							"Invalid array index value")
					indexTokens = indexTokens[1:]
					if indexTokens:
						if indexTokens[0] != ',':
							raise AwlParserError("Missing "
								"comma in array index.")
						indexTokens = indexTokens[1:]
				# Strip indices.
				tokens = tokens[:openIdx]
			else:
				if closeIdx >= 0:
					raise AwlParserError("Found closing "
						"brackets, but no opening "
						"brackets.")

			if len(indices) > 6:
				raise AwlParserError(
					"More than 6 array indices specified")
			if len(tokens) != 1:
				raise AwlParserError(
					"Invalid variable name in assignment")
			identChain.idents.append(AwlDataIdent(tokens[0], indices))
		return identChain

	# Expand an identifier token list.
	# Returns a tuple (tokenList, countOfConsumedTokens).
	@classmethod
	def expandTokens(cls, tokens):
		# Find the end of this identifier.
		# Identifiers are delimited by ',' or '('
		inBrackets, endIdx = False, 0
		while endIdx < len(tokens) and\
		      ((tokens[endIdx] != ',' and tokens[endIdx] != '(') or\
		       inBrackets):
			if tokens[endIdx] == '[':
				inBrackets = True
			elif tokens[endIdx] == ']':
				inBrackets = False
			endIdx += 1

		# Split all ops by '.'
		tokens = listExpand(tokens[:endIdx],
			lambda e: strPartitionFull(e, '.', keepEmpty=False))

		return tokens, endIdx

	def __init__(self, idents=None):
		"""idents -> A list of AwlDataIdent instances."""

		self.idents = toList(idents or [])

	# Duplicate this identifier chain (deep copy).
	def dup(self, withIndices=True):
		return AwlDataIdentChain(
			[ ident.dup(withIndices) for ident in self.idents ]
		)

	# == operator
	def __eq__(self, other):
		if other is None:
			return False
		return self.idents == other.idents

	# != operator
	def __ne__(self, other):
		return not self.__eq__(other)

	def __len__(self):
		return len(self.idents)

	def __getitem__(self, key):
		return self.idents[key]

	def __setitem__(self, key, value):
		self.idents[key] = value

	def __delitem__(self, key):
		del self.idents[key]

	def __iter__(self):
		return self.idents.__iter__()

	def __reversed__(self):
		return self.idents.__reversed__()

	# Get the sanitized identifier chain string.
	def getString(self):
		return ".".join(ident.getString() for ident in self.idents)

	def __repr__(self):
		return self.getString()

	def __str__(self):
		return self.__repr__()
