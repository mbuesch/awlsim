# -*- coding: utf-8 -*-
#
# LinuxCNC fake Python HAL module for unit testing
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


HAL_BIT		= 1
HAL_FLOAT	= 2
HAL_S32		= 3
HAL_U32		= 4

HAL_IN		= 16
HAL_OUT		= 32
HAL_IO		= HAL_IN | HAL_OUT

HAL_RO		= 64
HAL_RW		= 192


class _Pin(object):
	def __init__(self, halName, halType, halDir):
		assert(halType in (HAL_BIT, HAL_FLOAT, HAL_S32, HAL_U32))
		assert(halDir in (HAL_IN, HAL_OUT, HAL_IO))
		self.halName = halName
		self.halType = halType
		self.halDir = halDir
		self.signals = []
		if self.halType == HAL_FLOAT:
			self.setHalData(0.0)
		else:
			self.setHalData(0)

	def setHalData(self, v):
		if self.halType == HAL_BIT:
			assert(v in (0, 1))
		elif self.halType == HAL_FLOAT:
			assert(isinstance(v, float))
		elif self.halType == HAL_S32:
			assert(v >= -2147483648 and v <= 2147483647) #@nocy
#@cy			assert(v >= -2147483648LL and v <= 2147483647LL)
		elif self.halType == HAL_U32:
			assert(v >= 0 and v <= 2147483647)
		else:
			assert(0)
		self.halData = v
		if self.halDir in (HAL_OUT, HAL_IO):
			for signal in self.signals:
				signal.setHalData(v)

	def _connectSignal(self, signal):
		if self.halDir == HAL_IN:
			assert(not self.signals)
		self.signals.append(signal)

class _Param(_Pin):
	def __init__(self, halName, halType, halDir):
		assert(halType in (HAL_BIT, HAL_FLOAT, HAL_S32, HAL_U32))
		assert(halDir in (HAL_RO, HAL_RW))
		self.halName = halName
		self.halType = halType
		self.halDir = halDir
		if self.halType == HAL_FLOAT:
			self.setHalData(0.0)
		else:
			self.setHalData(0)

class _Signal(object):
	def __init__(self, halName):
		self.halName = halName
		self.halType = None
		self.connectedPins = []

	def connectPin(self, pin):
		assert(pin.halDir in (HAL_IN, HAL_OUT, HAL_IO))
		assert(pin not in self.connectedPins)
		if self.halType is None:
			assert(not self.connectedPins)
			self.halType = pin.halType
		assert(self.halType == pin.halType)
		self.connectedPins.append(pin)
		pin._connectSignal(self)

	def setHalData(self, v):
		for pin in self.connectedPins:
			if pin.halDir in (HAL_IN, HAL_IO):
				pin.setHalData(v)

class component(object):
	def __init__(self, name):
		self.__pins = {}
		self.__params = {}
		self.__signals = {}
		self.__ready = False

	def newpin(self, p, t, d):
		assert(p not in self.__pins)
		assert(p not in self.__params)
		assert(not self.__ready)
		assert(not self.__signals)
		self.__pins[p] = _Pin(p, t, d)

	def newparam(self, p, t, d):
		assert(p not in self.__pins)
		assert(p not in self.__params)
		assert(not self.__ready)
		assert(not self.__signals)
		self.__params[p] = _Param(p, t, d)

	def __sanitizePinName(self, pinName):
		assert(pinName.startswith("awlsim."))
		pinName = pinName[7:]
		assert(pinName)
		return pinName

	def __importHalFile(self, filename):
		assert(not self.__signals)
		lines = open(filename, "r").readlines()
		import re
		setp_re = re.compile(r'^setp\s+([\w\.\-]+)\s+([\w\.\-]+)$')
		net_re = re.compile(r'^net\s+([\w\.\-]+)\s+<?=?>?\s*([\w\.\-]+)(?:\s+<?=?>?\s*([\w\.\-]+))?$')
		for line in lines:
			line = line.strip()
			if not line:
				continue
			if line.startswith("#"):
				continue
			m = setp_re.match(line)
			if m: # setp statement
				halName, value = m.group(1), m.group(2)
				halName = self.__sanitizePinName(halName)
				value = int(value)
				try:
					self.__params[halName].setHalData(value)
				except KeyError:
					self.__pins[halName].setHalData(value)
				continue
			m = net_re.match(line)
			if m: # net statement
				if len(m.groups()) == 2:
					sigName, pin0Name, pin1Name =\
						m.group(1), m.group(2), None
				else:
					sigName, pin0Name, pin1Name =\
						m.group(1), m.group(2), m.group(3)
				if sigName in self.__signals:
					sig = self.__signals[sigName]
				else:
					sig = _Signal(sigName)
					self.__signals[sigName] = sig
				if pin0Name:
					sig.connectPin(self.__pins[self.__sanitizePinName(pin0Name)])
				if pin1Name:
					sig.connectPin(self.__pins[self.__sanitizePinName(pin1Name)])
			# Ignore other statements

	def ready(self):
		import os
		halFile = os.environ.get("FAKEHAL_HALFILE")
		if halFile:
			self.__importHalFile(halFile)
		self.__ready = True

	def __getitem__(self, k):
		assert(self.__ready)
		try:
			pin = self.__pins[k]
			assert(pin.halDir in (HAL_IN, HAL_IO))
			return pin.halData
		except KeyError:
			param = self.__params[k]
			assert(param.halDir in (HAL_RW, HAL_RO))
			return param.halData

	def __setitem__(self, k, v):
		assert(self.__ready)
		pin = self.__pins[k]
		assert(pin.halDir in (HAL_OUT, HAL_IO))
		pin.setHalData(v)
