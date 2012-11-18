# -*- coding: utf-8 -*-
#
# AWL simulator - status word
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

from util import *


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

	nr2name = { }
	for name, type in name2nr.items():
		nr2name[type] = name

	NR_BITS = 9

	@classmethod
	def getBitnrByName(cls, name):
		try:
			return cls.name2nr[name]
		except KeyError as e:
			raise AwlSimError("Invalid status word bit "
				"name: " + str(name))

	def __init__(self):
		self.reset()

	def getByBitNumber(self, bitNumber):
		try:
			return (self.NER, self.VKE, self.STA, self.OR,
				self.OS, self.OV, self.A0, self.A1,
				self.BIE)[bitNumber]
		except IndexError as e:
			raise AwlSimError("Status word bit fetch '%d' "
				"out of range" % bitNumber)

	def getWord(self):
		pass#TODO

	def reset(self):
		self.NER = 0	# /ER	=> Erstabfrage
		self.VKE = 0	# VKE	=> Verknuepfungsergebnis
		self.STA = 0	# STA	=> Statusbit
		self.OR = 0	# OR	=> Oderbit
		self.OS = 0	# OS	=> Ueberlauf speichernd
		self.OV = 0	# OV	=> Ueberlauf
		self.A0 = 0	# A0	=> Ergebnisanzeige 0
		self.A1 = 0	# A1	=> Ergebnisanzeige 1
		self.BIE = 0	# BIE	=> Binaerergebnis

	def setForFloatingPoint(self, dword):
		noSign, s = dword & 0x7FFFFFFF, self
		if noSign == 0: # zero
			s.A1, s.A0, s.OV = 0, 0, 0
		elif noSign < 0x00800000: # denorm
			s.A1, s.A0, s.OV, s.OS = 0, 0, 1, 1
		elif noSign >= 0x7F800000:
			if noSign == 0x7F800000: # inf
				if dword & 0x80000000:
					s.A1, s.A0, s.OV, s.OS = 0, 1, 1, 1
				else:
					s.A1, s.A0, s.OV, s.OS = 1, 0, 1, 1
			else: # nan
				s.A1, s.A0, s.OV, s.OS = 1, 1, 1, 1
		elif dword & 0x80000000:
			s.A1, s.A0, s.OV = 0, 1, 0
		else:
			s.A1, s.A0, s.OV = 1, 0, 0

	def __repr__(self):
		ret = []
		for i in range(self.NR_BITS - 1, -1, -1):
			ret.append("%s=%d" % (
				self.nr2name[i],
				self.getByBitNumber(i)
			))
		return ', '.join(ret)
