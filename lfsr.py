# -*- coding: utf-8 -*-
#
# Linear feedback shift register
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import random


class LFSR16(object):
	"16-bit Galois linear feedback shift register"

	DEFAULT_INIT	= 0xACE1

	def __init__(self, init=DEFAULT_INIT):
		self.__lfsr = init & 0xFFFF
		assert(self.__lfsr != 0)

	def getBits(self, count):
		ret, lfsr = 0, self.__lfsr
		while count:
			lfsr = (lfsr >> 1) ^ (-(lfsr & 1) & 0xB400)
			ret, count = (ret << 1) | (lfsr & 1), count - 1
		self.__lfsr = lfsr
		return ret

class Simple_PRNG(LFSR16):
	def __init__(self):
		LFSR16.__init__(self, random.randint(1, 0xFFFF))
