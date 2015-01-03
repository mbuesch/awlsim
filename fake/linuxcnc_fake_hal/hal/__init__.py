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
			assert(v >= -2147483648 and v <= 2147483647)
		elif self.halType == HAL_U32:
			assert(v >= 0 and v <= 2147483647)
		else:
			assert(0)
		self.halData = v

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

class component(object):
	def __init__(self, name):
		self.__pins = {}
		self.__params = {}
		self.__ready = False

	def newpin(self, p, t, d):
		assert(p not in self.__pins)
		assert(p not in self.__params)
		assert(not self.__ready)
		self.__pins[p] = _Pin(p, t, d)

	def newparam(self, p, t, d):
		assert(p not in self.__pins)
		assert(p not in self.__params)
		assert(not self.__ready)
		self.__params[p] = _Param(p, t, d)

	def __importHalFile(self, filename):
		try:
			lines = open(filename, "r").readlines()
		except IOError:
			assert(0)
		import re
		setp_re = re.compile(r'^setp\s+([\w\.]+)\s+([\w\.]+)$')
		for line in lines:
			line = line.strip()
			if not line:
				continue
			if line.startswith("#"):
				continue
			m = setp_re.match(line)
			if m: # setp statement
				halName, value = m.group(1), m.group(2)
				assert(halName.startswith("awlsim."))
				halName = halName[7:]
				assert(halName)
				try:
					value = int(value)
				except ValueError:
					assert(0)
				try:
					self.__params[halName].setHalData(value)
				except KeyError:
					self.__pins[halName].setHalData(value)
				continue
			#TODO add support for net

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
			return self.__pins[k].halData
		except KeyError:
			return self.__params[k].halData

	def __setitem__(self, k, v):
		assert(self.__ready)
		self.__pins[k].setHalData(v)
