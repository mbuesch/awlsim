# -*- coding: utf-8 -*-
#
# AWL simulator - timers
#
# Copyright 2012-2018 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.exceptions import *
from awlsim.common.util import *

from awlsim.core.statusword import * #+cimport

# Get the C round() function. This is different from the Python3 round().
#from libc.math cimport round #@cy


class TimerConstsClass(object): #+cdef
	def __init__(self):
		# Timebases
		self.TB_10MS	= 0x0
		self.TB_100MS	= 0x1
		self.TB_1S	= 0x2
		self.TB_10S	= 0x3

		self.TB_SHIFT	= 12
		self.TB_MASK	= 0x3
		self.TB_MASK_S	= self.TB_MASK << self.TB_SHIFT

		# Shifted timebases
		self.TB_10MS_S	= self.TB_10MS << self.TB_SHIFT
		self.TB_100MS_S	= self.TB_100MS << self.TB_SHIFT
		self.TB_1S_S	= self.TB_1S << self.TB_SHIFT
		self.TB_10S_S	= self.TB_10S << self.TB_SHIFT

TimerConsts = TimerConstsClass() #+cdef-TimerConstsClass

def _seconds_to_s5t_tb10ms(seconds): #@nocy
#cdef uint16_t _seconds_to_s5t_tb10ms(double seconds): #@cy
#@cy	cdef uint32_t centisec
#@cy	cdef uint16_t s5t

	centisec = int(round(seconds * 100.0))
	s5t = TimerConsts.TB_10MS_S
	s5t |= centisec % 10
	s5t |= ((centisec // 10) % 10) << 4
	return s5t | ((centisec // 100) % 10) << 8

def _seconds_to_s5t_tb100ms(seconds): #@nocy
#cdef uint16_t _seconds_to_s5t_tb100ms(double seconds): #@cy
#@cy	cdef uint32_t decisec
#@cy	cdef uint16_t s5t

	decisec = int(round(seconds * 10.0))
	s5t = TimerConsts.TB_100MS_S
	s5t |= decisec % 10
	s5t |= ((decisec // 10) % 10) << 4
	return s5t | ((decisec // 100) % 10) << 8

def _seconds_to_s5t_tb1s(seconds): #@nocy
#cdef uint16_t _seconds_to_s5t_tb1s(double seconds): #@cy
#@cy	cdef uint32_t secondsInt
#@cy	cdef uint16_t s5t

	secondsInt = int(seconds)
	s5t = TimerConsts.TB_1S_S
	s5t |= secondsInt % 10
	s5t |= ((secondsInt // 10) % 10) << 4
	return s5t | ((secondsInt // 100) % 10) << 8

def _seconds_to_s5t_tb10s(seconds): #@nocy
#cdef uint16_t _seconds_to_s5t_tb10s(double seconds): #@cy
#@cy	cdef uint32_t decasecs
#@cy	cdef uint16_t s5t

	decasecs = int(round(seconds)) // 10 #@nocy
#@cy	decasecs = <uint32_t>int(round(seconds)) // 10u
	s5t = TimerConsts.TB_10S_S
	s5t |= decasecs % 10
	s5t |= ((decasecs // 10) % 10) << 4
	return s5t | ((decasecs // 100) % 10) << 8

# Convert floating point seconds to S5T encoded value
def Timer_seconds_to_s5t(seconds): #@nocy
#cdef uint32_t Timer_seconds_to_s5t(double seconds) except? 0xFFFFFFFF: #@cy

	if seconds < 0.0:
		raise AwlSimError("Cannot convert %f seconds "
				  "to S5T" % seconds)
	if seconds <= 9.99:
		return _seconds_to_s5t_tb10ms(seconds)
	elif seconds <= 99.9:
		return _seconds_to_s5t_tb100ms(seconds)
	elif seconds <= 999.0:
		return _seconds_to_s5t_tb1s(seconds)
	elif seconds <= 9990.0:
		return _seconds_to_s5t_tb10s(seconds)
	else:
		raise AwlSimError("Cannot convert %f seconds "
				  "to S5T" % seconds)

# Convert S5T encoded value to floating point seconds
def Timer_s5t_to_seconds(s5t): #@nocy
#cdef double Timer_s5t_to_seconds(uint16_t s5t) except? -1.0: #@cy
#@cy	cdef uint16_t a
#@cy	cdef uint16_t b
#@cy	cdef uint16_t c
#@cy	cdef uint8_t tb

	a, b, c = (s5t & 0xF), ((s5t >> 4) & 0xF),\
		  ((s5t >> 8) & 0xF)
	if (s5t & ~TimerConsts.TB_MASK_S) > 0x999 or a > 9 or b > 9 or c > 9:
		raise AwlSimError("Invalid S5T value: %04X" % s5t)
	tb = (s5t >> TimerConsts.TB_SHIFT) & TimerConsts.TB_MASK
	if tb == TimerConsts.TB_10MS:
		return (a + (b * 10) + (c * 100)) * 0.01
	elif tb == TimerConsts.TB_100MS:
		return (a + (b * 10) + (c * 100)) * 0.1
	elif tb == TimerConsts.TB_1S:
		return (a + (b * 10) + (c * 100)) * 1.0
	elif tb == TimerConsts.TB_10S:
		return (a + (b * 10) + (c * 100)) * 10.0
	raise AwlSimError("Timer_s5t_to_seconds: Invalid time base")

class Timer(object): #+cdef
	"""Classic AWL timer.
	"""

	__slots__ = (
		"cpu",
		"index",
		"prevVKE_S",
		"prevVKE_FR",
		"timebase",
		"deadlineActionSetStatus",
		"deadline",
		"remaining",
		"status",
		"running",
	)

	def __init__(self, cpu, index):
		self.cpu = cpu
		self.index = index
		self.prevVKE_S = 0
		self.prevVKE_FR = 0
		self.timebase = TimerConsts.TB_10MS
		self.deadlineActionSetStatus = False
		self.deadline = 0.0
		self.remaining = 0.0
		self.status = 0
		self.running = False

	# Get the timer status (Q)
	def get(self): #@nocy
#@cy	cdef _Bool get(self):
		self.__checkDeadline()
		return self.status

	# Reset (R) timer
	def reset(self): #@nocy
#@cy	cdef void reset(self):
		self.running, self.status, self.remaining =\
			False, 0, 0.0

	# Set the timeval of a running counter.
	def setTimevalS5T(self, s5t): #@nocy
#@cy	cdef setTimevalS5T(self, uint16_t s5t):
		if self.running:
			self.__start(s5t)

	# Return the timer value in binary.
	# The interpretation of the result depends on the active timebase.
	def getTimevalBin(self): #@nocy
#@cy	cdef uint32_t getTimevalBin(self) except? 0xFFFFFFFF:
#@cy		cdef uint16_t timebase

		timebase = self.timebase
		if timebase == TimerConsts.TB_10MS:
			return int(round(self.__getRemainingSeconds() / 0.01))
		elif timebase == TimerConsts.TB_100MS:
			return int(round(self.__getRemainingSeconds() / 0.1))
		elif timebase == TimerConsts.TB_1S:
			return int(round(self.__getRemainingSeconds()))
		elif timebase == TimerConsts.TB_10S:
			return int(round(self.__getRemainingSeconds() / 10.0))
		raise AwlSimError("getTimevalBin: Invalid time base")

	# Return the timer value in S5T BCD format.
	# The interpretation of the result depends on the active timebase.
	def getTimevalS5T(self): #@nocy
#@cy	cdef uint16_t getTimevalS5T(self) except? 0xFFFF:
#@cy		cdef uint16_t timebase

		timebase = self.timebase
		if timebase == TimerConsts.TB_10MS:
			return _seconds_to_s5t_tb10ms(self.__getRemainingSeconds())
		elif timebase == TimerConsts.TB_100MS:
			return _seconds_to_s5t_tb100ms(self.__getRemainingSeconds())
		elif timebase == TimerConsts.TB_1S:
			return _seconds_to_s5t_tb1s(self.__getRemainingSeconds())
		elif timebase == TimerConsts.TB_10S:
			return _seconds_to_s5t_tb10s(self.__getRemainingSeconds())
		raise AwlSimError("getTimevalS5T: Invalid time base")

	# Return the timer value in S5T BCD format with timebase.
	def getTimevalS5TwithBase(self): #@nocy
#@cy	cdef uint16_t getTimevalS5TwithBase(self) except? 0xFFFF:
		return self.getTimevalS5T() |\
			(self.timebase << TimerConsts.TB_SHIFT)

	# Get the remaining time, in seconds
	def __getRemainingSeconds(self): #@nocy
#@cy	cdef double __getRemainingSeconds(self):
		self.__checkDeadline()
		return self.remaining

	# Update the remaining time value
	def __updateRemaining(self): #@nocy
#@cy	cdef void __updateRemaining(self):
		self.remaining = max(0.0, self.deadline - self.cpu.now)

	def run_FR(self): #+cdef
#@cy		cdef S7StatusWord s

		s = self.cpu.statusWord
		if (self.prevVKE_FR ^ 1) & s.VKE:
			self.prevVKE_S = 0
		self.prevVKE_FR, s.OR, s.NER = s.VKE, 0, 0

	def run_SI(self, s5t): #@nocy
#@cy	cdef run_SI(self, uint16_t s5t):
#@cy		cdef S7StatusWord s

		self.deadlineActionSetStatus = False
		s = self.cpu.statusWord
		if s.VKE:
			if not self.prevVKE_S: # Pos edge
				self.status = 1
				self.__start(s5t)
		else:
			self.__checkDeadline()
			self.running, self.status = False, 0
		self.prevVKE_S, s.OR, s.NER = s.VKE, 0, 0

	def run_SV(self, s5t): #@nocy
#@cy	cdef run_SV(self, uint16_t s5t):
#@cy		cdef S7StatusWord s

		self.deadlineActionSetStatus = False
		s = self.cpu.statusWord
		if s.VKE & (self.prevVKE_S ^ 1): # Pos edge
			self.status = 1
			self.__start(s5t)
		self.prevVKE_S, s.OR, s.NER = s.VKE, 0, 0

	def run_SE(self, s5t): #@nocy
#@cy	cdef run_SE(self, uint16_t s5t):
#@cy		cdef S7StatusWord s

		self.deadlineActionSetStatus = True
		s = self.cpu.statusWord
		if s.VKE:
			if not self.prevVKE_S: # Pos edge
				self.__start(s5t)
		else:
			self.__checkDeadline()
			self.running, self.status = False, 0
		self.prevVKE_S, s.OR, s.NER = s.VKE, 0, 0

	def run_SS(self, s5t): #@nocy
#@cy	cdef run_SS(self, uint16_t s5t):
#@cy		cdef S7StatusWord s

		self.deadlineActionSetStatus = True
		s = self.cpu.statusWord
		if s.VKE & (self.prevVKE_S ^ 1): # Pos edge
			self.__start(s5t)
		self.prevVKE_S, s.OR, s.NER = s.VKE, 0, 0

	def run_SA(self, s5t): #@nocy
#@cy	cdef run_SA(self, uint16_t s5t):
#@cy		cdef S7StatusWord s

		self.deadlineActionSetStatus = False
		s = self.cpu.statusWord
		if s.VKE & (self.prevVKE_S ^ 1): # Pos edge
			self.__checkDeadline()
			self.status, self.running = 1, False
		if (s.VKE ^ 1) & self.prevVKE_S: # Neg edge
			self.status = 1
			self.__start(s5t)
		self.prevVKE_S, s.OR, s.NER = s.VKE, 0, 0

	def __start(self, s5t): #@nocy
#@cy	cdef __start(self, uint16_t s5t):
		self.timebase = (s5t >> TimerConsts.TB_SHIFT) & TimerConsts.TB_MASK
		self.deadline = self.cpu.now + Timer_s5t_to_seconds(s5t)
		self.__updateRemaining()
		self.running = True

	def __checkDeadline(self): #@nocy
#@cy	cdef void __checkDeadline(self):
		if self.running:
			self.__updateRemaining()
			if self.remaining <= 0.0:
				if self.deadlineActionSetStatus:
					self.running, self.status = False, 1
				else:
					self.running, self.status = False, 0
