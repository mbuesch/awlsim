# -*- coding: utf-8 -*-
#
# AWL simulator - status word
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

from awlsim.core.util import *
from awlsim.core.datatypehelpers import *


class S7StatusWord(object):
	"STEP 7 status word"

	name2nr = {
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
	nr2name = pivotDict(name2nr)

	NR_BITS = 9

	@classmethod
	def getBitnrByName(cls, name):
		try:
			return cls.name2nr[name]
		except KeyError as e:
			raise AwlSimError("Invalid status word bit "
				"name: " + str(name))

	def __init__(self):
		(self.NER,	# /ER	=> Erstabfrage
		 self.VKE,	# VKE	=> Verknuepfungsergebnis
		 self.STA,	# STA	=> Statusbit
		 self.OR,	# OR	=> Oderbit
		 self.OS,	# OS	=> Ueberlauf speichernd
		 self.OV,	# OV	=> Ueberlauf
		 self.A0,	# A0	=> Ergebnisanzeige 0
		 self.A1,	# A1	=> Ergebnisanzeige 1
		 self.BIE,	# BIE	=> Binaerergebnis
		) = 0, 0, 0, 0, 0, 0, 0, 0, 0

	def getByBitNumber(self, bitNumber):
		try:
			return (self.NER, self.VKE, self.STA, self.OR,
				self.OS, self.OV, self.A0, self.A1,
				self.BIE)[bitNumber]
		except IndexError as e:
			raise AwlSimError("Status word bit fetch '%d' "
				"out of range" % bitNumber)

	def getWord(self):
		return self.NER | (self.VKE << 1) | (self.STA << 2) |\
		       (self.OR << 3) | (self.OS << 4) | (self.OV << 5) |\
		       (self.A0 << 6) | (self.A1 << 7) | (self.BIE << 8)

	def setWord(self, word):
		self.NER = 1 if (word & (1 << 0)) else 0
		self.VKE = 1 if (word & (1 << 1)) else 0
		self.STA = 1 if (word & (1 << 2)) else 0
		self.OR = 1 if (word & (1 << 3)) else 0
		self.OS = 1 if (word & (1 << 4)) else 0
		self.OV = 1 if (word & (1 << 5)) else 0
		self.A0 = 1 if (word & (1 << 6)) else 0
		self.A1 = 1 if (word & (1 << 7)) else 0
		self.BIE = 1 if (word & (1 << 8)) else 0

	def copy(self):
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
		dwordNoSign, s = dword & 0x7FFFFFFF, self
		if isDenormalPyFloat(pyFloat) or\
		   (dwordNoSign < 0x00800000 and dwordNoSign != 0):
			# denorm
			s.A1, s.A0, s.OV, s.OS = 0, 0, 1, 1
		elif dwordNoSign == 0:
			# zero
			s.A1, s.A0, s.OV = 0, 0, 0
		elif dwordNoSign >= 0x7F800000:
			if dwordNoSign == 0x7F800000:
				# inf
				if dword & 0x80000000:
					s.A1, s.A0, s.OV, s.OS = 0, 1, 1, 1
				else:
					s.A1, s.A0, s.OV, s.OS = 1, 0, 1, 1
			else:
				# nan
				s.A1, s.A0, s.OV, s.OS = 1, 1, 1, 1
		elif dword & 0x80000000:
			# norm neg
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			# norm pos
			s.A1, s.A0, s.OV = 1, 0, 0

	def __repr__(self):
		ret = []
		for i in range(self.NR_BITS - 1, -1, -1):
			ret.append("%s:%d" % (
				self.nr2name[i],
				self.getByBitNumber(i)
			))
		return '  '.join(ret)
