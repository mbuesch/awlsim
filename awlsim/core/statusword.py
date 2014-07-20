# -*- coding: utf-8 -*-
#
# AWL simulator - status word
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

from awlsim.core.dynattrs import *
from awlsim.core.util import *
from awlsim.core.datatypehelpers import *
from awlsim.core.cpuspecs import *


class S7StatusWord(DynAttrs):
	"""STEP 7 status word
	The instance of this class holds the following nine
	attributes. One for each STW bit:
	NER, VKE, STA, OR, OS, OV, A0, A1, BIE
	"""

	name2nr_german = {
		"/ER"	: 0,
		"VKE"	: 1,
		"STA"	: 2,
		"OR"	: 3,
		"OS"	: 4,
		"OV"	: 5,
		"A0"	: 6,
		"A1"	: 7,
		"BIE"	: 8,
	}
	nr2name_german = pivotDict(name2nr_german)

	__english2german = {
		"/FC"	: "/ER",
		"RLO"	: "VKE",
		"STA"	: "STA",
		"OR"	: "OR",
		"OS"	: "OS",
		"OV"	: "OV",
		"CC1"	: "A1",
		"CC0"	: "A0",
		"BR"	: "BIE",
	}
	__german2english = pivotDict(__english2german)

	NR_BITS = 9

	# Dynamic attributes
	dynAttrs = {
		"NER"	: 0,
		"VKE"	: 0,
		"STA"	: 0,
		"OR"	: 0,
		"OS"	: 0,
		"OV"	: 0,
		"A0"	: 0,
		"A1"	: 0,
		"BIE"	: 0,
	}

	@classmethod
	def getBitnrByName(cls, name, mnemonics):
		assert(mnemonics != S7CPUSpecs.MNEMONICS_AUTO)
		try:
			if mnemonics == S7CPUSpecs.MNEMONICS_EN:
				name = cls.__english2german[name]
			return cls.name2nr_german[name]
		except KeyError as e:
			raise AwlSimError("Invalid status word bit "
				"name: " + str(name))

	def __getNER(self):
		return self.NER

	def __getVKE(self):
		return self.VKE

	def __getSTA(self):
		return self.STA

	def __getOR(self):
		return self.OR

	def __getOS(self):
		return self.OS

	def __getOV(self):
		return self.OV

	def __getA0(self):
		return self.A0

	def __getA1(self):
		return self.A1

	def __getBIE(self):
		return self.BIE

	__bitnr2getter = (
		__getNER,
		__getVKE,
		__getSTA,
		__getOR,
		__getOS,
		__getOV,
		__getA0,
		__getA1,
		__getBIE,
	)

	def getByBitNumber(self, bitNumber):
		try:
			return self.__bitnr2getter[bitNumber](self)
		except IndexError as e:
			raise AwlSimError("Status word bit fetch '%d' "
				"out of range" % bitNumber)

	def getWord(self):
		return self.NER | (self.VKE << 1) | (self.STA << 2) |\
		       (self.OR << 3) | (self.OS << 4) | (self.OV << 5) |\
		       (self.A0 << 6) | (self.A1 << 7) | (self.BIE << 8)

	def setWord(self, word):
		self.NER = word & 1
		self.VKE = (word >> 1) & 1
		self.STA = (word >> 2) & 1
		self.OR = (word >> 3) & 1
		self.OS = (word >> 4) & 1
		self.OV = (word >> 5) & 1
		self.A0 = (word >> 6) & 1
		self.A1 = (word >> 7) & 1
		self.BIE = (word >> 8) & 1

	def dup(self):
		new = S7StatusWord()
		new.NER = self.NER
		new.VKE = self.VKE
		new.STA = self.STA
		new.OR = self.OR
		new.OS = self.OS
		new.OV = self.OV
		new.A0 = self.A0
		new.A1 = self.A1
		new.BIE = self.BIE
		return new

	def setForFloatingPoint(self, pyFloat):
		dword = pyFloatToDWord(pyFloat)
		dwordNoSign = dword & 0x7FFFFFFF
		if isDenormalPyFloat(pyFloat) or\
		   (dwordNoSign < 0x00800000 and dwordNoSign != 0):
			# denorm
			self.A1, self.A0, self.OV, self.OS = 0, 0, 1, 1
		elif dwordNoSign == 0:
			# zero
			self.A1, self.A0, self.OV = 0, 0, 0
		elif dwordNoSign >= 0x7F800000:
			if dwordNoSign == 0x7F800000:
				# inf
				if dword & 0x80000000:
					self.A1, self.A0, self.OV, self.OS = 0, 1, 1, 1
				else:
					self.A1, self.A0, self.OV, self.OS = 1, 0, 1, 1
			else:
				# nan
				self.A1, self.A0, self.OV, self.OS = 1, 1, 1, 1
		elif dword & 0x80000000:
			# norm neg
			self.A1, self.A0, self.OV = 0, 1, 0
		else:
			# norm pos
			self.A1, self.A0, self.OV = 1, 0, 0

	def getString(self, mnemonics):
		assert(mnemonics != S7CPUSpecs.MNEMONICS_AUTO)
		ret = []
		for i in range(self.NR_BITS - 1, -1, -1):
			name = self.nr2name_german[i]
			if mnemonics == S7CPUSpecs.MNEMONICS_EN:
				name = self.__german2english[name]
			ret.append("%s:%d" % (name, self.getByBitNumber(i)))
		return '  '.join(ret)

	def __repr__(self):
		return self.getString(S7CPUSpecs.MNEMONICS_DE)
