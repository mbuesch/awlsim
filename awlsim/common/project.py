# -*- coding: utf-8 -*-
#
# AWL simulator - project
#
# Copyright 2014-2015 Michael Buesch <m@bues.ch>
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
from awlsim.common.util import *

from awlsim.library.libselection import *

import base64, binascii
import datetime
import os
import hashlib

if isPy2Compat:
	from ConfigParser import SafeConfigParser as _ConfigParser
	from ConfigParser import Error as _ConfigParserError
else:
	from configparser import ConfigParser as _ConfigParser
	from configparser import Error as _ConfigParserError


class GenericSource(object):
	SRCTYPE		= "<generic>"
	IDENT_HASH	= "sha256"

	def __init__(self, name="", filepath="", sourceBytes=b""):
		self.name = name
		self.filepath = filepath
		self.sourceBytes = sourceBytes
		self.__identHash = None

	@property
	def name(self):
		return self.__name

	@name.setter
	def name(self, newName):
		self.__name = newName
		self.__identHash = None

	@property
	def filepath(self):
		return self.__filepath

	@filepath.setter
	def filepath(self, newFilepath):
		self.__filepath = newFilepath
		self.__identHash = None

	@property
	def sourceBytes(self):
		return self.__sourceBytes

	@sourceBytes.setter
	def sourceBytes(self, newSourceBytes):
		self.__sourceBytes = newSourceBytes
		self.__identHash = None

	@property
	def identHash(self):
		if not self.__identHash:
			# Calculate the ident hash
			h = hashlib.new(self.IDENT_HASH, self.SRCTYPE.encode("utf-8"))
			if self.name is not None:
				h.update(self.name.encode("utf-8"))
			if self.filepath is not None:
				h.update(self.filepath.encode("utf-8"))
			h.update(self.sourceBytes)
			self.__identHash = h.digest()
		return self.__identHash

	@identHash.setter
	def identHash(self, identHash):
		# Force the ident hash.
		self.__identHash = identHash

	@property
	def identHashStr(self):
		return binascii.b2a_hex(self.identHash).decode("ascii")

	def dup(self):
		raise NotImplementedError

	def isFileBacked(self):
		return bool(self.filepath)

	def writeFileBacking(self):
		"Write the backing file, if any."
		if not self.isFileBacked():
			return
		awlFileWrite(self.filepath, self.sourceBytes, encoding="binary")

	def forceNonFileBacked(self, newName):
		"Convert this source to a non-file-backed source."
		if self.isFileBacked():
			self.filepath = ""
			self.name = newName

	def toBase64(self):
		return base64.b64encode(self.sourceBytes).decode("ascii")

	@classmethod
	def fromFile(cls, name, filepath):
		try:
			data = awlFileRead(filepath, encoding="binary")
		except AwlSimError as e:
			raise AwlSimError("Project: Could not read %s "
				"source file '%s':\n%s" %\
				(cls.SRCTYPE, filepath, str(e)))
		return cls(name, filepath, data)

	@classmethod
	def fromBase64(cls, name, b64):
		try:
			data = base64.b64decode(b64.encode("ascii"))
		except (TypeError, binascii.Error, UnicodeError) as e:
			raise AwlSimError("Project: %s source '%s' "
				"has invalid base64 encoding." %\
				(cls.SRCTYPE, name))
		return cls(name, None, data)

	def __repr__(self):
		return "%s%s %s %s" % ("" if self.isFileBacked() else "project ",
				    self.SRCTYPE, self.name, self.identHashStr)

class AwlSource(GenericSource):
	SRCTYPE = "AWL/STL"

	def dup(self):
		return AwlSource(self.name, self.filepath,
				 self.sourceBytes[:])

class SymTabSource(GenericSource):
	SRCTYPE = "symbol table"

	def dup(self):
		return SymTabSource(self.name, self.filepath,
				    self.sourceBytes[:])

class HwmodDescriptor(object):
	"""Hardware module descriptor."""

	def __init__(self, moduleName, parameters = None):
		self.setModuleName(moduleName)
		self.setParameters(parameters)

	def dup(self):
		return HwmodDescriptor(self.getModuleName(),
				       dict(self.getParameters()))

	def setModuleName(self, moduleName):
		self.moduleName = moduleName

	def getModuleName(self):
		return self.moduleName

	def setParameters(self, parameters):
		if not parameters:
			parameters = {}
		self.parameters = parameters

	def addParameter(self, name, value):
		self.setParameterValue(name, value)

	def setParameterValue(self, name, value):
		self.parameters[name] = value

	def removeParameter(self, name):
		self.parameters.pop(name, None)

	def getParameters(self):
		return self.parameters

	def getParameter(self, name):
		return self.parameters.get(name)

class GuiSettings(object):
	def __init__(self,
		     editorAutoIndentEn=True,
		     editorPasteIndentEn=True,
		     editorValidationEn=True,
		     editorFont=""):
		self.setEditorAutoIndentEn(editorAutoIndentEn)
		self.setEditorPasteIndentEn(editorPasteIndentEn)
		self.setEditorValidationEn(editorValidationEn)
		self.setEditorFont(editorFont)

	def setEditorAutoIndentEn(self, editorAutoIndentEn):
		self.editorAutoIndentEn = editorAutoIndentEn

	def getEditorAutoIndentEn(self):
		return self.editorAutoIndentEn

	def setEditorPasteIndentEn(self, editorPasteIndentEn):
		self.editorPasteIndentEn = editorPasteIndentEn

	def getEditorPasteIndentEn(self):
		return self.editorPasteIndentEn

	def setEditorValidationEn(self, editorValidationEn):
		self.editorValidationEn = editorValidationEn

	def getEditorValidationEn(self):
		return self.editorValidationEn

	def setEditorFont(self, editorFont):
		self.editorFont = editorFont

	def getEditorFont(self):
		return self.editorFont

class CoreLinkSettings(object):
	DEFAULT_INTERPRETERS = "pypy3; pypy; $CURRENT; python3; python2; python; py"
	SPAWN_PORT_BASE = 4151 + 32

	def __init__(self,
		     spawnLocalEn=True,
		     spawnLocalPortRange=range(SPAWN_PORT_BASE,
					       SPAWN_PORT_BASE + 4095 + 1),
		     spawnLocalInterpreters="$DEFAULT",
		     connectHost="localhost",
		     connectPort=4151,
		     connectTimeoutMs=3000):
		self.setSpawnLocalEn(spawnLocalEn)
		self.setSpawnLocalPortRange(spawnLocalPortRange)
		self.setSpawnLocalInterpreters(spawnLocalInterpreters),
		self.setConnectHost(connectHost)
		self.setConnectPort(connectPort)
		self.setConnectTimeoutMs(connectTimeoutMs)

	def setSpawnLocalEn(self, spawnLocalEn):
		self.spawnLocalEn = spawnLocalEn

	def getSpawnLocalEn(self):
		return self.spawnLocalEn

	def setSpawnLocalPortRange(self, spawnLocalPortRange):
		self.spawnLocalPortRange = spawnLocalPortRange

	def getSpawnLocalPortRange(self):
		return self.spawnLocalPortRange

	def setSpawnLocalInterpreters(self, spawnLocalInterpreters):
		self.spawnLocalInterpreters = spawnLocalInterpreters

	def getSpawnLocalInterpreters(self):
		return self.spawnLocalInterpreters

	def __expandInterpStr(self, interpStr):
		ret = []
		for inter in interpStr.split(';'):
			if inter.strip() == "$DEFAULT":
				inter = self.__expandInterpStr(self.DEFAULT_INTERPRETERS)
			elif inter.strip() == "$CURRENT":
				inter = sys.executable
			ret.append(inter)
		return ";".join(ret)

	def getSpawnLocalInterpreterList(self, replace=True):
		interpStr = self.getSpawnLocalInterpreters()
		if replace:
			interpStr = self.__expandInterpStr(interpStr)
		return [ i.strip() for i in interpStr.split(';') ]

	def setConnectHost(self, connectHost):
		self.connectHost = connectHost

	def getConnectHost(self):
		return self.connectHost

	def setConnectPort(self, connectPort):
		self.connectPort = connectPort

	def getConnectPort(self):
		return self.connectPort

	def setConnectTimeoutMs(self, connectTimeoutMs):
		self.connectTimeoutMs = connectTimeoutMs

	def getConnectTimeoutMs(self):
		return self.connectTimeoutMs

class HwmodSettings(object):
	def __init__(self,
		     loadedModules=None):
		self.setLoadedModules(loadedModules)

	def setLoadedModules(self, loadedModules):
		if not loadedModules:
			loadedModules = []
		self.loadedModules = loadedModules

	def addLoadedModule(self, modDesc):
		self.loadedModules.append(modDesc)

	def getLoadedModules(self):
		return self.loadedModules

class Project(object):
	DATETIME_FMT	= "%Y-%m-%d %H:%M:%S.%f"

	def __init__(self, projectFile,
		     createDate=None,
		     modifyDate=None,
		     awlSources=[],
		     symTabSources=[],
		     libSelections=[],
		     cpuSpecs=None,
		     obTempPresetsEn=False,
		     extInsnsEn=False,
		     guiSettings=None,
		     coreLinkSettings=None,
		     hwmodSettings=None):
		self.setProjectFile(projectFile)
		self.setCreateDate(createDate)
		self.setModifyDate(modifyDate)
		self.setAwlSources(awlSources)
		self.setSymTabSources(symTabSources)
		self.setLibSelections(libSelections)
		if not cpuSpecs:
			cpuSpecs = S7CPUSpecs()
		self.setCpuSpecs(cpuSpecs)
		self.setObTempPresetsEn(obTempPresetsEn)
		self.setExtInsnsEn(extInsnsEn)
		if not guiSettings:
			guiSettings = GuiSettings()
		self.setGuiSettings(guiSettings)
		if not coreLinkSettings:
			coreLinkSettings = CoreLinkSettings()
		self.setCoreLinkSettings(coreLinkSettings)
		if not hwmodSettings:
			hwmodSettings = HwmodSettings()
		self.setHwmodSettings(hwmodSettings)

	def setProjectFile(self, filename):
		self.projectFile = filename

	def getProjectFile(self):
		return self.projectFile

	def setCreateDate(self, createDate):
		if createDate is None:
			createDate = datetime.datetime.utcnow()
		self.createDate = createDate

	def getCreateDate(self):
		return self.createDate

	def setModifyDate(self, modifyDate):
		if modifyDate is None:
			modifyDate = self.getCreateDate()
		if modifyDate is None:
			modifyDate = datetime.datetime.utcnow()
		self.modifyDate = modifyDate

	def getModifyDate(self):
		return self.modifyDate

	def setAwlSources(self, awlSources):
		self.awlSources = awlSources

	def getAwlSources(self):
		return self.awlSources

	def setSymTabSources(self, symTabSources):
		self.symTabSources = symTabSources

	def getSymTabSources(self):
		return self.symTabSources

	def setLibSelections(self, libSelections):
		self.libSelections = libSelections

	def getLibSelections(self):
		return self.libSelections

	def setCpuSpecs(self, cpuSpecs):
		self.cpuSpecs = cpuSpecs

	def getCpuSpecs(self):
		return self.cpuSpecs

	def setObTempPresetsEn(self, obTempPresetsEn):
		self.obTempPresetsEn = obTempPresetsEn

	def getObTempPresetsEn(self):
		return self.obTempPresetsEn

	def setExtInsnsEn(self, extInsnsEn):
		self.extInsnsEn = extInsnsEn

	def getExtInsnsEn(self):
		return self.extInsnsEn

	def setGuiSettings(self, guiSettings):
		self.guiSettings = guiSettings

	def getGuiSettings(self):
		return self.guiSettings

	def setCoreLinkSettings(self, coreLinkSettings):
		self.coreLinkSettings = coreLinkSettings

	def getCoreLinkSettings(self):
		return self.coreLinkSettings

	def setHwmodSettings(self, hwmodSettings):
		self.hwmodSettings = hwmodSettings

	def getHwmodSettings(self):
		return self.hwmodSettings

	@classmethod
	def dataIsProject(cls, data):
		magic = b"[AWLSIM_PROJECT]"
		if isIronPython and isinstance(data, str):
			try:
				"a".startswith(b"a") # Test for ipy byte conversion bug
			except TypeError:
				# XXX: Workaround for IronPython byte conversion bug
				printInfo("Applying workaround for IronPython byte conversion bug")
				magic = magic.decode("UTF-8")
		return data.lstrip().startswith(magic)

	@classmethod
	def fileIsProject(cls, filename):
		return cls.dataIsProject(awlFileRead(filename, encoding="binary"))

	@classmethod
	def fromText(cls, text, projectFile):
		if not cls.dataIsProject(text.encode("utf-8")):
			raise AwlSimError("Project file: The data is "\
				"not an awlsim project.")
		projectDir = os.path.dirname(projectFile)
		createDate = None
		modifyDate = None
		awlSources = []
		symTabSources = []
		libSelections = []
		cpuSpecs = S7CPUSpecs()
		obTempPresetsEn = False
		extInsnsEn = False
		guiSettings = GuiSettings()
		linkSettings = CoreLinkSettings()
		hwmodSettings = HwmodSettings()
		try:
			p = _ConfigParser()
			p.readfp(StringIO(text), projectFile)

			# AWLSIM_PROJECT section
			version = p.getint("AWLSIM_PROJECT", "file_version")
			expectedVersion = 0
			if version != expectedVersion:
				raise AwlSimError("Project file: Unsupported version. "\
					"File version is %d, but expected %d." %\
					(version, expectedVersion))
			if p.has_option("AWLSIM_PROJECT", "date"):
				# Compatibility only. "date" is deprecated.
				dStr = p.get("AWLSIM_PROJECT", "date")
				createDate = datetime.datetime.strptime(dStr,
							cls.DATETIME_FMT)
				modifyDate = createDate
			if p.has_option("AWLSIM_PROJECT", "create_date"):
				dStr = p.get("AWLSIM_PROJECT", "create_date")
				createDate = datetime.datetime.strptime(dStr,
							cls.DATETIME_FMT)
			if p.has_option("AWLSIM_PROJECT", "modify_date"):
				dStr = p.get("AWLSIM_PROJECT", "modify_date")
				modifyDate = datetime.datetime.strptime(dStr,
							cls.DATETIME_FMT)

			# CPU section
			for i in range(0xFFFF):
				option = "awl_file_%d" % i
				if not p.has_option("CPU", option):
					break
				path = p.get("CPU", option)
				src = AwlSource.fromFile(path, cls.__generic2path(path, projectDir))
				awlSources.append(src)
			for i in range(0xFFFF):
				srcOption = "awl_%d" % i
				nameOption = "awl_name_%d" % i
				if not p.has_option("CPU", srcOption):
					break
				awlBase64 = p.get("CPU", srcOption)
				name = None
				if p.has_option("CPU", nameOption):
					try:
						name = base64ToStr(p.get("CPU", nameOption))
					except ValueError as e:
						pass
				if name is None:
					name = "AWL/STL #%d" % i
				src = AwlSource.fromBase64(name, awlBase64)
				awlSources.append(src)
			if p.has_option("CPU", "mnemonics"):
				mnemonics = p.getint("CPU", "mnemonics")
				cpuSpecs.setConfiguredMnemonics(mnemonics)
			if p.has_option("CPU", "nr_accus"):
				nrAccus = p.getint("CPU", "nr_accus")
				cpuSpecs.setNrAccus(nrAccus)
			if p.has_option("CPU", "clock_memory_byte"):
				clockMemByte = p.getint("CPU", "clock_memory_byte")
				cpuSpecs.setClockMemByte(clockMemByte)
			if p.has_option("CPU", "ob_startinfo_enable"):
				obTempPresetsEn = p.getboolean("CPU", "ob_startinfo_enable")
			if p.has_option("CPU", "ext_insns_enable"):
				extInsnsEn = p.getboolean("CPU", "ext_insns_enable")

			# SYMBOLS section
			for i in range(0xFFFF):
				option = "sym_tab_file_%d" % i
				if not p.has_option("SYMBOLS", option):
					break
				path = p.get("SYMBOLS", option)
				src = SymTabSource.fromFile(path, cls.__generic2path(path, projectDir))
				symTabSources.append(src)
			for i in range(0xFFFF):
				srcOption = "sym_tab_%d" % i
				nameOption = "sym_tab_name_%d" % i
				if not p.has_option("SYMBOLS", srcOption):
					break
				symTabBase64 = p.get("SYMBOLS", srcOption)
				name = None
				if p.has_option("SYMBOLS", nameOption):
					try:
						name = base64ToStr(p.get("SYMBOLS", nameOption))
					except ValueError as e:
						pass
				if name is None:
					name = "Symbol table #%d" % i
				src = SymTabSource.fromBase64(name, symTabBase64)
				symTabSources.append(src)

			# LIBS section
			for i in range(0xFFFF):
				nameOption = "lib_name_%d" % i
				blockOption = "lib_block_%d" % i
				effOption = "lib_block_effective_%d" % i
				if not p.has_option("LIBS", nameOption):
					break
				try:
					libName = base64ToStr(p.get("LIBS", nameOption))
				except ValueError as e:
					continue
				block = p.get("LIBS", blockOption).upper().strip()
				effBlock = p.getint("LIBS", effOption)
				try:
					if block.startswith("FC"):
						entryType = AwlLibEntrySelection.TYPE_FC
						entryIndex = int(block[2:].strip())
					elif block.startswith("FB"):
						entryType = AwlLibEntrySelection.TYPE_FB
						entryIndex = int(block[2:].strip())
					elif block.startswith("UNKNOWN"):
						entryType = AwlLibEntrySelection.TYPE_UNKNOWN
						entryIndex = int(block[7:].strip())
					else:
						raise ValueError
					if entryIndex < -1 or entryIndex > 0xFFFF:
						raise ValueError
				except ValueError:
					raise AwlSimError("Project file: Invalid "
						"library block: %s" % block)
				libSelections.append(
					AwlLibEntrySelection(libName = libName,
							     entryType = entryType,
							     entryIndex = entryIndex,
							     effectiveEntryIndex = effBlock)
				)

			# CORE_LINK section
			if p.has_option("CORE_LINK", "spawn_local"):
				linkSettings.setSpawnLocalEn(
					p.getboolean("CORE_LINK", "spawn_local"))
			if p.has_option("CORE_LINK", "spawn_local_port_range"):
				pRange = p.get("CORE_LINK", "spawn_local_port_range")
				try:
					pRange = pRange.split(":")
					begin = int(pRange[0])
					end = int(pRange[1])
					if end < begin:
						raise ValueError
					pRange = range(begin, end + 1)
				except (IndexError, ValueError) as e:
					raise AwlSimError("Project file: Invalid port range")
				linkSettings.setSpawnLocalPortRange(pRange)
			if p.has_option("CORE_LINK", "spawn_local_interpreters"):
				interp = p.get("CORE_LINK", "spawn_local_interpreters")
				try:
					interp = base64ToStr(interp)
				except ValueError as e:
					raise AwlSimError("Project file: "
						"Invalid interpreter list")
				linkSettings.setSpawnLocalInterpreters(interp)
			if p.has_option("CORE_LINK", "connect_host"):
				host = p.get("CORE_LINK", "connect_host")
				try:
					host = base64ToStr(host)
				except ValueError as e:
					raise AwlSimError("Project file: "
						"Invalid host name")
				linkSettings.setConnectHost(host)
			if p.has_option("CORE_LINK", "connect_port"):
				port = p.getint("CORE_LINK", "connect_port")
				linkSettings.setConnectPort(port)
			if p.has_option("CORE_LINK", "connect_timeout_ms"):
				timeout = p.getint("CORE_LINK", "connect_timeout_ms")
				linkSettings.setConnectTimeoutMs(timeout)

			# HWMODS section
			for i in range(0xFFFF):
				nameOption = "loaded_mod_%d" % i
				if not p.has_option("HWMODS", nameOption):
					break
				modName = base64ToStr(p.get("HWMODS", nameOption))
				modDesc = HwmodDescriptor(modName)
				for j in range(0x3FF):
					paramOption = "loaded_mod_%d_p%d" % (i, j)
					if not p.has_option("HWMODS", paramOption):
						break
					param = p.get("HWMODS", paramOption)
					try:
						param = param.split(":")
						if len(param) != 2:
							raise ValueError
						paramName = base64ToStr(param[0])
						if param[1].strip():
							paramValue = base64ToStr(param[1])
						else:
							paramValue = None
					except ValueError:
						raise AwlSimError("Project file: "
							"Invalid hw mod parameter")
					modDesc.addParameter(paramName, paramValue)
				hwmodSettings.addLoadedModule(modDesc)

			# GUI section
			if p.has_option("GUI", "editor_autoindent"):
				guiSettings.setEditorAutoIndentEn(
					p.getboolean("GUI", "editor_autoindent"))
			if p.has_option("GUI", "editor_paste_autoindent"):
				guiSettings.setEditorPasteIndentEn(
					p.getboolean("GUI", "editor_paste_autoindent"))
			if p.has_option("GUI", "editor_validation"):
				guiSettings.setEditorValidationEn(
					p.getboolean("GUI", "editor_validation"))
			if p.has_option("GUI", "editor_font"):
				guiSettings.setEditorFont(p.get("GUI", "editor_font").strip())

		except _ConfigParserError as e:
			raise AwlSimError("Project parser error: " + str(e))

		return cls(projectFile = projectFile,
			   createDate = createDate,
			   modifyDate = modifyDate,
			   awlSources = awlSources,
			   symTabSources = symTabSources,
			   libSelections = libSelections,
			   cpuSpecs = cpuSpecs,
			   obTempPresetsEn = obTempPresetsEn,
			   extInsnsEn = extInsnsEn,
			   guiSettings = guiSettings,
			   coreLinkSettings = linkSettings,
			   hwmodSettings = hwmodSettings)

	@classmethod
	def fromFile(cls, filename):
		return cls.fromText(awlFileRead(filename, encoding="utf8"), filename)

	@classmethod
	def fromProjectOrRawAwlFile(cls, filename):
		"""Read a project (.awlpro) or raw AWL file (.awl)
		and return a Project()."""

		if Project.fileIsProject(filename):
			project = Project.fromFile(filename)
		else:
			# Make a fake project
			awlSrc = AwlSource.fromFile(name = filename,
						    filepath = filename)
			project = Project(projectFile = None,
					  awlSources = [ awlSrc, ])
		return project

	@classmethod
	def __path2generic(cls, path, relativeToDir):
		"""Generate an OS-independent string from a path."""
		if "\r" in path or "\n" in path:
			# The project file format cannot handle these
			raise AwlSimError("Project file: Path '%s' contains invalid "\
				"characters (line breaks)." % path)
		path = os.path.relpath(path, relativeToDir)
		if os.path.splitdrive(path)[0]:
			raise AwlSimError("Project file: Failed to strip drive letter. "\
				"Please make sure the project file, AWL code files and "\
				"symbol tables files all reside on the same drive.")
		path = path.replace(os.path.sep, "/")
		return path

	@classmethod
	def __generic2path(cls, path, relativeToDir):
		"""Generate a path from an OS-independent string."""
		path = path.replace("/", os.path.sep)
		path = os.path.join(relativeToDir, path)
		return path

	def toText(self, projectFile=None):
		if not projectFile:
			projectFile = self.projectFile
		projectDir = os.path.dirname(projectFile)

		self.setModifyDate(datetime.datetime.utcnow())

		lines = []
		lines.append("[AWLSIM_PROJECT]")
		lines.append("file_version=0")
		lines.append("create_date=%s" %\
			     self.getCreateDate().strftime(self.DATETIME_FMT))
		lines.append("modify_date=%s" %\
			     self.getModifyDate().strftime(self.DATETIME_FMT))
		lines.append("")

		lines.append("[CPU]")
		fileBackedSources = (src for src in self.awlSources if src.isFileBacked())
		embeddedSources = (src for src in self.awlSources if not src.isFileBacked())
		for i, awlSrc in enumerate(fileBackedSources):
			path = self.__path2generic(awlSrc.filepath, projectDir)
			lines.append("awl_file_%d=%s" % (i, path))
		for i, awlSrc in enumerate(embeddedSources):
			lines.append("awl_%d=%s" % (i, awlSrc.toBase64()))
			name = strToBase64(awlSrc.name, ignoreErrors=True)
			lines.append("awl_name_%d=%s" % (i, name))
		lines.append("mnemonics=%d" % self.cpuSpecs.getConfiguredMnemonics())
		lines.append("nr_accus=%d" % self.cpuSpecs.nrAccus)
		lines.append("clock_memory_byte=%d" % self.cpuSpecs.clockMemByte)
		lines.append("ob_startinfo_enable=%d" % int(bool(self.obTempPresetsEn)))
		lines.append("ext_insns_enable=%d" % int(bool(self.extInsnsEn)))
		lines.append("")

		lines.append("[SYMBOLS]")
		fileBackedSources = (src for src in self.symTabSources if src.isFileBacked())
		embeddedSources = (src for src in self.symTabSources if not src.isFileBacked())
		for i, symSrc in enumerate(fileBackedSources):
			path = self.__path2generic(symSrc.filepath, projectDir)
			lines.append("sym_tab_file_%d=%s" % (i, path))
		for i, symSrc in enumerate(embeddedSources):
			lines.append("sym_tab_%d=%s" % (i, symSrc.toBase64()))
			name = strToBase64(symSrc.name, ignoreErrors=True)
			lines.append("sym_tab_name_%d=%s" % (i, name))
		lines.append("")

		lines.append("[LIBS]")
		for i, libSel in enumerate(self.libSelections):
			libName = strToBase64(libSel.getLibName(), ignoreErrors=True)
			lines.append("lib_name_%d=%s" % (i, libName))
			lines.append("lib_block_%d=%s %d" % (
				i, libSel.getEntryTypeStr(),
				libSel.getEntryIndex()))
			lines.append("lib_block_effective_%d=%d" % (
				i, libSel.getEffectiveEntryIndex()))
		lines.append("")

		lines.append("[CORE_LINK]")
		linkSettings = self.getCoreLinkSettings()
		lines.append("spawn_local=%d" %\
			     int(bool(linkSettings.getSpawnLocalEn())))
		lines.append("spawn_local_port_range=%d:%d" %(\
			     linkSettings.getSpawnLocalPortRange()[0],
			     linkSettings.getSpawnLocalPortRange()[-1]))
		interp = linkSettings.getSpawnLocalInterpreters()
		interp = strToBase64(interp, ignoreErrors=True)
		lines.append("spawn_local_interpreters=%s" % interp)
		host = linkSettings.getConnectHost()
		host = strToBase64(host, ignoreErrors=True)
		lines.append("connect_host=%s" % host)
		lines.append("connect_port=%d" %\
			     int(linkSettings.getConnectPort()))
		lines.append("connect_timeout_ms=%d" %\
			     int(linkSettings.getConnectTimeoutMs()))
		lines.append("")

		lines.append("[HWMODS]")
		hwSettings = self.getHwmodSettings()
		loadedMods = sorted(hwSettings.getLoadedModules(),
				    key = lambda modDesc: modDesc.getModuleName())
		for modNr, modDesc in enumerate(loadedMods):
			modName = strToBase64(modDesc.getModuleName(),
					      ignoreErrors=True)
			lines.append("loaded_mod_%d=%s" % (modNr, modName))
			modParams = sorted(list(modDesc.getParameters().items()),
					   key = lambda p: p[0])
			for paramNr, param in enumerate(modParams):
				paramName, paramValue = param
				paramName = strToBase64(paramName,
							ignoreErrors=True)
				if paramValue is None:
					paramValue = ""
				else:
					paramValue = strToBase64(paramValue,
								 ignoreErrors=True)
				lines.append("loaded_mod_%d_p%d=%s:%s" %\
					(modNr, paramNr,
					 paramName, paramValue))
		lines.append("")

		lines.append("[GUI]")
		guiSettings = self.getGuiSettings()
		lines.append("editor_autoindent=%d" %\
			     int(bool(guiSettings.getEditorAutoIndentEn())))
		lines.append("editor_paste_autoindent=%d" %\
			     int(bool(guiSettings.getEditorPasteIndentEn())))
		lines.append("editor_validation=%d" %\
			     int(bool(guiSettings.getEditorValidationEn())))
		lines.append("editor_font=%s" % guiSettings.getEditorFont())
		lines.append("")

		return "\r\n".join(lines)

	def toFile(self, projectFile=None):
		if not projectFile:
			projectFile = self.projectFile
		if not projectFile:
			raise AwlSimError("Project file: Cannot generate project file. "
				"No file name specified.")
		text = self.toText(projectFile)
		awlFileWrite(projectFile, text, encoding="utf8")
		for awlSrc in self.awlSources:
			awlSrc.writeFileBacking()
		for symSrc in self.symTabSources:
			symSrc.writeFileBacking()
