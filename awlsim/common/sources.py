# -*- coding: utf-8 -*-
#
# AWL simulator - source management
#
# Copyright 2014-2019 Michael Buesch <m@bues.ch>
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

from awlsim.common.xmlfactory import *
from awlsim.common.refmanager import *
from awlsim.common.util import *
from awlsim.common.exceptions import *

#from awlsim.core.blocks cimport CodeBlock #@cy
#from awlsim.core.datablocks cimport DB #@cy

import base64, binascii
import hashlib


__all__ = [
	"AwlSource",
	"FupSource",
	"KopSource",
	"SymTabSource",
	"SourceManager",
	"SourceContainer",
]


class SourceFactory(XmlFactory):
	def parser_open(self, tag=None):
		self.__data = []
		self.__haveSourceTag = False
		if tag:
			self.__parseSourceTag(tag)
		XmlFactory.parser_open(self, tag)

	def __parseSourceTag(self, tag):
		project, source = self.project, self.source
		srcType = tag.getAttrInt("type")
		name = tag.getAttr("name", source.SRCTYPE)
		filename = tag.getAttr("file", "")
		enabled = tag.getAttrBool("enabled", True)
		volatile = tag.getAttrBool("volatile", False)
		if source.SRCTYPE_ID != srcType:
			raise self.Error("SourceFactory: Got unexpected "
				"source type %d instead of %d." % (
				srcType, source.SRCTYPE_ID))
		if filename:
			filename = RelPath(project.projectDir).fromRelative(filename)
			source.readFromFile(filename, compatReEncode=True)
		else:
			source.filepath = ""
		source.name = name
		source.enabled = enabled
		source.volatile = volatile
		self.__haveSourceTag = True

	def parser_beginTag(self, tag):
		if not self.__haveSourceTag and tag.name == "source":
			self.__parseSourceTag(tag)
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		source = self.source
		if tag.name == "source":
			if self.__data:
				sourceData = "".join(self.__data)
				if source.STRIP_DATA:
					# Strip all leading and trailing white space.
					sourceData = sourceData.strip()
				else:
					# Only strip leading and trailing line break
					# that we added during compose.
					idx = sourceData.find("\n")
					if idx >= 0 and not sourceData[:idx].strip():
						sourceData = sourceData[idx+1:]
					idx = sourceData.rfind("\n")
					if idx >= 0 and not sourceData[idx+1:].strip():
						sourceData = sourceData[:idx]
					if sourceData.endswith("\r"):
						sourceData = sourceData[:-1]
				# Enforce the line end format.
				if source.DOS_EOL:
					sourceData = toDosEol(sourceData)
				else:
					sourceData = toUnixEol(sourceData)
				# Add the data to the source.
				try:
					source.sourceBytes = sourceData.encode(source.ENCODING)
				except UnicodeError as e:
					raise self.Error("Failed to encode source code data")
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def parser_data(self, data):
		source = self.source
		if not source.isFileBacked():
			self.__data.append(data)
			return
		XmlFactory.parser_data(self, data)

	def composer_getTags(self):
		project, source = self.project, self.source

		childTags = []

		filename = ""
		if source.isFileBacked():
			filename = RelPath(project.projectDir).toRelative(source.filepath)
			data = None
		else:
			try:
				data = source.sourceBytes.decode(source.ENCODING)
				# Enforce UNIX line endings.
				data = toUnixEol(data)
				# Add leading and trailing line break.
				data = "\n%s\n" % data
			except UnicodeError as e:
				raise self.Error("Failed to decode source code data")
		tags = [
			self.Tag(name="source",
				 comment="\n%s source code" % source.SRCTYPE,
				 attrs={
					"type"		: str(int(source.SRCTYPE_ID)),
					"file"		: str(filename),
					"name"		: str(source.name),
					"enabled"	: "1" if source.enabled else "0",
					"volatile"	: "1" if source.volatile else "",
				 },
				 data=data,
				 tags=childTags,
				 useCDATA=True),
		]
		return tags

class GenericSource(object):
	SRCTYPE		= "<generic>"
	SRCTYPE_ID	= -1 # .awlpro file format ID
	IDENT_HASH	= hashlib.sha256
	ENCODING	= "<unknown>"
	COMPAT_ENCODING	= "<unknown>"
	STRIP_DATA	= False
	DOS_EOL		= False

	factory		= SourceFactory

	if isMicroPython:
		latin1Trans = {
			b"\xE4" : "ä",
			b"\xC4" : "Ä",
			b"\xF6" : "ö",
			b"\xD6" : "Ö",
			b"\xFC" : "ü",
			b"\xDC" : "Ü",
			b"\xDF" : "ß",
		}

	def __init__(self,
		     name="",
		     enabled=True,
		     filepath="",
		     sourceBytes=b"",
		     userData={},
		     volatile=False):
		"""Initialize a source code object.
		name: Name string of the source.
		enabled: True, if the source is active.
		filepath: Path string to the source file, or an empty string.
		sourceBytes: bytes object of the actual source code.
		userData: Optional dict that may be filled with user data.
		          The source code object will not touch this data.
			  This data will _not_ be transferred to the core server.
			  This data does _not_ contribute to the identHash.
		volatile: Optional flag: This source is volatile.
			  Such sources will not be stored in the core server project.
			  This flag does _not_ contribute to the identHash.
		"""
		self.name = name
		self.enabled = enabled
		self.filepath = filepath
		self.sourceBytes = sourceBytes
		self.userData = userData.copy()
		self.volatile = volatile

		self.__identHash = None
		self.__identHashForced = False

	@property
	def name(self):
		return self.__name

	@name.setter
	def name(self, newName):
		self.__name = newName
		self.__identHash = None
		self.__identHashForced = False

	@property
	def enabled(self):
		return self.__enabled

	@enabled.setter
	def enabled(self, enabled):
		self.__enabled = bool(enabled)
		self.__identHash = None
		self.__identHashForced = False

	@property
	def volatile(self):
		return self.__volatile

	@volatile.setter
	def volatile(self, volatile):
		self.__volatile = bool(volatile)

	@property
	def filepath(self):
		return self.__filepath

	@filepath.setter
	def filepath(self, newFilepath):
		self.__filepath = newFilepath

	@property
	def sourceBytes(self):
		"""Get the source byte stream, in native ENCODING format.
		"""
		return self.__sourceBytes

	@sourceBytes.setter
	def sourceBytes(self, newSourceBytes):
		"""Set the source byte stream.
		The bytes must be in native ENCODING format.
		"""
		self.__sourceBytes = newSourceBytes
		self.__identHash = None
		self.__identHashForced = False

	@property
	def compatSourceBytes(self):
		"""Get the source byte stream, in COMPAT_ENCODING format.
		"""
		return self._compatReEncode(self.sourceBytes, self.ENCODING,
					    self.COMPAT_ENCODING)

	@property
	def sourceText(self):
		"""Get the source as decoded text.
		"""
		try:
			return self.sourceBytes.decode(self.ENCODING)
		except UnicodeError as e:
			raise AwlSimError("Failed to decode '%s' source code "
				"bytes to text." % (
				self.name))

	@classmethod
	def _compatReEncode(cls, sourceBytes, fromEncoding, toEncoding):
		"""Re-encode the sourceBytes from 'fromEncoding' to 'toEncoding'.
		"""
		try:
			if fromEncoding != toEncoding:
				sourceString = sourceBytes.decode(fromEncoding, "ignore")
				sourceBytes = sourceString.encode(toEncoding, "ignore")
		except UnicodeError as e:
			if isMicroPython:
				for b, c in dictItems(cls.latin1Trans):
					sourceBytes = sourceBytes.replace(b, c.encode(toEncoding))
			else:
				raise AwlSimError("Failed to re-encode source code "
					"from %s to %s." % (fromEncoding, toEncoding))
		return sourceBytes

	@property
	def identHash(self):
		identHash = self.__identHash
		if not identHash:
			# Calculate the ident hash
			bd = deque()
			bd.append(self.SRCTYPE.encode(self.ENCODING, "strict"))
			if self.name is None:
				bd.append(b'0')
			else:
				bd.append(b'1')
				bd.append(self.name.encode(self.ENCODING, "ignore"))
			bd.append(b'1' if self.enabled else b'0')
			bd.append(self.sourceBytes)
			identHash = self.__identHash = self.IDENT_HASH(b'|'.join(bd)).digest()
		return identHash

	@identHash.setter
	def identHash(self, identHash):
		# Force the ident hash.
		self.__identHash = identHash
		self.__identHashForced = True

	@property
	def identHashStr(self):
		return bytesToHexStr(self.identHash)

	def isFileBacked(self):
		return bool(self.filepath)

	def writeFileBacking(self, compatReEncode=False):
		"""Write the backing file, if any.
		"""
		if not self.isFileBacked():
			return
		sourceBytes = self.sourceBytes
		if compatReEncode:
			sourceBytes = self._compatReEncode(sourceBytes,
							   self.ENCODING,
							   self.COMPAT_ENCODING)
		safeFileWrite(self.filepath, sourceBytes)

	def forceNonFileBacked(self, newName):
		"Convert this source to a non-file-backed source."
		if self.isFileBacked():
			self.filepath = ""
			self.name = newName

	def readFromFile(self, filepath, compatReEncode=False):
		try:
			data = safeFileRead(filepath)
			if compatReEncode:
				data = self._compatReEncode(data,
							    self.COMPAT_ENCODING,
							    self.ENCODING)
		except AwlSimError as e:
			raise AwlSimError("Project: Could not read %s "
				"source file '%s':\n%s" %\
				(self.SRCTYPE, filepath, str(e)))
		self.sourceBytes = data
		self.filepath = filepath

	@classmethod
	def fromFile(cls, name, filepath, compatReEncode=False):
		source = cls(name=name,
			     filepath=filepath,
			     sourceBytes=b"")
		source.readFromFile(filepath, compatReEncode)
		return source

	@classmethod
	def fromBytes(cls, name, sourceBytes, compatReEncode=False):
		source = cls(name=name)
		if compatReEncode:
			sourceBytes = cls._compatReEncode(sourceBytes,
							  cls.COMPAT_ENCODING,
							  cls.ENCODING)
		source.sourceBytes = sourceBytes
		return source

	@classmethod
	def fromBase64(cls, name, b64):
		try:
			data = base64.b64decode(b64.encode("ascii"))
		except (TypeError, binascii.Error, UnicodeError) as e:
			raise AwlSimError("Project: %s source '%s' "
				"has invalid base64 encoding." %\
				(cls.SRCTYPE, name))
		return cls(name=name,
			   filepath=None,
			   sourceBytes=data)

	def dup(self):
		"""Duplicate this source. Returns a copy.
		"""
		new = self.__class__(name=self.name,
				     enabled=self.enabled,
				     filepath=self.filepath,
				     sourceBytes=self.sourceBytes[:],
				     userData=self.userData,
				     volatile=self.volatile)
		if self.__identHashForced:
			# identHash has been forced. Copy that, too.
			new.identHash = self.identHash
		return new

	def copyFrom(self, other,
		     copyName=True,
		     copyEnabled=True,
		     copyFilepath=True,
		     copySourceBytes=True,
		     copyUserData=True,
		     updateUserData=False,
		     copyVolatile=True):
		"""Copy the content of another source into this one.
		"""
		if copyName:
			self.name = other.name
		if copyEnabled:
			self.enabled = other.enabled
		if copyFilepath:
			self.filepath = other.filepath
		if copySourceBytes:
			self.sourceBytes = other.sourceBytes[:]
		if copyUserData:
			self.userData = other.userData.copy()
		if updateUserData:
			self.userData.update(other.userData)
		if copyVolatile:
			self.volatile = other.volatile

	def __eq__(self, other):
		return self.identHash == other.identHash

	def __ne__(self, other):
		return not self.__eq__(other)

	def __repr__(self):
		return "%s%s %s%s%s %s" % (
			self.SRCTYPE,
			"" if self.isFileBacked() else " project",
			self.name,
			"" if self.enabled else " (DISABLED)",
			" (VOLATILE)" if self.volatile else "",
			self.identHashStr)

class AwlSource(GenericSource):
	SRCTYPE		= "AWL/STL"
	SRCTYPE_ID	= 0 # .awlpro file format ID
	ENCODING	= XmlFactory.XML_ENCODING
	COMPAT_ENCODING	= "latin_1"
	STRIP_DATA	= False
	DOS_EOL		= True

class FupSource(GenericSource):
	SRCTYPE		= "FUP/FBD"
	SRCTYPE_ID	= 1 # .awlpro file format ID
	ENCODING	= XmlFactory.XML_ENCODING
	COMPAT_ENCODING	= ENCODING
	STRIP_DATA	= True
	DOS_EOL		= False

class KopSource(GenericSource):
	SRCTYPE		= "KOP/LAD"
	SRCTYPE_ID	= 2 # .awlpro file format ID
	ENCODING	= XmlFactory.XML_ENCODING
	COMPAT_ENCODING	= ENCODING
	STRIP_DATA	= True
	DOS_EOL		= False

class SymTabSource(GenericSource):
	SRCTYPE		= "symbol table"
	SRCTYPE_ID	= 3 # .awlpro file format ID
	ENCODING	= XmlFactory.XML_ENCODING
	COMPAT_ENCODING	= "latin_1"
	STRIP_DATA	= False
	DOS_EOL		= True

class SourceManager(ObjRefManager):
	"""Manages one source."""

	__slots__ = (
		"source",
		"container",
	)

	def __init__(self, source, container=None):
		"""source -> An AwlSource or SymTabSource instance.
		container -> A SourceContainer instance or None.
		"""
		def makeName(slf):
			if not slf.source:
				return "SourceManager"
			return "%s/%s" % (slf.source.name,
					  slf.source.identHashStr)
		super(SourceManager, self).__init__(name=makeName)

		self.source = source
		self.container = container
		if container:
			container.addManager(self)

	def removeFromContainer(self):
		"""Remove this source from the SourceContainer,
		if it is inserted into one.
		"""
		if self.container:
			self.container.removeManager(self)
		self.container = None

	def allRefsDestroyed(self):
		"""Called, if all source references are destroyed.
		"""
		super(SourceManager, self).allRefsDestroyed()
		self.removeFromContainer()
		self.source = None

	def getCodeBlocks(self):
		"""Get all compiled CodeBlock()s that were created from the
		source managed here.
		"""
		from awlsim.core.blocks import CodeBlock #@nocy
		return { ref.obj for ref in self.refs
			 if isinstance(ref.obj, CodeBlock) }

	def getDataBlocks(self):
		"""Get all compiled DB()s that were created from the
		source managed here.
		"""
		from awlsim.core.datablocks import DB #@nocy
		return { ref.obj for ref in self.refs
			 if isinstance(ref.obj, DB) }

	def getRelatedSourceManagers(self):
		"""Get all related source managers (e.g. sources created from sources).
		"""
		return { ref.obj for ref in self.refs
			 if isinstance(ref.obj, self.__class__) }

class SourceContainer(object):
	"""Container for source managers."""

	__slots__ = (
		"__sourceManagers",
	)

	def __init__(self):
		self.__sourceManagers = []

	def addManager(self, sourceManager):
		"""Add a SourceManager instance to this container.
		"""
		self.__sourceManagers.append(sourceManager)
		sourceManager.container = self

	def removeManager(self, sourceManager):
		"""Remove a SourceManager instance from this container.
		"""
		try:
			self.__sourceManagers.remove(sourceManager)
		except ValueError as e:
			# The removed manager did not exist.
			# This might happen in rare conditions, for example if a
			# previous download/translation attempt failed.
			# Just ignore this.
			pass

	def clear(self):
		"""Remove all managers from the container.
		"""
		for sourceManager in self.__sourceManagers[:]:
			self.removeManager(sourceManager)

	def getSourceManagers(self):
		"""Return a list of source managers in this container.
		"""
		return self.__sourceManagers

	def getSources(self):
		"""Return a list of sources in this container.
		"""
		return [ m.source for m in self.getSourceManagers() ]

	def getSourceManagerByIdent(self, identHash):
		"""Get the source manager by source ident hash.
		Returns None, if no such source was found.
		"""
		for sourceManager in self.__sourceManagers:
			if sourceManager.source.identHash == identHash:
				return sourceManager
		return None

	def getSourceByIdent(self, identHash):
		"""Get the source by source ident hash.
		Returns None, if no such source was found.
		"""
		sourceManager = self.getSourceManagerByIdent(identHash)
		return sourceManager.source if sourceManager else None
