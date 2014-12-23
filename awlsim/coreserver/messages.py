# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server messages
#
# Copyright 2013-2014 Michael Buesch <m@bues.ch>
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

from awlsim.common.cpuspecs import *
from awlsim.common.project import *
from awlsim.common.datatypehelpers import *

from awlsim.coreserver.memarea import *

import struct
import socket
import errno


SocketErrors = (socket.error, BlockingIOError, ConnectionError)

class TransferError(Exception):
	EnumGen.start
	REASON_UNKNOWN		= EnumGen.item
	REASON_BLOCKING		= EnumGen.item
	REASON_REMOTEDIED	= EnumGen.item
	EnumGen.end

	def __init__(self, text, parentException=None, reason=None):
		if not text and parentException:
			text = str(parentException)
		if hasattr(parentException, "errno"):
			_errno = parentException.errno
		else:
			_errno = errno.ECONNREFUSED
		if reason is None:
			if parentException:
				# Try to find out whether this was an exception due
				# to blocking IO (on a nonblocking socket).
				# This varies between Python versions, argh.
				if isinstance(parentException, socket.timeout) or\
				   isinstance(parentException, BlockingIOError) or\
				   _errno == errno.EAGAIN or\
				   _errno == errno.EWOULDBLOCK or\
				   _errno == errno.EINTR:
					reason = self.REASON_BLOCKING
				else:
					reason = self.REASON_UNKNOWN
			else:
				reason = self.REASON_UNKNOWN
		Exception.__init__(self, text)
		self.parent = parentException
		self.reason = reason
		self.errno = _errno

class AwlSimMessage(object):
	# Header format:
	#	Magic (16 bit)
	#	Message ID (16 bit)
	#	Sequence count (16 bit)
	#	Reserved (16 bit)
	#	Payload length (32 bit)
	#	Payload (optional)
	hdrStruct = struct.Struct(str(">HHHHI"))

	HDR_MAGIC		= 0x5713
	HDR_LENGTH		= hdrStruct.size

	EnumGen.start
	MSG_ID_REPLY		= EnumGen.item # Generic status reply
	MSG_ID_EXCEPTION	= EnumGen.item
	MSG_ID_PING		= EnumGen.item
	MSG_ID_PONG		= EnumGen.item
	MSG_ID_RESET		= EnumGen.item
	MSG_ID_SHUTDOWN		= EnumGen.item
	MSG_ID_RUNSTATE		= EnumGen.item
	MSG_ID_LOAD_SYMTAB	= EnumGen.item
	MSG_ID_LOAD_CODE	= EnumGen.item
	MSG_ID_LOAD_HW		= EnumGen.item
	MSG_ID_SET_OPT		= EnumGen.item
	MSG_ID_CPUDUMP		= EnumGen.item
	MSG_ID_MAINTREQ		= EnumGen.item
	MSG_ID_GET_CPUSPECS	= EnumGen.item
	MSG_ID_CPUSPECS		= EnumGen.item
	MSG_ID_REQ_MEMORY	= EnumGen.item
	MSG_ID_MEMORY		= EnumGen.item
	MSG_ID_INSNSTATE	= EnumGen.item
	MSG_ID_INSNSTATE_CONFIG	= EnumGen.item
	MSG_ID_LOAD_LIB		= EnumGen.item
	MSG_ID_GET_RUNSTATE	= EnumGen.item
	MSG_ID_GET_IDENTS	= EnumGen.item
	MSG_ID_IDENTS		= EnumGen.item
	EnumGen.end

	_bytesLenStruct = struct.Struct(str(">I"))

	@classmethod
	def packString(cls, string):
		try:
			if not string:
				string = ""
			return cls.packBytes(string.encode("utf-8", "strict"))
		except UnicodeError as e:
			raise ValueError

	@classmethod
	def packBytes(cls, _bytes):
		try:
			if not _bytes:
				_bytes = b""
			if len(_bytes) > 0xFFFFFFFF:
				raise ValueError
			return cls._bytesLenStruct.pack(len(_bytes)) + _bytes
		except struct.error as e:
			raise ValueError

	@classmethod
	def unpackString(cls, data, offset = 0):
		try:
			_bytes, count = cls.unpackBytes(data, offset)
			return (_bytes.decode("utf-8", "strict"), count)
		except UnicodeError as e:
			raise ValueError

	@classmethod
	def unpackBytes(cls, data, offset = 0):
		try:
			(length, ) = cls._bytesLenStruct.unpack_from(data, offset)
			_bytes = data[offset + cls._bytesLenStruct.size :
				      offset + cls._bytesLenStruct.size + length]
			if len(_bytes) != length:
				raise ValueError
			return (_bytes, cls._bytesLenStruct.size + length)
		except struct.error as e:
			raise ValueError

	def __init__(self, msgId, seq=0):
		self.msgId = msgId
		self.seq = seq

	def toBytes(self, payloadLength=0):
		return self.hdrStruct.pack(self.HDR_MAGIC,
					   self.msgId,
					   self.seq,
					   0,
					   payloadLength)

	@classmethod
	def fromBytes(cls, payload):
		return cls()

class AwlSimMessage_REPLY(AwlSimMessage):
	EnumGen.start
	STAT_OK		= EnumGen.item
	STAT_FAIL	= EnumGen.item
	EnumGen.end

	plStruct = struct.Struct(str(">HHH"))

	@classmethod
	def make(cls, inReplyToMsg, status):
		return cls(inReplyToMsg.msgId, inReplyToMsg.seq, status)

	def __init__(self, inReplyToId, inReplyToSeq, status):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_REPLY)
		self.inReplyToId = inReplyToId
		self.inReplyToSeq = inReplyToSeq
		self.status = status

	def toBytes(self):
		pl = self.plStruct.pack(self.inReplyToId,
					self.inReplyToSeq,
					self.status)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			inReplyToId, inReplyToSeq, status =\
				cls.plStruct.unpack(payload)
		except struct.error as e:
			raise TransferError("REPLY: Invalid data format")
		return cls(inReplyToId, inReplyToSeq, status)

class AwlSimMessage_PING(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_PING)

class AwlSimMessage_PONG(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_PONG)

class AwlSimMessage_RESET(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_RESET)

class AwlSimMessage_SHUTDOWN(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_SHUTDOWN)

class AwlSimMessage_RUNSTATE(AwlSimMessage):
	EnumGen.start
	STATE_STOP	= EnumGen.item
	STATE_RUN	= EnumGen.item
	EnumGen.end

	plStruct = struct.Struct(str(">H"))

	def __init__(self, runState):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_RUNSTATE)
		self.runState = runState

	def toBytes(self):
		pl = self.plStruct.pack(self.runState)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			(runState, ) = cls.plStruct.unpack(payload)
		except struct.error as e:
			raise TransferError("RUNSTATE: Invalid data format")
		return cls(runState)

class AwlSimMessage_GET_RUNSTATE(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_GET_RUNSTATE)

class AwlSimMessage_EXCEPTION(AwlSimMessage):
	def __init__(self, exception):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_EXCEPTION)
		self.exception = exception

	def toBytes(self):
		try:
			pl = self.packString(self.exception.getReport(verbose = False)) +\
			     self.packString(self.exception.getReport(verbose = True))
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("EXCEPTION: Encoding error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			text, count = cls.unpackString(payload)
			verboseText, count = cls.unpackString(payload, count)
		except ValueError:
			raise TransferError("EXCEPTION: Encoding error")
		return cls(AwlSimErrorText(text, verboseText))

class _AwlSimMessage_source(AwlSimMessage):
	sourceClass = None

	def __init__(self, msgId, source):
		AwlSimMessage.__init__(self, msgId)
		self.source = source

	def toBytes(self):
		try:
			pl = self.packString(self.source.name) +\
				self.packString(self.source.filepath) +\
				self.packBytes(self.source.sourceBytes)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("SOURCE: Data format error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			count = 0
			name, cnt = cls.unpackString(payload, count)
			count += cnt
			filepath, cnt = cls.unpackString(payload, count)
			count += cnt
			sourceBytes, cnt = cls.unpackBytes(payload, count)
		except (ValueError, struct.error) as e:
			raise TransferError("SOURCE: Data format error")
		return cls(cls.sourceClass(name, filepath, sourceBytes))

class AwlSimMessage_LOAD_SYMTAB(_AwlSimMessage_source):
	sourceClass = SymTabSource

	def __init__(self, source):
		_AwlSimMessage_source.__init__(self, AwlSimMessage.MSG_ID_LOAD_SYMTAB, source)

class AwlSimMessage_LOAD_CODE(_AwlSimMessage_source):
	sourceClass = AwlSource

	def __init__(self, source):
		_AwlSimMessage_source.__init__(self, AwlSimMessage.MSG_ID_LOAD_CODE, source)

class AwlSimMessage_LOAD_HW(AwlSimMessage):
	def __init__(self, name, paramDict):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_LOAD_HW)
		self.name = name
		self.paramDict = paramDict

	def toBytes(self):
		payload = b""
		try:
			payload += self.packString(self.name)
			for pname, pval in self.paramDict.items():
				payload += self.packString(pname)
				payload += self.packString(pval)
			return AwlSimMessage.toBytes(self, len(payload)) + payload
		except (ValueError) as e:
			raise TransferError("LOAD_HW: Invalid data format")

	@classmethod
	def fromBytes(cls, payload):
		paramDict = {}
		offset = 0
		try:
			name, count = cls.unpackString(payload, offset)
			offset += count
			while offset < len(payload):
				pname, count = cls.unpackString(payload, offset)
				offset += count
				pval, count = cls.unpackString(payload, offset)
				offset += count
				paramDict[pname] = pval
		except (ValueError) as e:
			raise TransferError("LOAD_HW: Invalid data format")
		return cls(name = name, paramDict = paramDict)

class AwlSimMessage_LOAD_LIB(AwlSimMessage):
	plStruct = struct.Struct(str(">Hii"))

	def __init__(self, libSelection):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_LOAD_LIB)
		self.libSelection = libSelection

	# Pack a library selection.
	# May raise ValueError or struct.error
	@classmethod
	def packLibSelection(cls, libSel):
		payload = [ cls.packString(libSel.getLibName()), ]
		payload.append(cls.plStruct.pack(libSel.getEntryType(),
						 libSel.getEntryIndex(),
						 libSel.getEffectiveEntryIndex()))
		return b''.join(payload)

	# Unpack a library selection.
	# May raise ValueError, struct.error or AwlSimError
	@classmethod
	def unpackLibSelection(cls, payload, offset = 0):
		libName, count = cls.unpackString(payload, offset)
		offset += count
		eType, eIndex, effIndex =\
			cls.plStruct.unpack_from(payload, offset)
		offset += cls.plStruct.size
		return (AwlLibEntrySelection(
				libName = libName,
				entryType = eType,
				entryIndex = eIndex,
				effectiveEntryIndex = effIndex),
			offset)

	def toBytes(self):
		try:
			payload = self.packLibSelection(self.libSelection)
			return AwlSimMessage.toBytes(self, len(payload)) + payload
		except (ValueError, struct.error) as e:
			raise TransferError("LOAD_LIB: Invalid data format")

	@classmethod
	def fromBytes(cls, payload):
		try:
			libSelection, offset = cls.unpackLibSelection(payload)
		except (ValueError, struct.error, AwlSimError) as e:
			raise TransferError("LOAD_LIB: Invalid data format")
		return cls(libSelection = libSelection)

class AwlSimMessage_SET_OPT(AwlSimMessage):
	def __init__(self, name, value):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_SET_OPT)
		self.name = name
		self.value = value

	def getStrValue(self):
		return self.value

	def getIntValue(self):
		try:
			return int(self.value)
		except ValueError as e:
			raise AwlSimError("SET_OPT: Value is not an integer")

	def getBoolValue(self):
		try:
			return bool(self.getIntValue())
		except ValueError as e:
			raise AwlSimError("SET_OPT: Value is not a boolean")

	def getFloatValue(self):
		try:
			return float(self.value)
		except ValueError as e:
			raise AwlSimError("SET_OPT: Value is not a float")

	def toBytes(self):
		try:
			payload = self.packString(self.name)
			payload += self.packString(self.value)
		except ValueError as e:
			raise TransferError("SET_OPT: Invalid data format")
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			name, count = cls.unpackString(payload, offset)
			offset += count
			value, count = cls.unpackString(payload, offset)
			offset += count
		except ValueError as e:
			raise TransferError("SET_OPT: Invalid data format")
		return cls(name = name, value = value)

class AwlSimMessage_CPUDUMP(AwlSimMessage):
	def __init__(self, dumpText):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_CPUDUMP)
		self.dumpText = dumpText

	def toBytes(self):
		try:
			pl = self.packString(self.dumpText)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			dumpText, count = cls.unpackString(payload)
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")
		return cls(dumpText)

class AwlSimMessage_MAINTREQ(AwlSimMessage):
	plStruct = struct.Struct(str(">H"))

	def __init__(self, maintRequest):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_MAINTREQ)
		self.maintRequest = maintRequest

	def toBytes(self):
		pl = self.plStruct.pack(self.maintRequest.requestType) +\
		     self.packString(str(self.maintRequest))
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			(requestType, ) = cls.plStruct.unpack_from(payload, 0)
			msg, count = cls.unpackString(payload, cls.plStruct.size)
		except (struct.error, ValueError) as e:
			raise TransferError("MAINTREQ: Invalid data format")
		return cls(MaintenanceRequest(requestType, msg))

class AwlSimMessage_GET_CPUSPECS(AwlSimMessage):
	def __init__(self):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_GET_CPUSPECS)

class AwlSimMessage_CPUSPECS(AwlSimMessage):
	plStruct = struct.Struct(str(">32I"))

	def __init__(self, cpuspecs):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_CPUSPECS)
		self.cpuspecs = cpuspecs

	def toBytes(self):
		pl = self.plStruct.pack(self.cpuspecs.getConfiguredMnemonics(),
					self.cpuspecs.nrAccus,
					self.cpuspecs.nrTimers,
					self.cpuspecs.nrCounters,
					self.cpuspecs.nrFlags,
					self.cpuspecs.nrInputs,
					self.cpuspecs.nrOutputs,
					self.cpuspecs.nrLocalbytes,
					self.cpuspecs.clockMemByte & 0xFFFFFFFF,
					*( (0,) * 23 ) # padding
		)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			data = cls.plStruct.unpack(payload)
			(mnemonics, nrAccus, nrTimers,
			 nrCounters, nrFlags, nrInputs,
			 nrOutputs, nrLocalbytes, clockMemByte) = data[:9]
		except struct.error as e:
			raise TransferError("CPUSPECS: Invalid data format")
		cpuspecs = S7CPUSpecs()
		cpuspecs.setConfiguredMnemonics(mnemonics)
		cpuspecs.setNrAccus(nrAccus)
		cpuspecs.setNrTimers(nrTimers)
		cpuspecs.setNrCounters(nrCounters)
		cpuspecs.setNrFlags(nrFlags)
		cpuspecs.setNrInputs(nrInputs)
		cpuspecs.setNrOutputs(nrOutputs)
		cpuspecs.setNrLocalbytes(nrLocalbytes)
		cpuspecs.setClockMemByte(-1 if clockMemByte > 0xFFFF else clockMemByte)
		return cls(cpuspecs)

class AwlSimMessage_REQ_MEMORY(AwlSimMessage):
	# Payload header struct:
	#	flags (32 bit)
	#	repetition factor (32 bit)
	plHdrStruct = struct.Struct(str(">II"))

	# Payload memory area struct:
	#	memType (8 bit)
	#	flags (8 bit)
	#	index (16 bit)
	#	start (32 bit)
	#	length (32 bit)
	plAreaStruct = struct.Struct(str(">BBHII"))

	# Flags
	FLG_SYNC	= 1 << 0 # Synchronous. Returns a REPLY when finished.

	def __init__(self, flags, repetitionFactor, memAreas):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_REQ_MEMORY)
		self.flags = flags
		self.repetitionFactor = repetitionFactor
		self.memAreas = memAreas

	def toBytes(self):
		pl = self.plHdrStruct.pack(self.flags,
					   self.repetitionFactor)
		for memArea in self.memAreas:
			pl += self.plAreaStruct.pack(memArea.memType,
						     memArea.flags,
						     memArea.index,
						     memArea.start,
						     memArea.length)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, repetitionFactor =\
				cls.plHdrStruct.unpack_from(payload, offset)
			offset += cls.plHdrStruct.size
			memAreas = []
			while offset < len(payload):
				memType, mFlags, index, start, length =\
					cls.plAreaStruct.unpack_from(payload, offset)
				offset += cls.plAreaStruct.size
				memAreas.append(MemoryArea(memType, mFlags, index, start, length))
		except struct.error as e:
			raise TransferError("REQ_MEMORY: Invalid data format")
		return cls(flags, repetitionFactor, memAreas)

class AwlSimMessage_MEMORY(AwlSimMessage):
	# Payload header struct:
	#	flags (32 bit)
	plHdrStruct = struct.Struct(str(">I"))

	# Payload memory area struct:
	#	memType (8 bit)
	#	flags (8 bit)
	#	index (16 bit)
	#	start (32 bit)
	#	specified length (32 bit)
	#	actual length (32 bit)
	#	the actual binary data (variable length, padded to 32-bit boundary)
	plAreaStruct = struct.Struct(str(">BBHIII"))

	# Flags
	FLG_SYNC	= 1 << 0 # Synchronous. Returns a REPLY when finished.

	def __init__(self, flags, memAreas):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_MEMORY)
		self.flags = flags
		self.memAreas = memAreas

	def toBytes(self):
		pl = [ self.plHdrStruct.pack(self.flags) ]
		for memArea in self.memAreas:
			actualLength = len(memArea.data)
			pl.append(self.plAreaStruct.pack(memArea.memType,
							 memArea.flags,
							 memArea.index,
							 memArea.start,
							 memArea.length,
							 actualLength))
			pl.append(bytes(memArea.data))
			# Pad to a 32-bit boundary
			pl.append(b'\x00' * (roundUp(actualLength, 4) - actualLength))
		pl = b''.join(pl)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			(flags, ) = cls.plHdrStruct.unpack_from(payload, offset)
			offset += cls.plHdrStruct.size
			memAreas = []
			while offset < len(payload):
				memType, mFlags, index, start, length, actualLength =\
					cls.plAreaStruct.unpack_from(payload, offset)
				offset += cls.plAreaStruct.size
				data = payload[offset : offset + actualLength]
				offset += roundUp(actualLength, 4)
				if len(data) != actualLength:
					raise IndexError
				memAreas.append(MemoryArea(memType, mFlags, index,
							   start, length, data))
		except (struct.error, IndexError) as e:
			raise TransferError("MEMORY: Invalid data format")
		return cls(flags, memAreas)

class AwlSimMessage_INSNSTATE(AwlSimMessage):
	# Payload data struct:
	#	AWL line number (32 bit)
	#	Serial number. Reset to 0 on cycle exit. (32 bit)
	#	Flags (16 bit) (currently unused. Set to 0)
	#	CPU status word (16 bit)
	#	CPU ACCU 1 (32 bit)
	#	CPU ACCU 2 (32 bit)
	#	CPU ACCU 3 (32 bit)
	#	CPU ACCU 4 (32 bit)
	#	CPU AR 1 (32 bit)
	#	CPU AR 2 (32 bit)
	#	CPU DB register (16 bit)
	#	CPU DI register (16 bit)
	#	AWL source ident hash bytes (variable length)
	plDataStruct = struct.Struct(str(">IIHHIIIIIIHH"))

	def __init__(self, sourceId, lineNr, serial, flags, stw, accu1, accu2, accu3, accu4, ar1, ar2, db, di):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_INSNSTATE)
		self.sourceId = sourceId
		self.lineNr = lineNr
		self.serial = serial
		self.flags = flags
		self.stw = stw
		self.accu1 = accu1
		self.accu2 = accu2
		self.accu3 = accu3
		self.accu4 = accu4
		self.ar1 = ar1
		self.ar2 = ar2
		self.db = db
		self.di = di

	def toBytes(self):
		pl = self.plDataStruct.pack(
			self.lineNr, self.serial,
			self.flags, self.stw, self.accu1, self.accu2,
			self.accu3, self.accu4, self.ar1, self.ar2,
			self.db, self.di)
		pl += self.packBytes(self.sourceId)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			lineNr, serial, flags, stw, accu1, accu2, accu3, accu4, ar1, ar2, db, di =\
				cls.plDataStruct.unpack_from(payload, 0)
			sourceId, offset = cls.unpackBytes(payload, cls.plDataStruct.size)
		except (struct.error, IndexError) as e:
			raise TransferError("INSNSTATE: Invalid data format")
		return cls(sourceId, lineNr, serial, flags, stw, accu1, accu2, accu3, accu4, ar1, ar2, db, di)

class AwlSimMessage_INSNSTATE_CONFIG(AwlSimMessage):
	# Payload data struct:
	#	Flags (32 bit)
	#	From AWL line (32 bit)
	#	To AWL line (32 bit)
	#	AWL source ident hash bytes (variable length)
	plDataStruct = struct.Struct(str(">III"))

	# Flags:
	FLG_SYNC		= 1 << 0 # Synchronous status reply.
	FLG_CLEAR_ONLY		= 1 << 1 # Just clear current settings.
	FLG_CLEAR		= 1 << 2 # Clear, then apply settings.

	def __init__(self, flags, sourceId, fromLine, toLine):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_INSNSTATE_CONFIG)
		self.flags = flags
		self.sourceId = sourceId
		self.fromLine = fromLine
		self.toLine = toLine

	def toBytes(self):
		pl = self.plDataStruct.pack(
			self.flags, self.fromLine, self.toLine)
		pl += self.packBytes(self.sourceId)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			flags, fromLine, toLine =\
				cls.plDataStruct.unpack_from(payload, 0)
			sourceId, offset = cls.unpackBytes(payload, cls.plDataStruct.size)
		except (struct.error, IndexError) as e:
			raise TransferError("INSNSTATE_CONFIG: Invalid data format")
		return cls(flags, sourceId, fromLine, toLine)

class AwlSimMessage_GET_IDENTS(AwlSimMessage):
	# Get-flags. Specify what information to get.
	EnumGen.start
	GET_AWLSRCS		= EnumGen.bitmask # Get AwlSource()s (w/o data)
	GET_SYMTABSRCS		= EnumGen.bitmask # Get SymTabSource()s (w/o data)
	GET_HWMODS		= EnumGen.bitmask # Get HW modules
	GET_LIBSELS		= EnumGen.bitmask # Get AwlLibEntrySelection()s
	EnumGen.end

	# Payload header struct:
	#	Get-flags (32 bit)
	#	Reserved (32 bit)
	plHdrStruct = struct.Struct(str(">II"))

	def __init__(self, getFlags):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_GET_IDENTS)
		self.getFlags = getFlags

	def toBytes(self):
		payload = self.plHdrStruct.pack(self.getFlags, 0)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			getFlags, _unused = cls.plHdrStruct.unpack_from(payload, 0)
		except (ValueError, struct.error) as e:
			raise TransferError("GET_IDENTS: Invalid data format")
		return cls(getFlags)

class AwlSimMessage_IDENTS(AwlSimMessage):
	# Payload header struct:
	#	Number of AWL sources (32 bit)
	#	Number of symbol tables (32 bit)
	#	Number of hardware modules (32 bit)
	#	Number of library selections (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	plHdrStruct = struct.Struct(str(">IIIIII"))

	# Payload module header struct:
	#	Number of parameters (32 bit)
	#	Reserved (32 bit)
	plModStruct = struct.Struct(str(">II"))

	# awlSources: List of AwlSource()s
	# symTabSources: List of SymTabSource()s
	# hwMods: List of tuples: (modName, parametersDict)
	# libSelections: List of AwlLibEntrySelection()s
	def __init__(self, awlSources, symTabSources, hwMods, libSelections):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_IDENTS)
		self.awlSources = awlSources
		self.symTabSources = symTabSources
		self.hwMods = hwMods
		self.libSelections = libSelections

	def toBytes(self):
		payload = [ self.plHdrStruct.pack(len(self.awlSources),
						  len(self.symTabSources),
						  len(self.hwMods),
						  len(self.libSelections),
						  0, 0), ]
		for src in self.awlSources:
			payload.append(self.packString(src.name))
			payload.append(self.packString(src.filepath))
			payload.append(self.packBytes(src.identHash))
		for src in self.symTabSources:
			payload.append(self.packString(src.name))
			payload.append(self.packString(src.filepath))
			payload.append(self.packBytes(src.identHash))
		for modName, parametersDict in self.hwMods:
			payload.append(self.plModStruct.pack(len(parametersDict), 0))
			payload.append(self.packString(modName))
			for pName, pVal in parametersDict.items():
				payload.append(self.packString(pName))
				payload.append(self.packString(pVal))
		for libSel in self.libSelections:
			payload.append(AwlSimMessage_LOAD_LIB.packLibSelection(libSel))
		payload = b''.join(payload)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			awlSources = []
			symTabSources = []
			hwMods = []
			libSelections = []
			offset = 0
			nrAwl, nrSym, nrHw, nrLib, _a, _b  = cls.plHdrStruct.unpack_from(
								payload, offset)
			offset += cls.plHdrStruct.size
			for i in range(nrAwl):
				name, count = cls.unpackString(payload, offset)
				offset += count
				path, count = cls.unpackString(payload, offset)
				offset += count
				identHash, count = cls.unpackBytes(payload, offset)
				offset += count
				src = AwlSource(name, path, None)
				src.identHash = identHash # Force hash
				awlSources.append(src)
			for i in range(nrSym):
				name, count = cls.unpackString(payload, offset)
				offset += count
				path, count = cls.unpackString(payload, offset)
				offset += count
				identHash, count = cls.unpackBytes(payload, offset)
				offset += count
				src = SymTabSource(name, path, None)
				src.identHash = identHash # Force hash
				symTabSources.append(src)
			for i in range(nrHw):
				nrParam, _unused = cls.plModStruct.unpack_from(
								payload, offset)
				offset += cls.plModStruct.size
				modName, count = cls.unpackString(payload, offset)
				offset += count
				params = {}
				for i in range(nrParam):
					pName, count = cls.unpackString(payload, offset)
					offset += count
					pVal, count = cls.unpackString(payload, offset)
					offset += count
					params[pName] = pVal
				hwMods.append( (modName, params) )
			for i in range(nrLib):
				libSel, offset = AwlSimMessage_LOAD_LIB.unpackLibSelection(
						payload, offset)
				libSelections.append(libSel)
		except (ValueError, struct.error, AwlSimError) as e:
			raise TransferError("IDENTS: Invalid data format")
		return cls(awlSources = awlSources,
			   symTabSources = symTabSources,
			   hwMods = hwMods,
			   libSelections = libSelections)

class AwlSimMessageTransceiver(object):
	id2class = {
		AwlSimMessage.MSG_ID_REPLY		: AwlSimMessage_REPLY,
		AwlSimMessage.MSG_ID_EXCEPTION		: AwlSimMessage_EXCEPTION,
		AwlSimMessage.MSG_ID_PING		: AwlSimMessage_PING,
		AwlSimMessage.MSG_ID_PONG		: AwlSimMessage_PONG,
		AwlSimMessage.MSG_ID_RESET		: AwlSimMessage_RESET,
		AwlSimMessage.MSG_ID_SHUTDOWN		: AwlSimMessage_SHUTDOWN,
		AwlSimMessage.MSG_ID_RUNSTATE		: AwlSimMessage_RUNSTATE,
		AwlSimMessage.MSG_ID_GET_RUNSTATE	: AwlSimMessage_GET_RUNSTATE,
		AwlSimMessage.MSG_ID_LOAD_SYMTAB	: AwlSimMessage_LOAD_SYMTAB,
		AwlSimMessage.MSG_ID_LOAD_CODE		: AwlSimMessage_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_HW		: AwlSimMessage_LOAD_HW,
		AwlSimMessage.MSG_ID_LOAD_LIB		: AwlSimMessage_LOAD_LIB,
		AwlSimMessage.MSG_ID_SET_OPT		: AwlSimMessage_SET_OPT,
		AwlSimMessage.MSG_ID_CPUDUMP		: AwlSimMessage_CPUDUMP,
		AwlSimMessage.MSG_ID_MAINTREQ		: AwlSimMessage_MAINTREQ,
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: AwlSimMessage_GET_CPUSPECS,
		AwlSimMessage.MSG_ID_CPUSPECS		: AwlSimMessage_CPUSPECS,
		AwlSimMessage.MSG_ID_REQ_MEMORY		: AwlSimMessage_REQ_MEMORY,
		AwlSimMessage.MSG_ID_MEMORY		: AwlSimMessage_MEMORY,
		AwlSimMessage.MSG_ID_INSNSTATE		: AwlSimMessage_INSNSTATE,
		AwlSimMessage.MSG_ID_INSNSTATE_CONFIG	: AwlSimMessage_INSNSTATE_CONFIG,
		AwlSimMessage.MSG_ID_GET_IDENTS		: AwlSimMessage_GET_IDENTS,
		AwlSimMessage.MSG_ID_IDENTS		: AwlSimMessage_IDENTS,
	}

	def __init__(self, sock, peerInfoString):
		self.sock = sock
		self.peerInfoString = peerInfoString

		# Transmit status
		self.txSeqCount = 0

		# Receive buffer
		self.buf = b""
		self.msgId = None
		self.seq = None
		self.payloadLen = None

		try:
			if isJython: #XXX Workaround
				self.sock.setblocking(True)
			self.__timeout = None
			self.sock.settimeout(self.__timeout)

			if self.sock.family in (socket.AF_INET, socket.AF_INET6) and\
			   self.sock.type == socket.SOCK_STREAM:
				self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8192)
		except SocketErrors as e:
			raise AwlSimError("Failed to initialize socket: %s" % str(e))

	def shutdown(self):
		if self.sock:
			CALL_NOEX(self.sock.shutdown, socket.SHUT_RDWR)
			CALL_NOEX(self.sock.close)
			self.sock = None

	def send(self, msg, timeout=None):
		if timeout != self.__timeout:
			self.sock.settimeout(timeout)
			self.__timeout = timeout

		msg.seq = self.txSeqCount
		self.txSeqCount = (self.txSeqCount + 1) & 0xFFFF

		offset, data = 0, msg.toBytes()
		while offset < len(data):
			try:
				offset += self.sock.send(data[offset : ])
			except SocketErrors as e:
				transferError = TransferError(None, parentException = e)
				if transferError.reason != TransferError.REASON_BLOCKING:
					raise transferError

	def receive(self, timeout=0.0):
		if timeout != self.__timeout:
			self.sock.settimeout(timeout)
			self.__timeout = timeout

		hdrLen = AwlSimMessage.HDR_LENGTH
		if len(self.buf) < hdrLen:
			try:
				data = self.sock.recv(hdrLen - len(self.buf))
			except SocketErrors as e:
				transferError = TransferError(None, parentException = e)
				if transferError.reason == TransferError.REASON_BLOCKING:
					return None
				raise transferError
			if not data:
				# The remote end closed the connection
				raise TransferError(None,
					reason = TransferError.REASON_REMOTEDIED)
			self.buf += data
			if len(self.buf) < hdrLen:
				return None
			try:
				magic, self.msgId, self.seq, _reserved, self.payloadLen =\
					AwlSimMessage.hdrStruct.unpack(self.buf)
			except struct.error as e:
				raise AwlSimError("Received message with invalid "
					"header format.")
			if magic != AwlSimMessage.HDR_MAGIC:
				raise AwlSimError("Received message with invalid "
					"magic value (was 0x%04X, expected 0x%04X)." %\
					(magic, AwlSimMessage.HDR_MAGIC))
			if self.payloadLen:
				return None
		if len(self.buf) < hdrLen + self.payloadLen:
			data = self.sock.recv(hdrLen + self.payloadLen - len(self.buf))
			if not data:
				# The remote end closed the connection
				raise TransferError(None,
					reason = TransferError.REASON_REMOTEDIED)
			self.buf += data
			if len(self.buf) < hdrLen + self.payloadLen:
				return None
		try:
			cls = self.id2class[self.msgId]
		except KeyError:
			raise AwlSimError("Received unknown message: 0x%04X" %\
				self.msgId)
		msg = cls.fromBytes(self.buf[hdrLen : ])
		msg.seq = self.seq
		self.buf, self.msgId, self.seq, self.payloadLen = b"", None, None, None
		return msg
