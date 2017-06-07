# -*- coding: utf-8 -*-
#
# AWL simulator - timers
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
from awlsim.common.compat import *

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *

from awlsim.core.util import *


def _seconds_to_s5t_tb10ms(seconds):
	centisec = int(round(seconds * 100))
	s5t = Timer.TB_10MS_S
	s5t |= centisec % 10
	s5t |= ((centisec // 10) % 10) << 4
	return s5t | ((centisec // 100) % 10) << 8

def _seconds_to_s5t_tb100ms(seconds):
	decisec = int(round(seconds * 10))
	s5t = Timer.TB_100MS_S
	s5t |= decisec % 10
	s5t |= ((decisec // 10) % 10) << 4
	return s5t | ((decisec // 100) % 10) << 8

def _seconds_to_s5t_tb1s(seconds):
	seconds = int(seconds)
	s5t = Timer.TB_1S_S
	s5t |= seconds % 10
	s5t |= ((seconds // 10) % 10) << 4
	return s5t | ((seconds // 100) % 10) << 8

def _seconds_to_s5t_tb10s(seconds):
	decasecs = int(round(seconds)) // 10
	s5t = Timer.TB_10S_S
	s5t |= decasecs % 10
	s5t |= ((decasecs // 10) % 10) << 4
	return s5t | ((decasecs // 100) % 10) << 8

class Timer(object): #+cdef
	"""Classic AWL timer."""

	# Timebases
	TB_10MS		= 0x0
	TB_100MS	= 0x1
	TB_1S		= 0x2
	TB_10S		= 0x3

	TB_SHIFT	= 12
	TB_MASK		= 0x3
	TB_MASK_S	= TB_MASK << TB_SHIFT

	# Shifted timebases
	TB_10MS_S	= TB_10MS << TB_SHIFT
	TB_100MS_S	= TB_100MS << TB_SHIFT
	TB_1S_S		= TB_1S << TB_SHIFT
	TB_10S_S	= TB_10S << TB_SHIFT

	__slots__ = (
		"cpu",
		"index",
		"prevVKE",
		"timebase",
		"deadlineCallback",
		"deadline",
		"remaining",
		"status",
		"running",
	)

	def __init__(self, cpu, index):
		self.cpu = cpu
		self.index = index
		self.prevVKE = 0
		self.timebase = self.TB_10MS
		self.deadlineCallback = None
		self.deadline = 0.0
		self.remaining = 0.0
		self.status = 0
		self.running = False

	__seconds_to_s5t_table = (
		_seconds_to_s5t_tb10ms,		# TB_10MS
		_seconds_to_s5t_tb100ms,	# TB_100MS
		_seconds_to_s5t_tb1s,		# TB_1S
		_seconds_to_s5t_tb10s,		# TB_10S
	)

	# Convert floating point seconds to S5T encoded value
	@classmethod
	def seconds_to_s5t(cls, seconds):
		if seconds < 0.0:
			raise AwlSimError("Cannot convert %f seconds "
					  "to S5T" % seconds)
		if seconds <= 9.99:
			timebase = cls.TB_10MS
		elif seconds <= 99.9:
			timebase = cls.TB_100MS
		elif seconds <= 999.0:
			timebase = cls.TB_1S
		elif seconds <= 9990.0:
			timebase = cls.TB_10S
		else:
			raise AwlSimError("Cannot convert %f seconds "
					  "to S5T" % seconds)
		return cls.__seconds_to_s5t_table[timebase](seconds)

	__s5t_base2sec = (
		0.01,	# TB_10MS
		0.1,	# TB_100MS
		1.0,	# TB_1S
		10.0	# TB_10S
	)

	# Convert S5T encoded value to floating point seconds
	@classmethod
	def s5t_to_seconds(cls, s5t):
		a, b, c = (s5t & 0xF), ((s5t >> 4) & 0xF),\
			  ((s5t >> 8) & 0xF)
		if (s5t & ~cls.TB_MASK_S) > 0x999 or a > 9 or b > 9 or c > 9:
			raise AwlSimError("Invalid S5T value: %04X" % s5t)
		return cls.__s5t_base2sec[
			(s5t >> cls.TB_SHIFT) & cls.TB_MASK] * (\
			a + (b * 10) + (c * 100))

	# Get the timer status (Q)
	def get(self):
		self.__checkDeadline()
		return self.status

	# Reset (R) timer
	def reset(self):
		self.running, self.status, self.remaining =\
			False, 0, 0.0

	# Set the timeval of a running counter.
	def setTimevalS5T(self, s5t):
		if self.running:
			self.__start(s5t)

	# Return the timer value in binary.
	# The interpretation of the result depends on the active timebase.
	def getTimevalBin(self):
		return int(round(
			self.__getRemainingSeconds() / \
			self.__s5t_base2sec[self.timebase]
		))

	# Return the timer value in S5T BCD format.
	# The interpretation of the result depends on the active timebase.
	def getTimevalS5T(self):
		return self.__seconds_to_s5t_table[self.timebase](
				self.__getRemainingSeconds())

	# Return the timer value in S5T BCD format with timebase.
	def getTimevalS5TwithBase(self):
		return self.__seconds_to_s5t_table[self.timebase](
				self.__getRemainingSeconds()) |\
			(self.timebase << self.TB_SHIFT)

	# Get the remaining time, in seconds
	def __getRemainingSeconds(self):
		self.__checkDeadline()
		return self.remaining

	# Update the remaining time value
	def __updateRemaining(self):
		self.remaining = max(0.0, self.deadline - self.cpu.now)

	def run_SI(self, s5t):
		self.deadlineCallback = self.__cb_clearStatus
		s = self.cpu.statusWord
		if s.VKE:
			if not self.prevVKE: # Pos edge
				self.status = 1
				self.__start(s5t)
		else:
			self.__checkDeadline()
			self.running, self.status = False, 0
		self.prevVKE, s.OR, s.NER = s.VKE, 0, 0

	def run_SV(self, s5t):
		self.deadlineCallback = self.__cb_clearStatus
		s = self.cpu.statusWord
		if s.VKE & ~self.prevVKE: # Pos edge
			self.status = 1
			self.__start(s5t)
		self.prevVKE, s.OR, s.NER = s.VKE, 0, 0

	def run_SE(self, s5t):
		self.deadlineCallback = self.__cb_setStatus
		s = self.cpu.statusWord
		if s.VKE:
			if not self.prevVKE: # Pos edge
				self.__start(s5t)
		else:
			self.__checkDeadline()
			self.running, self.status = False, 0
		self.prevVKE, s.OR, s.NER = s.VKE, 0, 0

	def run_SS(self, s5t):
		self.deadlineCallback = self.__cb_setStatus
		s = self.cpu.statusWord
		if s.VKE & ~self.prevVKE: # Pos edge
			self.__start(s5t)
		self.prevVKE, s.OR, s.NER = s.VKE, 0, 0

	def run_SA(self, s5t):
		self.deadlineCallback = self.__cb_clearStatus
		s = self.cpu.statusWord
		if s.VKE & ~self.prevVKE: # Pos edge
			self.__checkDeadline()
			self.status, self.running = 1, False
		if ~s.VKE & self.prevVKE: # Neg edge
			self.status = 1
			self.__start(s5t)
		self.prevVKE, s.OR, s.NER = s.VKE, 0, 0

	def __start(self, s5t):
		self.timebase = (s5t >> self.TB_SHIFT) & self.TB_MASK
		self.deadline = self.cpu.now + self.s5t_to_seconds(s5t)
		self.__updateRemaining()
		self.running = True

	def __checkDeadline(self):
		if self.running:
			self.__updateRemaining()
			if self.remaining <= 0.0:
				self.deadlineCallback()

	# Deadline callback - set status
	def __cb_setStatus(self):
		self.running, self.status = False, 1

	# Deadline callback - clear status
	def __cb_clearStatus(self):
		self.running, self.status = False, 0

def Timer_seconds_to_s5t(seconds): #+cdef
	return Timer.seconds_to_s5t(seconds)

def Timer_s5t_to_seconds(s5t): #+cdef
	return Timer.s5t_to_seconds(s5t)
