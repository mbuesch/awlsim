# -*- coding: utf-8 -*-
#
# AWL simulator - PLC core server messages
#
# Copyright 2013-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.cpuspecs import * #+cimport
from awlsim.common.cpuconfig import *
from awlsim.common.project import *
from awlsim.common.hwmod import *
from awlsim.common.datatypehelpers import * #+cimport
from awlsim.common.blockinfo import *
from awlsim.common.net import *
from awlsim.common.sources import *
from awlsim.common.exceptions import *

from awlsim.coreserver.memarea import *

from awlsim.library.libselection import *

import struct
import socket
import errno


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

	HDR_MAGIC		= 0x5718
	HDR_LENGTH		= hdrStruct.size

	# Message IDs:
	EnumGen.start
	# Basic functionality
	MSG_ID_REPLY		= EnumGen.itemAt(0x0000) # Generic status reply
	MSG_ID_EXCEPTION	= EnumGen.item
	MSG_ID_MAINTREQ		= EnumGen.item
	MSG_ID_PING		= EnumGen.item
	MSG_ID_PONG		= EnumGen.item
	MSG_ID_RESET		= EnumGen.item
	MSG_ID_SHUTDOWN		= EnumGen.item
	# Program sources and blocks
	MSG_ID_GET_AWLSRC	= EnumGen.itemAt(0x0100)
	MSG_ID_AWLSRC		= EnumGen.item
	MSG_ID_GET_SYMTABSRC	= EnumGen.item
	MSG_ID_SYMTABSRC	= EnumGen.item
	MSG_ID_HWMOD		= EnumGen.item
	MSG_ID_LIBSEL		= EnumGen.item
	MSG_ID_GET_FUPSRC	= EnumGen.item		#TODO not implemented, yet
	MSG_ID_FUPSRC		= EnumGen.item
	MSG_ID_GET_KOPSRC	= EnumGen.item		#TODO not implemented, yet
	MSG_ID_KOPSRC		= EnumGen.item
	MSG_ID_BUILD		= EnumGen.itemAt(0x0170)
	MSG_ID_REMOVESRC	= EnumGen.itemAt(0x0180)
	MSG_ID_REMOVEBLK	= EnumGen.item
	MSG_ID_GET_IDENTS	= EnumGen.itemAt(0x0190)
	MSG_ID_IDENTS		= EnumGen.item
	MSG_ID_GET_BLOCKINFO	= EnumGen.item
	MSG_ID_BLOCKINFO	= EnumGen.item
	# Configuration
	MSG_ID_GET_OPT		= EnumGen.itemAt(0x0200) #TODO not implemented, yet
	MSG_ID_OPT		= EnumGen.item
	MSG_ID_GET_CPUSPECS	= EnumGen.item
	MSG_ID_CPUSPECS		= EnumGen.item
	MSG_ID_GET_CPUCONF	= EnumGen.item
	MSG_ID_CPUCONF		= EnumGen.item
	# State
	MSG_ID_GET_RUNSTATE	= EnumGen.itemAt(0x0300)
	MSG_ID_RUNSTATE		= EnumGen.item
	MSG_ID_GET_CPUDUMP	= EnumGen.item		#TODO not implemented, yet
	MSG_ID_CPUDUMP		= EnumGen.item
	MSG_ID_REQ_MEMORY	= EnumGen.item
	MSG_ID_MEMORY		= EnumGen.item
	MSG_ID_INSNSTATE_CONFIG	= EnumGen.item
	MSG_ID_INSNSTATE	= EnumGen.item
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

	# Default values for instance attributes:
	msgId = None	# MSG_ID_...
	seq = 0		# Sequence number.

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
	msgId = AwlSimMessage.MSG_ID_REPLY

	EnumGen.start
	STAT_OK		= EnumGen.item
	STAT_FAIL	= EnumGen.item
	EnumGen.end

	plStruct = struct.Struct(str(">HHH"))

	@classmethod
	def make(cls, inReplyToMsg, status):
		return cls(inReplyToMsg.msgId, inReplyToMsg.seq, status)

	def __init__(self, inReplyToId, inReplyToSeq, status):
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
	msgId = AwlSimMessage.MSG_ID_PING

class AwlSimMessage_PONG(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_PONG

class AwlSimMessage_RESET(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_RESET

class AwlSimMessage_SHUTDOWN(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_SHUTDOWN

class AwlSimMessage_RUNSTATE(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_RUNSTATE

	EnumGen.start
	STATE_STOP	= EnumGen.item
	STATE_RUN	= EnumGen.item
	EnumGen.end

	plStruct = struct.Struct(str(">H"))

	def __init__(self, runState):
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
	msgId = AwlSimMessage.MSG_ID_GET_RUNSTATE

class AwlSimMessage_EXCEPTION(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_EXCEPTION

	# Payload struct:
	#	flags (32 bit)
	#	lineNr (32 bit)
	#	exception type (string)
	#	sourceName (string)
	#	sourceId (bytes)
	#	failing insn string (string)
	#	message (string)
	#	verboseMsg (string)
	plStruct = struct.Struct(str(">II"))

	def __init__(self, exception):
		self.exception = exception

	def toBytes(self):
		try:
			e = self.exception
			lineNr = e.getLineNr()
			lineNr = 0xFFFFFFFF if lineNr is None else lineNr
			pl = self.plStruct.pack(0, lineNr) +\
			     self.packString(e.EXC_TYPE) +\
			     self.packString(e.getSourceName() or "") +\
			     self.packBytes(e.getSourceId() or "") +\
			     self.packString(e.getFailingInsnStr()) +\
			     self.packString(e.getReport(verbose = False)) +\
			     self.packString(e.getReport(verbose = True))
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("EXCEPTION: Encoding error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, lineNr = cls.plStruct.unpack_from(payload, offset)
			offset += cls.plStruct.size
			excType, count = cls.unpackString(payload, offset)
			offset += count
			sourceName, count = cls.unpackString(payload, offset)
			offset += count
			sourceId, count = cls.unpackBytes(payload, offset)
			offset += count
			failingInsnStr, count = cls.unpackString(payload, offset)
			offset += count
			text, count = cls.unpackString(payload, offset)
			offset += count
			verboseText, count = cls.unpackString(payload, offset)
		except ValueError:
			raise TransferError("EXCEPTION: Encoding error")
		e = FrozenAwlSimError(excType = excType,
				      errorText = text,
				      verboseErrorText = verboseText)
		e.setLineNr(lineNr if lineNr < 0xFFFFFFFF else None)
		e.setSourceName(sourceName)
		e.setSourceId(sourceId)
		e.setFailingInsnStr(failingInsnStr)
		return cls(e)

class _AwlSimMessage_GET_source(AwlSimMessage):
	msgId = None

	def __init__(self, identHash):
		self.identHash = identHash

	def toBytes(self):
		payload = self.packBytes(self.identHash)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			identHash, count = cls.unpackBytes(payload, 0)
		except (ValueError, struct.error, AwlSimError) as e:
			raise TransferError("GET_source: Invalid data format")
		return cls(identHash = identHash)

class _AwlSimMessage_source(AwlSimMessage):
	sourceClass = None

	# Payload struct:
	#	flags (32 bit)
	#	unused (32 bit)
	#	unused (32 bit)
	#	unused (32 bit)
	#	sourceName (string)
	#	sourceFilePath (string)
	#	sourceBytes (bytes)
	plStruct = struct.Struct(str(">IIII"))

	FLAG_ENABLED	= 1 << 0

	def __init__(self, source):
		if not source:
			source = self.sourceClass()
		self.source = source

	def toBytes(self):
		try:
			flags = 0
			if self.source.enabled:
				flags |= self.FLAG_ENABLED
			pl = self.plStruct.pack(flags, 0, 0, 0) +\
				self.packString(self.source.name) +\
				self.packString(self.source.filepath) +\
				self.packBytes(self.source.sourceBytes)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("SOURCE: Data format error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			offset = 0
			flags, unused0, unused1, unused2 =\
				cls.plStruct.unpack_from(payload, offset)
			offset += cls.plStruct.size
			name, cnt = cls.unpackString(payload, offset)
			offset += cnt
			filepath, cnt = cls.unpackString(payload, offset)
			offset += cnt
			sourceBytes, cnt = cls.unpackBytes(payload, offset)
		except (ValueError, struct.error) as e:
			raise TransferError("SOURCE: Data format error")
		return cls(cls.sourceClass(name=name,
					   enabled=(flags & cls.FLAG_ENABLED),
					   filepath=filepath,
					   sourceBytes=sourceBytes))

class AwlSimMessage_GET_SYMTABSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_SYMTABSRC

class AwlSimMessage_SYMTABSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_SYMTABSRC
	sourceClass = SymTabSource

class AwlSimMessage_GET_AWLSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_AWLSRC

class AwlSimMessage_AWLSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_AWLSRC
	sourceClass = AwlSource

class AwlSimMessage_GET_FUPSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_FUPSRC

class AwlSimMessage_FUPSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_FUPSRC
	sourceClass = FupSource

class AwlSimMessage_GET_KOPSRC(_AwlSimMessage_GET_source):
	msgId = AwlSimMessage.MSG_ID_GET_KOPSRC

class AwlSimMessage_KOPSRC(_AwlSimMessage_source):
	msgId = AwlSimMessage.MSG_ID_KOPSRC
	sourceClass = KopSource

class AwlSimMessage_HWMOD(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_HWMOD

	# hwmodDesc -> HwmodDescriptor instance
	def __init__(self, hwmodDesc):
		self.hwmodDesc = hwmodDesc

	def toBytes(self):
		payload = b""
		try:
			payload += self.packString(self.hwmodDesc.getModuleName())
			for pname, pval in dictItems(self.hwmodDesc.getParameters()):
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
		return cls(HwmodDescriptor(name, paramDict))

class AwlSimMessage_LIBSEL(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_LIBSEL

	plStruct = struct.Struct(str(">Hii"))

	def __init__(self, libSelection):
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

class AwlSimMessage_BUILD(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_BUILD

	plStruct = struct.Struct(str(">16x"))

	def toBytes(self):
		try:
			pl = self.plStruct.pack()
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except (ValueError, struct.error) as e:
			raise TransferError("BUILD: Invalid data format")

	@classmethod
	def fromBytes(cls, payload):
		try:
			pass
		except (ValueError, struct.error) as e:
			raise TransferError("BUILD: Invalid data format")
		return cls()

class AwlSimMessage_OPT(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_OPT

	def __init__(self, name, value):
		self.name = name
		self.value = value

	def getStrValue(self):
		return self.value

	def getIntValue(self):
		try:
			return int(self.value)
		except ValueError as e:
			raise AwlSimError("OPT: Value is not an integer")

	def getBoolValue(self):
		try:
			return bool(self.getIntValue())
		except ValueError as e:
			raise AwlSimError("OPT: Value is not a boolean")

	def getFloatValue(self):
		try:
			return float(self.value)
		except ValueError as e:
			raise AwlSimError("OPT: Value is not a float")

	def toBytes(self):
		try:
			payload = self.packString(self.name)
			payload += self.packString(self.value)
		except ValueError as e:
			raise TransferError("OPT: Invalid data format")
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
			raise TransferError("OPT: Invalid data format")
		return cls(name = name, value = value)

class AwlSimMessage_CPUDUMP(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_CPUDUMP

	def __init__(self, dumpText):
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
	msgId = AwlSimMessage.MSG_ID_MAINTREQ

	plStruct = struct.Struct(str(">H"))

	def __init__(self, maintRequest):
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
	msgId = AwlSimMessage.MSG_ID_GET_CPUSPECS

class AwlSimMessage_CPUSPECS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_CPUSPECS

	plStruct = struct.Struct(str(">32I"))

	def __init__(self, cpuspecs):
		self.cpuspecs = cpuspecs

	def toBytes(self):
		pl = self.plStruct.pack(self.cpuspecs.nrAccus,
					self.cpuspecs.nrTimers,
					self.cpuspecs.nrCounters,
					self.cpuspecs.nrFlags,
					self.cpuspecs.nrInputs,
					self.cpuspecs.nrOutputs,
					self.cpuspecs.nrLocalbytes,
					*( (0,) * 25 ) # padding
		)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			data = cls.plStruct.unpack(payload)
			(nrAccus, nrTimers,
			 nrCounters, nrFlags, nrInputs,
			 nrOutputs, nrLocalbytes) = data[:7]
		except struct.error as e:
			raise TransferError("CPUSPECS: Invalid data format")
		cpuspecs = S7CPUSpecs()
		cpuspecs.setNrAccus(nrAccus)
		cpuspecs.setNrTimers(nrTimers)
		cpuspecs.setNrCounters(nrCounters)
		cpuspecs.setNrFlags(nrFlags)
		cpuspecs.setNrInputs(nrInputs)
		cpuspecs.setNrOutputs(nrOutputs)
		cpuspecs.setNrLocalbytes(nrLocalbytes)
		return cls(cpuspecs)

class AwlSimMessage_GET_CPUCONF(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_CPUCONF

class AwlSimMessage_CPUCONF(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_CPUCONF

	plStruct = struct.Struct(str(">32I"))

	def __init__(self, cpuconf):
		self.cpuconf = cpuconf

	def toBytes(self):
		pl = self.plStruct.pack(self.cpuconf.getConfiguredMnemonics(),
					self.cpuconf.clockMemByte & 0xFFFFFFFF,
					*( (0,) * 30 ) # padding
		)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			data = cls.plStruct.unpack(payload)
			(mnemonics, clockMemByte) = data[:2]
		except struct.error as e:
			raise TransferError("CPUCONF: Invalid data format")
		cpuconf = S7CPUConfig()
		cpuconf.setConfiguredMnemonics(mnemonics)
		cpuconf.setClockMemByte(-1 if clockMemByte > 0xFFFF else clockMemByte)
		return cls(cpuconf)

class AwlSimMessage_REQ_MEMORY(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_REQ_MEMORY

	# Payload header struct:
	#	flags (32 bit)
	#	repetition period in nanoseconds (32 bit)
	plHdrStruct = struct.Struct(str(">Ii"))

	# Payload memory area struct:
	#	memType (8 bit)
	#	flags (8 bit)
	#	index (16 bit)
	#	start (32 bit)
	#	length (32 bit)
	plAreaStruct = struct.Struct(str(">BBHII"))

	# Flags
	FLG_SYNC	= 1 << 0 # Synchronous. Returns a REPLY when finished.

	def __init__(self, flags, repetitionPeriod, memAreas):
		self.flags = flags
		self.repetitionPeriod = repetitionPeriod
		self.memAreas = memAreas

	def toBytes(self):
		repPeriodNs = int(round(self.repetitionPeriod * 1000000000.0))
		pl = self.plHdrStruct.pack(self.flags, repPeriodNs)
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
			flags, repPeriodNs =\
				cls.plHdrStruct.unpack_from(payload, offset)
			offset += cls.plHdrStruct.size
			repetitionPeriod = float(repPeriodNs) / 1000000000.0
			memAreas = []
			while offset < len(payload):
				memType, mFlags, index, start, length =\
					cls.plAreaStruct.unpack_from(payload, offset)
				offset += cls.plAreaStruct.size
				memAreas.append(MemoryArea(memType, mFlags, index, start, length))
		except struct.error as e:
			raise TransferError("REQ_MEMORY: Invalid data format")
		return cls(flags, repetitionPeriod, memAreas)

class AwlSimMessage_MEMORY(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_MEMORY

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
	msgId = AwlSimMessage.MSG_ID_INSNSTATE

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
	#	Source ident hash bytes (variable length)
	plDataStruct = struct.Struct(str(">IIHHIIIIIIHH"))

	def __init__(self, sourceId, lineNr, serial, flags, stw, accu1, accu2, accu3, accu4, ar1, ar2, db, di):
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
	msgId = AwlSimMessage.MSG_ID_INSNSTATE_CONFIG

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

class AwlSimMessage_REMOVESRC(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_REMOVESRC

	def __init__(self, identHash):
		self.identHash = identHash

	def toBytes(self):
		payload = self.packBytes(self.identHash)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			identHash, count = cls.unpackBytes(payload, 0)
		except (ValueError, struct.error) as e:
			raise TransferError("REMOVESRC: Invalid data format")
		return cls(identHash)

class AwlSimMessage_REMOVEBLK(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_REMOVEBLK

	# Block info payload struct:
	#	BlockInfo.TYPE_... (32 bit)
	#	Block index (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	plStruct = struct.Struct(str(">IIII"))

	def __init__(self, blockInfo):
		self.blockInfo = blockInfo

	def toBytes(self):
		payload = self.plStruct.pack(
				self.blockInfo.blockIndex,
				self.blockInfo.blockType,
				0, 0)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			blockIndex, blockType, _unused0, _unused1 = \
				cls.plStruct.unpack_from(payload, 0)
			blockInfo = BlockInfo(
				blockType = blockType,
				blockIndex = blockIndex)
		except (ValueError, struct.error) as e:
			raise TransferError("REMOVEBLK: Invalid data format")
		return cls(blockInfo)

class AwlSimMessage_GET_IDENTS(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_IDENTS

	# Get-flags. Specify what information to get.
	EnumGen.start
	GET_AWLSRCS		= EnumGen.bitmask # Get AwlSource()s (w/o data)
	GET_SYMTABSRCS		= EnumGen.bitmask # Get SymTabSource()s (w/o data)
	GET_HWMODS		= EnumGen.bitmask # Get HW modules
	GET_LIBSELS		= EnumGen.bitmask # Get AwlLibEntrySelection()s
	GET_FUPSRCS		= EnumGen.bitmask # Get FupSource()s (w/o data)
	GET_KOPSRCS		= EnumGen.bitmask # Get KopSource()s (w/o data)
	EnumGen.end

	# Payload header struct:
	#	Get-flags (32 bit)
	#	Reserved (32 bit)
	plHdrStruct = struct.Struct(str(">II"))

	def __init__(self, getFlags):
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
	msgId = AwlSimMessage.MSG_ID_IDENTS

	# Payload header struct:
	#	Number of AWL sources (32 bit)
	#	Number of symbol tables (32 bit)
	#	Number of hardware modules (32 bit)
	#	Number of library selections (32 bit)
	#	Number of FUP sources (32 bit)
	#	Number of KOP sources (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	plHdrStruct = struct.Struct(str(">6I40x"))

	# Payload module header struct:
	#	Number of parameters (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	plModStruct = struct.Struct(str(">I12x"))

	# awlSources: List of AwlSource()s
	# symTabSources: List of SymTabSource()s
	# hwMods: List of HwmodDescriptor()s
	# libSelections: List of AwlLibEntrySelection()s
	def __init__(self, awlSources, symTabSources, hwMods, libSelections, fupSources, kopSources):
		self.awlSources = awlSources
		self.symTabSources = symTabSources
		self.hwMods = hwMods
		self.libSelections = libSelections
		self.fupSources = fupSources
		self.kopSources = kopSources

	def toBytes(self):
		payload = [ self.plHdrStruct.pack(len(self.awlSources),
						  len(self.symTabSources),
						  len(self.hwMods),
						  len(self.libSelections),
						  len(self.fupSources),
						  len(self.kopSources)) ]
		def addSrcs(srcs):
			for src in srcs:
				payload.append(self.packString(src.name))
				payload.append(self.packString(src.filepath))
				payload.append(self.packBytes(src.identHash))
		addSrcs(self.awlSources)
		addSrcs(self.symTabSources)
		for hwmodDesc in self.hwMods:
			params = hwmodDesc.getParameters()
			payload.append(self.plModStruct.pack(len(params)))
			payload.append(self.packString(hwmodDesc.getModuleName()))
			for pName, pVal in dictItems(params):
				payload.append(self.packString(pName))
				payload.append(self.packString(pVal))
		for libSel in self.libSelections:
			payload.append(AwlSimMessage_LIBSEL.packLibSelection(libSel))
		addSrcs(self.fupSources)
		addSrcs(self.kopSources)
		payload = b''.join(payload)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			awlSources = []
			symTabSources = []
			hwMods = []
			libSelections = []
			fupSources = []
			kopSources = []
			offset = 0
			nrAwl, nrSym, nrHw, nrLib, nrFup, nrKop = cls.plHdrStruct.unpack_from(
								payload, offset)
			offset += cls.plHdrStruct.size
			def unpackSrcs(srcClass, sourcesList, count, offset):
				for i in range(count):
					name, count = cls.unpackString(payload, offset)
					offset += count
					path, count = cls.unpackString(payload, offset)
					offset += count
					identHash, count = cls.unpackBytes(payload, offset)
					offset += count
					src = srcClass(name, path, None)
					src.identHash = identHash # Force hash
					sourcesList.append(src)
				return offset
			offset = unpackSrcs(AwlSource, awlSources, nrAwl, offset)
			offset = unpackSrcs(SymTabSource, symTabSources, nrSym, offset)
			for i in range(nrHw):
				(nrParam, ) = cls.plModStruct.unpack_from(
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
				hwMods.append(HwmodDescriptor(modName, params))
			for i in range(nrLib):
				libSel, offset = AwlSimMessage_LIBSEL.unpackLibSelection(
						payload, offset)
				libSelections.append(libSel)
			offset = unpackSrcs(FupSource, fupSources, nrFup, offset)
			offset = unpackSrcs(KopSource, kopSources, nrKop, offset)
		except (ValueError, struct.error, AwlSimError) as e:
			raise TransferError("IDENTS: Invalid data format")
		return cls(awlSources = awlSources,
			   symTabSources = symTabSources,
			   hwMods = hwMods,
			   libSelections = libSelections,
			   fupSources = fupSources,
			   kopSources = kopSources)

class AwlSimMessage_GET_BLOCKINFO(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_GET_BLOCKINFO

	# Get-flags. Specify what information to get.
	EnumGen.start
	GET_OB_INFO		= EnumGen.bitmask # Get OB info
	GET_FC_INFO		= EnumGen.bitmask # Get FC info
	GET_FB_INFO		= EnumGen.bitmask # Get FB info
	GET_DB_INFO		= EnumGen.bitmask # Get DB info
	EnumGen.end

	# Payload header struct:
	#	Get-flags (32 bit)
	#	Reserved (32 bit)
	plHdrStruct = struct.Struct(str(">II"))

	def __init__(self, getFlags):
		self.getFlags = getFlags

	def toBytes(self):
		payload = self.plHdrStruct.pack(self.getFlags, 0)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			getFlags, _unused = cls.plHdrStruct.unpack_from(payload, 0)
		except (ValueError, struct.error) as e:
			raise TransferError("GET_BLOCKINFO: Invalid data format")
		return cls(getFlags)

class AwlSimMessage_BLOCKINFO(AwlSimMessage):
	msgId = AwlSimMessage.MSG_ID_BLOCKINFO

	# Payload header struct:
	#	Number of block infos (32 bit)
	#	Reserved (32 bit)
	plHdrStruct = struct.Struct(str(">II"))

	# Block info payload struct:
	#	BlockInfo.TYPE_... (32 bit)
	#	Block index (32 bit)
	#	Reserved (32 bit)
	#	Reserved (32 bit)
	#	ident hash bytes (length prefix, variable length)
	plBlockInfoStruct = struct.Struct(str(">IIII"))

	def __init__(self, blockInfos):
		self.blockInfos = blockInfos

	def toBytes(self):
		payload = [ self.plHdrStruct.pack(len(self.blockInfos), 0) ]
		for blockInfo in self.blockInfos:
			payload.append(self.plBlockInfoStruct.pack(
					blockInfo.blockIndex,
					blockInfo.blockType,
					0, 0))
			payload.append(self.packBytes(blockInfo.identHash))
		payload = b"".join(payload)
		return AwlSimMessage.toBytes(self, len(payload)) + payload

	@classmethod
	def fromBytes(cls, payload):
		try:
			blockInfos = []
			nrBlockInfos, _unused = cls.plHdrStruct.unpack_from(payload, 0)
			offset = cls.plHdrStruct.size
			for i in range(nrBlockInfos):
				blockIndex, blockType, _unused0, _unused1 = \
					cls.plBlockInfoStruct.unpack_from(payload, offset)
				offset += cls.plBlockInfoStruct.size
				identHash, count = cls.unpackBytes(payload, offset)
				offset += count
				blockInfos.append(BlockInfo(
					blockType = blockType,
					blockIndex = blockIndex,
					identHash = identHash)
				)
		except (ValueError, struct.error) as e:
			raise TransferError("BLOCKINFO: Invalid data format")
		return cls(blockInfos = blockInfos)

class AwlSimMessageTransceiver(object):
	id2class = {
		AwlSimMessage.MSG_ID_REPLY		: AwlSimMessage_REPLY,
		AwlSimMessage.MSG_ID_EXCEPTION		: AwlSimMessage_EXCEPTION,
		AwlSimMessage.MSG_ID_MAINTREQ		: AwlSimMessage_MAINTREQ,
		AwlSimMessage.MSG_ID_PING		: AwlSimMessage_PING,
		AwlSimMessage.MSG_ID_PONG		: AwlSimMessage_PONG,
		AwlSimMessage.MSG_ID_RESET		: AwlSimMessage_RESET,
		AwlSimMessage.MSG_ID_SHUTDOWN		: AwlSimMessage_SHUTDOWN,
		AwlSimMessage.MSG_ID_GET_AWLSRC		: AwlSimMessage_GET_AWLSRC,
		AwlSimMessage.MSG_ID_AWLSRC		: AwlSimMessage_AWLSRC,
		AwlSimMessage.MSG_ID_GET_SYMTABSRC	: AwlSimMessage_GET_SYMTABSRC,
		AwlSimMessage.MSG_ID_SYMTABSRC		: AwlSimMessage_SYMTABSRC,
		AwlSimMessage.MSG_ID_HWMOD		: AwlSimMessage_HWMOD,
		AwlSimMessage.MSG_ID_LIBSEL		: AwlSimMessage_LIBSEL,
		AwlSimMessage.MSG_ID_GET_FUPSRC		: AwlSimMessage_GET_FUPSRC,
		AwlSimMessage.MSG_ID_FUPSRC		: AwlSimMessage_FUPSRC,
		AwlSimMessage.MSG_ID_GET_KOPSRC		: AwlSimMessage_GET_KOPSRC,
		AwlSimMessage.MSG_ID_KOPSRC		: AwlSimMessage_KOPSRC,
		AwlSimMessage.MSG_ID_BUILD		: AwlSimMessage_BUILD,
		AwlSimMessage.MSG_ID_REMOVESRC		: AwlSimMessage_REMOVESRC,
		AwlSimMessage.MSG_ID_REMOVEBLK		: AwlSimMessage_REMOVEBLK,
		AwlSimMessage.MSG_ID_GET_IDENTS		: AwlSimMessage_GET_IDENTS,
		AwlSimMessage.MSG_ID_IDENTS		: AwlSimMessage_IDENTS,
		AwlSimMessage.MSG_ID_GET_BLOCKINFO	: AwlSimMessage_GET_BLOCKINFO,
		AwlSimMessage.MSG_ID_BLOCKINFO		: AwlSimMessage_BLOCKINFO,
#TODO		AwlSimMessage.MSG_ID_GET_OPT		: AwlSimMessage_GET_OPT,
		AwlSimMessage.MSG_ID_OPT		: AwlSimMessage_OPT,
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: AwlSimMessage_GET_CPUSPECS,
		AwlSimMessage.MSG_ID_CPUSPECS		: AwlSimMessage_CPUSPECS,
		AwlSimMessage.MSG_ID_GET_CPUCONF	: AwlSimMessage_GET_CPUCONF,
		AwlSimMessage.MSG_ID_CPUCONF		: AwlSimMessage_CPUCONF,
		AwlSimMessage.MSG_ID_GET_RUNSTATE	: AwlSimMessage_GET_RUNSTATE,
		AwlSimMessage.MSG_ID_RUNSTATE		: AwlSimMessage_RUNSTATE,
#TODO		AwlSimMessage.MSG_ID_GET_CPUDUMP	: AwlSimMessage_GET_CPUDUMP,
		AwlSimMessage.MSG_ID_CPUDUMP		: AwlSimMessage_CPUDUMP,
		AwlSimMessage.MSG_ID_REQ_MEMORY		: AwlSimMessage_REQ_MEMORY,
		AwlSimMessage.MSG_ID_MEMORY		: AwlSimMessage_MEMORY,
		AwlSimMessage.MSG_ID_INSNSTATE_CONFIG	: AwlSimMessage_INSNSTATE_CONFIG,
		AwlSimMessage.MSG_ID_INSNSTATE		: AwlSimMessage_INSNSTATE,
	}

	DEFAULT_TX_BUF_SIZE	= 1024 * 100
	DEFAULT_RX_BUF_SIZE	= 1024 * 100

	def __init__(self, sock, peerInfoString):
		self.sock = sock
		self.peerInfoString = peerInfoString
		self.__isTCP = sock.family in (socket.AF_INET, socket.AF_INET6) and\
			       sock.type == socket.SOCK_STREAM
		self.__haveCork = hasattr(socket, "TCP_CORK")
		self.__haveCork = False #XXX disabled

		# Transmit status
		self.txSeqCount = 0

		# Receive buffer
		self.rxBuffers = []
		self.rxByteCnt = 0
		self.msgId = None
		self.seq = None
		self.payloadLen = None

		try:
			if isJython: #XXX Workaround
				self.sock.setblocking(True)
			self.__timeout = None
			self.sock.settimeout(self.__timeout)

			self.sock.setsockopt(socket.SOL_SOCKET,
					     socket.SO_OOBINLINE,
					     1)
			SO_PRIORITY = getattr(socket, "SO_PRIORITY",
					      12 if (osIsPosix and isPy2Compat) else None)
			if SO_PRIORITY is not None:
				self.sock.setsockopt(socket.SOL_SOCKET,
						     SO_PRIORITY,
						     6)
			self.setTxBufSize(self.DEFAULT_TX_BUF_SIZE)
			self.setRxBufSize(self.DEFAULT_RX_BUF_SIZE)
			if self.__isTCP:
				self.sock.setsockopt(socket.IPPROTO_TCP,
						     socket.TCP_NODELAY,
						     1)
		except SocketErrors as e:
			raise AwlSimError("Failed to initialize socket: %s" % str(e))

	def setTxBufSize(self, size):
		self.sock.setsockopt(socket.SOL_SOCKET,
				     socket.SO_SNDBUF,
				     size)

	def setRxBufSize(self, size):
		self.sock.setsockopt(socket.SOL_SOCKET,
				     socket.SO_RCVBUF,
				     size)

	def shutdown(self):
		if self.sock:
			with suppressAllExc:
				self.sock.shutdown(socket.SHUT_RDWR)
			with suppressAllExc:
				self.sock.close()
			self.sock = None

	def txCork(self, cork = True):
		if self.__isTCP and self.__haveCork:
			self.sock.setsockopt(socket.IPPROTO_TCP,
					     socket.TCP_CORK,
					     1 if cork else 0)

	def send(self, msg, timeout=None):
		if timeout != self.__timeout:
			self.sock.settimeout(timeout)
			self.__timeout = timeout

		msg.seq = self.txSeqCount
		self.txSeqCount = (self.txSeqCount + 1) & 0xFFFF

		offset, data = 0, memoryview(msg.toBytes())
		datalen, sock, _SocketErrors = len(data), self.sock, SocketErrors
		while offset < datalen:
			try:
				offset += sock.send(data[offset : ])
			except _SocketErrors as e:
				transferError = TransferError(None, parentException = e)
				if transferError.reason != TransferError.REASON_BLOCKING:
					raise transferError

	def receive(self, timeout=0.0):
		if timeout != self.__timeout:
			self.sock.settimeout(timeout)
			self.__timeout = timeout

		hdrLen, rxByteCnt = AwlSimMessage.HDR_LENGTH, self.rxByteCnt
		if rxByteCnt < hdrLen:
			try:
				data = self.sock.recv(hdrLen - rxByteCnt)
			except SocketErrors as e:
				transferError = TransferError(None, parentException = e)
				if transferError.reason == TransferError.REASON_BLOCKING:
					return None
				raise transferError
			if not data:
				# The remote end closed the connection
				raise TransferError(None,
					reason = TransferError.REASON_REMOTEDIED)
			self.rxBuffers.append(data)
			self.rxByteCnt = rxByteCnt = rxByteCnt + len(data)
			if rxByteCnt < hdrLen:
				return None
			try:
				magic, self.msgId, self.seq, _reserved, self.payloadLen =\
					AwlSimMessage.hdrStruct.unpack(b"".join(self.rxBuffers))
				self.rxBuffers = [] # Discard raw header bytes.
			except struct.error as e:
				raise AwlSimError("Received message with invalid "
					"header format.")
			if magic != AwlSimMessage.HDR_MAGIC:
				raise AwlSimError("Received message with invalid "
					"magic value (was 0x%04X, expected 0x%04X)." %\
					(magic, AwlSimMessage.HDR_MAGIC))
			if self.payloadLen:
				return None
		msgLen = hdrLen + self.payloadLen
		if rxByteCnt < msgLen:
			try:
				data = self.sock.recv(msgLen - rxByteCnt)
			except SocketErrors as e:
				transferError = TransferError(None, parentException = e)
				if transferError.reason == TransferError.REASON_BLOCKING:
					return None
				raise transferError
			if not data:
				# The remote end closed the connection
				raise TransferError(None,
					reason = TransferError.REASON_REMOTEDIED)
			self.rxBuffers.append(data)
			self.rxByteCnt = rxByteCnt = rxByteCnt + len(data)
			if rxByteCnt < msgLen:
				return None
		try:
			cls = self.id2class[self.msgId]
		except KeyError:
			raise AwlSimError("Received unknown message: 0x%04X" %\
				self.msgId)
		msg = cls.fromBytes(b"".join(self.rxBuffers))
		msg.seq = self.seq
		self.rxBuffers, self.rxByteCnt, self.msgId, self.seq, self.payloadLen =\
			[], 0, None, None, None
		return msg
