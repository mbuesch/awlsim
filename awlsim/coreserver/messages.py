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
from awlsim.core.compat import *

from awlsim.coreserver.memarea import *
from awlsim.core.util import *
from awlsim.core.datatypehelpers import *
from awlsim.core.cpuspecs import *
from awlsim.core.project import *

import struct
import socket
import errno


class TransferError(Exception):
	pass

class AwlSimMessage(object):
	# Header format:
	#	Magic (16 bit)
	#	Message ID (16 bit)
	#	Sequence count (16 bit)
	#	Reserved (16 bit)
	#	Payload length (32 bit)
	#	Payload (optional)
	hdrStruct = struct.Struct(str(">HHHHI"))

	HDR_MAGIC		= 0x5711
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

class AwlSimMessage_EXCEPTION(AwlSimMessage):
	def __init__(self, exceptionText):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_EXCEPTION)
		self.exceptionText = exceptionText

	def toBytes(self):
		try:
			textBytes = self.exceptionText.encode()
			return AwlSimMessage.toBytes(self, len(textBytes)) + textBytes
		except UnicodeError:
			raise TransferError("EXCEPTION: Unicode error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			text = payload.decode()
		except UnicodeError:
			raise TransferError("EXCEPTION: Unicode error")
		return cls(text)

class _AwlSimMessage_source(AwlSimMessage):
	sourceClass = None

	def __init__(self, msgId, source):
		AwlSimMessage.__init__(self, msgId)
		self.source = source

	def toBytes(self):
		try:
			pl = self.packString(self.source.identifier) +\
				self.packString(self.source.filepath) +\
				self.packBytes(self.source.sourceBytes)
			return AwlSimMessage.toBytes(self, len(pl)) + pl
		except ValueError:
			raise TransferError("SOURCE: Data format error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			identifier, count = cls.unpackString(payload)
			filepath, cnt = cls.unpackString(payload, count)
			count += cnt
			sourceBytes, cnt = cls.unpackBytes(payload, count)
		except ValueError:
			raise TransferError("SOURCE: Data format error")
		return cls(cls.sourceClass(identifier, filepath, sourceBytes))

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
			dumpBytes = self.dumpText.encode()
			return AwlSimMessage.toBytes(self, len(dumpBytes)) + dumpBytes
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")

	@classmethod
	def fromBytes(cls, payload):
		try:
			dumpText = payload.decode()
		except UnicodeError:
			raise TransferError("CPUDUMP: Unicode error")
		return cls(dumpText)

class AwlSimMessage_MAINTREQ(AwlSimMessage):
	plStruct = struct.Struct(str(">H"))

	def __init__(self, requestType):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_MAINTREQ)
		self.requestType = requestType

	def toBytes(self):
		pl = self.plStruct.pack(self.requestType)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			(requestType, ) = cls.plStruct.unpack(payload)
		except struct.error as e:
			raise TransferError("MAINTREQ: Invalid data format")
		return cls(requestType)

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
					*( (0,) * 24 ) # padding
		)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			data = cls.plStruct.unpack(payload)
			(mnemonics, nrAccus, nrTimers,
			 nrCounters, nrFlags, nrInputs,
			 nrOutputs, nrLocalbytes) = data[:8]
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
			pl.append(memArea.data)
			# Pad to a 32-bit boundary
			pl.append(b'\x00' * (round_up(actualLength, 4) - actualLength))
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
				offset += round_up(actualLength, 4)
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
	#	Flags (16 bit)
	#	CPU status word (16 bit)
	#	CPU ACCU 1 (32 bit)
	#	CPU ACCU 2 (32 bit)
	#	CPU AR 1 (32 bit)
	#	CPU AR 2 (32 bit)
	#	CPU DB register (16 bit)
	#	CPU DI register (16 bit)
	plDataStruct = struct.Struct(str(">IIHHIIIIHH"))

	def __init__(self, lineNr, serial, flags, stw, accu1, accu2, ar1, ar2, db, di):
		AwlSimMessage.__init__(self, AwlSimMessage.MSG_ID_INSNSTATE)
		self.lineNr = lineNr
		self.serial = serial
		self.flags = flags
		self.stw = stw
		self.accu1 = accu1
		self.accu2 = accu2
		self.ar1 = ar1
		self.ar2 = ar2
		self.db = db
		self.di = di

	def toBytes(self):
		pl = self.plDataStruct.pack(self.lineNr, self.serial,
			self.flags, self.stw, self.accu1, self.accu2,
			self.ar1, self.ar2, self.db, self.di)
		return AwlSimMessage.toBytes(self, len(pl)) + pl

	@classmethod
	def fromBytes(cls, payload):
		try:
			lineNr, serial, flags, stw, accu1, accu2, ar1, ar2, db, di =\
				cls.plDataStruct.unpack_from(payload, 0)
		except (struct.error, IndexError) as e:
			raise TransferError("INSNSTATE: Invalid data format")
		return cls(lineNr, serial, flags, stw, accu1, accu2, ar1, ar2, db, di)

class AwlSimMessageTransceiver(object):
	class RemoteEndDied(Exception): pass

	id2class = {
		AwlSimMessage.MSG_ID_REPLY		: AwlSimMessage_REPLY,
		AwlSimMessage.MSG_ID_EXCEPTION		: AwlSimMessage_EXCEPTION,
		AwlSimMessage.MSG_ID_PING		: AwlSimMessage_PING,
		AwlSimMessage.MSG_ID_PONG		: AwlSimMessage_PONG,
		AwlSimMessage.MSG_ID_RESET		: AwlSimMessage_RESET,
		AwlSimMessage.MSG_ID_SHUTDOWN		: AwlSimMessage_SHUTDOWN,
		AwlSimMessage.MSG_ID_RUNSTATE		: AwlSimMessage_RUNSTATE,
		AwlSimMessage.MSG_ID_LOAD_SYMTAB	: AwlSimMessage_LOAD_SYMTAB,
		AwlSimMessage.MSG_ID_LOAD_CODE		: AwlSimMessage_LOAD_CODE,
		AwlSimMessage.MSG_ID_LOAD_HW		: AwlSimMessage_LOAD_HW,
		AwlSimMessage.MSG_ID_SET_OPT		: AwlSimMessage_SET_OPT,
		AwlSimMessage.MSG_ID_CPUDUMP		: AwlSimMessage_CPUDUMP,
		AwlSimMessage.MSG_ID_MAINTREQ		: AwlSimMessage_MAINTREQ,
		AwlSimMessage.MSG_ID_GET_CPUSPECS	: AwlSimMessage_GET_CPUSPECS,
		AwlSimMessage.MSG_ID_CPUSPECS		: AwlSimMessage_CPUSPECS,
		AwlSimMessage.MSG_ID_REQ_MEMORY		: AwlSimMessage_REQ_MEMORY,
		AwlSimMessage.MSG_ID_MEMORY		: AwlSimMessage_MEMORY,
		AwlSimMessage.MSG_ID_INSNSTATE		: AwlSimMessage_INSNSTATE,
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
		except socket.error as e:
			raise AwlSimError("Failed to initialize socket: %s" % str(e))

	def shutdown(self):
		if self.sock:
			try:
				self.sock.shutdown(socket.SHUT_RDWR)
			except socket.error as e:
				pass
			try:
				self.sock.close()
			except socket.error as e:
				pass
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
			except (socket.error, BlockingIOError) as e:
				if e.errno != errno.EAGAIN and\
				   e.errno != errno.EWOULDBLOCK and\
				   not isinstance(e, BlockingIOError) and\
				   not isinstance(e, socket.timeout):
					raise TransferError(str(e))

	def receive(self, timeout=0.0):
		if timeout != self.__timeout:
			self.sock.settimeout(timeout)
			self.__timeout = timeout

		hdrLen = AwlSimMessage.HDR_LENGTH
		if len(self.buf) < hdrLen:
			try:
				data = self.sock.recv(hdrLen - len(self.buf))
			except (socket.error, BlockingIOError) as e:
				if e.errno == errno.EAGAIN or\
				   e.errno == errno.EWOULDBLOCK or\
				   isinstance(e, BlockingIOError):
					return None
				raise
			if not data:
				# The remote end closed the connection
				raise self.RemoteEndDied()
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
				raise self.RemoteEndDied()
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
