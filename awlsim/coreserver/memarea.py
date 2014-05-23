# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server memory area helpers
#
# Copyright 2013 Michael Buesch <m@bues.ch>
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


class MemoryArea(object):
	# Possible memType values
	EnumGen.start
	TYPE_E		= EnumGen.item # input memory
	TYPE_A		= EnumGen.item # output memory
	TYPE_M		= EnumGen.item # flags memory
	TYPE_L		= EnumGen.item # localdata memory
	TYPE_DB		= EnumGen.item # DB memory
	TYPE_T		= EnumGen.item # timer
	TYPE_Z		= EnumGen.item # counter
	TYPE_STW	= EnumGen.item # status word
	EnumGen.end

	# Possible flags
	FLG_ERR_READ	= 0x01
	FLG_ERR_WRITE	= 0x02

	def __init__(self, memType, flags, index, start, length, data=b''):
		self.memType = memType
		self.flags = flags
		self.index = index
		self.start = start
		self.length = length
		self.data = data

	def __raiseReadErr(self, exception):
		self.flags |= self.FLG_ERR_READ
		raise exception

	def __raiseWriteErr(self, exception):
		self.flags |= self.FLG_ERR_WRITE
		raise exception

	def __read_E(self, cpu):
		self.data = bytes(cpu.inputs[self.start : self.start + self.length])

	def __read_A(self, cpu):
		self.data = bytes(cpu.outputs[self.start : self.start + self.length])

	def __read_M(self, cpu):
		self.data = bytes(cpu.flags[self.start : self.start + self.length])

	def __read_L(self, cpu):
		self.data = bytes(cpu.callStackTop.localdata[self.start : self.start + self.length])

	def __read_DB(self, cpu):
		try:
			db = cpu.dbs[self.index]
		except KeyError:
			self.__raiseReadErr(
				AwlSimError("MemoryArea: Read access to "
				"nonexistent DB %d" % self.index)
			)
		if not (db.permissions & db.PERM_READ):
			self.__raiseReadErr(
				AwlSimError("MemoryArea: Read access to "
				"read-protected DB %d" % self.index)
			)
		self.data = bytes(db.structInstance.dataBytes[self.start : self.start + self.length])

	def __read_T(self, cpu):
		try:
			timer = cpu.timers[self.index]
		except IndexError as e:
			self.__raiseReadErr(
				AwlSimError("MemoryArea: Invalid timer index %d" % self.index)
			)
		if self.start == 1:
			self.data, self.length = b'\x01' if timerget() else b'\x00', 1
		elif self.start == 16:
			v = timer.getTimevalBin()
			self.data, self.length = bytes(((v >> 8) & 0xFF, v & 0xFF)), 2
		else:
			self.__raiseReadErr(
				AwlSimError("MemoryArea: Invalid start=%d in timer read. "
				"Must be 1 or 16." % self.start)
			)

	def __read_Z(self, cpu):
		try:
			counter = cpu.timers[self.index]
		except IndexError as e:
			self.__raiseReadErr(
				AwlSimError("MemoryArea: Invalid counter index %d" % self.index)
			)
		if self.start == 1:
			self.data, self.length = b'\x01' if counter.get() else b'\x00', 1
		elif self.start == 16:
			v = counter.getValueBin()
			self.data, self.length = bytes(((v >> 8) & 0xFF, v & 0xFF)), 2
		else:
			self.__raiseReadErr(
				AwlSimError("MemoryArea: Invalid start=%d in counter read. "
				"Must be 1 or 16." % self.start)
			)

	def __read_STW(self, cpu):
		stw = cpu.statusWord.getWord()
		self.data, self.length = bytes(((stw >> 8) & 0xFF, stw & 0xFF)), 2

	__readHandlers = {
		TYPE_E		: __read_E,
		TYPE_A		: __read_A,
		TYPE_M		: __read_M,
		TYPE_L		: __read_L,
		TYPE_DB		: __read_DB,
		TYPE_T		: __read_T,
		TYPE_Z		: __read_Z,
		TYPE_STW	: __read_STW,
	}

	def __write_E(self, cpu):
		cpu.inputs[self.start : self.start + self.length] = self.data

	def __write_A(self, cpu):
		cpu.outputs[self.start : self.start + self.length] = self.data

	def __write_M(self, cpu):
		cpu.flags[self.start : self.start + self.length] = self.data

	def __write_DB(self, cpu):
		try:
			db = cpu.dbs[self.index]
		except KeyError:
			self.__raiseWriteErr(
				AwlSimError("MemoryArea: Write access to "
				"nonexistent DB %d" % self.index)
			)
		if not (db.permissions & db.PERM_WRITE):
			self.__raiseWriteErr(
				AwlSimError("MemoryArea: Write access to "
				"write-protected DB %d" % self.index)
			)
		db.structInstance.dataBytes[self.start : self.start + self.length] = self.data

	__writeHandlers = {
		TYPE_E		: __write_E,
		TYPE_A		: __write_A,
		TYPE_M		: __write_M,
		TYPE_DB		: __write_DB,
	}

	def readFromCpu(self, cpu):
		try:
			self.__readHandlers[self.memType](self, cpu)
		except KeyError:
			self.__raiseReadErr(
				AwlSimError("Invalid MemoryArea memType %d "
				"in read operation" % self.memType)
			)
		except (IndexError, TypeError) as e:
			self.__raiseReadErr(
				AwlSimError("Invalid MemoryArea read")
			)

	def writeToCpu(self, cpu):
		try:
			self.__writeHandlers[self.memType](self, cpu)
		except KeyError:
			self.__raiseWriteErr(
				AwlSimError("Invalid MemoryArea memType %d "
				"in write operation" % self.memType)
			)
		except (IndexError, TypeError) as e:
			self.__raiseWriteErr(
				AwlSimError("Invalid MemoryArea write")
			)

	# Check whether another area overlaps with this one.
	# Doesn't compare the flags.
	# Doesn't compare the data.
	def overlapsWith(self, other):
		if self.memType != other.memType or\
		   self.index != other.index:
			return False
		if self.memType in (self.TYPE_T, self.TYPE_Z, self.TYPE_STW):
			return self.start == other.start and\
			       self.length == other.length
		if self.length and other.length:
			selfEnd = self.start + self.length - 1
			otherEnd = other.start + other.length - 1
			if selfEnd < other.start or\
			   otherEnd < self.start:
				return False
		elif self.length != other.length:
			return False # One length is zero and the other isn't
		return True

	def overlapsWithAny(self, otherMemAreas):
		return any(self.overlapsWith(a) for a in otherMemAreas)

	def __repr__(self):
		return "MemoryArea(memType=%d, flags=0x%02X, index=%d, "\
			"start=%d, length=%d, len(data)=%s)" %\
			(self.memType, self.flags, self.index,
			 self.start, self.length,
			 str(len(self.data)) if self.data is not None else "None")
