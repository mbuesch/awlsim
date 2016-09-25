# -*- coding: utf-8 -*-
#
# AWL simulator - project
#
# Copyright 2014-2016 Michael Buesch <m@bues.ch>
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
from awlsim.common.sources import *
from awlsim.common.hwmod import *
from awlsim.common.util import *

from awlsim.library.libselection import *

import base64, binascii
import datetime
import os

if isPy2Compat:
	from ConfigParser import SafeConfigParser as _ConfigParser
	from ConfigParser import Error as _ConfigParserError
else:
	from configparser import ConfigParser as _ConfigParser
	from configparser import Error as _ConfigParserError


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
	DEFAULT_INTERPRETERS	= "pypy3; pypy; $CURRENT; python3; python2; python; py"
	SPAWN_PORT_BASE		= 4151 + 32

	TUNNEL_NONE		= 0
	TUNNEL_SSH		= 1

	TUNNEL_LOCPORT_AUTO	= -1

	def __init__(self,
		     spawnLocalEn=True,
		     spawnLocalPortRange=range(SPAWN_PORT_BASE,
					       SPAWN_PORT_BASE + 4095 + 1),
		     spawnLocalInterpreters="$DEFAULT",
		     connectHost="localhost",
		     connectPort=4151,
		     connectTimeoutMs=3000,
		     tunnel=TUNNEL_NONE,
		     tunnelLocalPort=TUNNEL_LOCPORT_AUTO,
		     sshUser="pi",
		     sshPort=22,
		     sshExecutable="ssh"):
		self.setSpawnLocalEn(spawnLocalEn)
		self.setSpawnLocalPortRange(spawnLocalPortRange)
		self.setSpawnLocalInterpreters(spawnLocalInterpreters),
		self.setConnectHost(connectHost)
		self.setConnectPort(connectPort)
		self.setConnectTimeoutMs(connectTimeoutMs)
		self.setTunnel(tunnel)
		self.setTunnelLocalPort(tunnelLocalPort)
		self.setSSHUser(sshUser)
		self.setSSHPort(sshPort)
		self.setSSHExecutable(sshExecutable)

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

	def setTunnel(self, tunnel):
		self.tunnel = tunnel

	def getTunnel(self):
		return self.tunnel

	def setTunnelLocalPort(self, tunnelLocalPort):
		self.tunnelLocalPort = tunnelLocalPort

	def getTunnelLocalPort(self):
		return self.tunnelLocalPort

	def setSSHUser(self, sshUser):
		self.sshUser = sshUser

	def getSSHUser(self):
		return self.sshUser

	def setSSHPort(self, sshPort):
		self.sshPort = sshPort

	def getSSHPort(self):
		return self.sshPort

	def setSSHExecutable(self, sshExecutable):
		self.sshExecutable = sshExecutable

	def getSSHExecutable(self):
		return self.sshExecutable

class HwmodSettings(object):
	def __init__(self,
		     loadedModules=None):
		self.setLoadedModules(loadedModules)

	def setLoadedModules(self, loadedModules):
		self.loadedModules = loadedModules or []

	def addLoadedModule(self, modDesc):
		self.loadedModules.append(modDesc)

	def getLoadedModules(self):
		return self.loadedModules

class Project(object):
	DATETIME_FMT	= "%Y-%m-%d %H:%M:%S.%f"

	def __init__(self, projectFile,
		     createDate=None,
		     modifyDate=None,
		     awlSources=None,
		     fupSources=None,
		     kopSources=None,
		     symTabSources=None,
		     libSelections=None,
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
		self.setFupSources(fupSources)
		self.setKopSources(kopSources)
		self.setSymTabSources(symTabSources)
		self.setLibSelections(libSelections)
		self.setCpuSpecs(cpuSpecs)
		self.setObTempPresetsEn(obTempPresetsEn)
		self.setExtInsnsEn(extInsnsEn)
		self.setGuiSettings(guiSettings)
		self.setCoreLinkSettings(coreLinkSettings)
		self.setHwmodSettings(hwmodSettings)

	def clear(self):
		self.setProjectFile(None)
		self.setCreateDate(None)
		self.setModifyDate(None)
		self.setAwlSources(None)
		self.setFupSources(None)
		self.setKopSources(None)
		self.setSymTabSources(None)
		self.setLibSelections(None)
		self.setCpuSpecs(None)
		self.setObTempPresetsEn(False)
		self.setExtInsnsEn(False)
		self.setGuiSettings(None)
		self.setCoreLinkSettings(None)
		self.setHwmodSettings(None)

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
		self.awlSources = awlSources or []

	def getAwlSources(self):
		return self.awlSources

	def setFupSources(self, fupSources):
		self.fupSources = fupSources or []

	def getFupSources(self):
		return self.fupSources

	def setKopSources(self, kopSources):
		self.kopSources = kopSources or []

	def getKopSources(self):
		return self.kopSources

	def setSymTabSources(self, symTabSources):
		self.symTabSources = symTabSources or []

	def getSymTabSources(self):
		return self.symTabSources

	def setLibSelections(self, libSelections):
		self.libSelections = libSelections or []

	def getLibSelections(self):
		return self.libSelections

	def setCpuSpecs(self, cpuSpecs):
		self.cpuSpecs = cpuSpecs or S7CPUSpecs()

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
		self.guiSettings = guiSettings or GuiSettings()

	def getGuiSettings(self):
		return self.guiSettings

	def setCoreLinkSettings(self, coreLinkSettings):
		self.coreLinkSettings = coreLinkSettings or CoreLinkSettings()

	def getCoreLinkSettings(self):
		return self.coreLinkSettings

	def setHwmodSettings(self, hwmodSettings):
		self.hwmodSettings = hwmodSettings or HwmodSettings()

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
		fupSources = []
		kopSources = []
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

			def getSrcs(srcList, section, prefix, SrcClass):
				for i in range(0xFFFF):
					option = "%s_file_%d" % (prefix, i)
					if not p.has_option(section, option):
						break
					path = p.get(section, option)
					src = SrcClass.fromFile(path,
						cls.__generic2path(path, projectDir))
					srcList.append(src)
				for i in range(0xFFFF):
					srcOption = "%s_%d" % (prefix, i)
					nameOption = "%s_name_%d" % (prefix, i)
					if not p.has_option(section, srcOption):
						break
					awlBase64 = p.get(section, srcOption)
					name = None
					if p.has_option(section, nameOption):
						with contextlib.suppress(ValueError):
							name = base64ToStr(
								p.get(section, nameOption))
					if name is None:
						name = "%s #%d" % (SrcClass.SRCTYPE, i)
					src = SrcClass.fromBase64(name, awlBase64)
					srcList.append(src)

			# CPU section
			getSrcs(awlSources, "CPU", "awl", AwlSource)
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

			# FUP section
			getSrcs(fupSources, "FUP", "fup", FupSource)

			# KOP section
			getSrcs(kopSources, "KOP", "kop", KopSource)

			# SYMBOLS section
			getSrcs(symTabSources, "SYMBOLS", "sym_tab", SymTabSource)

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
			if p.has_option("CORE_LINK", "tunnel"):
				tunnel = p.getint("CORE_LINK", "tunnel")
				linkSettings.setTunnel(tunnel)
			if p.has_option("CORE_LINK", "tunnel_local_port"):
				tunnelLocalPort = p.getint("CORE_LINK", "tunnel_local_port")
				linkSettings.setTunnelLocalPort(tunnelLocalPort)
			if p.has_option("CORE_LINK", "ssh_user"):
				sshUser = p.get("CORE_LINK", "ssh_user")
				try:
					sshUser = base64ToStr(sshUser)
				except ValueError as e:
					raise AwlSimError("Project file: "
						"Invalid ssh_user")
				linkSettings.setSSHUser(sshUser)
			if p.has_option("CORE_LINK", "ssh_port"):
				sshPort = p.getint("CORE_LINK", "ssh_port")
				linkSettings.setSSHPort(sshPort)
			if p.has_option("CORE_LINK", "ssh_executable"):
				sshExecutable = p.get("CORE_LINK", "ssh_executable")
				try:
					sshExecutable = base64ToStr(sshExecutable)
				except ValueError as e:
					raise AwlSimError("Project file: "
						"Invalid ssh_executable")
				linkSettings.setSSHExecutable(sshExecutable)

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
			   fupSources = fupSources,
			   kopSources = kopSources,
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

		def makeSrcs(prefix, srcList):
			fileBackedSources = (src for src in srcList if src.isFileBacked())
			embeddedSources = (src for src in srcList if not src.isFileBacked())
			for i, src in enumerate(fileBackedSources):
				path = self.__path2generic(src.filepath, projectDir)
				lines.append("%s_file_%d=%s" % (prefix, i, path))
			for i, src in enumerate(embeddedSources):
				lines.append("%s_%d=%s" % (prefix, i, src.toBase64()))
				name = strToBase64(src.name, ignoreErrors=True)
				lines.append("%s_name_%d=%s" % (prefix, i, name))

		lines.append("[CPU]")
		makeSrcs("awl", self.awlSources)
		lines.append("mnemonics=%d" % self.cpuSpecs.getConfiguredMnemonics())
		lines.append("nr_accus=%d" % self.cpuSpecs.nrAccus)
		lines.append("clock_memory_byte=%d" % self.cpuSpecs.clockMemByte)
		lines.append("ob_startinfo_enable=%d" % int(bool(self.obTempPresetsEn)))
		lines.append("ext_insns_enable=%d" % int(bool(self.extInsnsEn)))
		lines.append("")

		lines.append("[FUP]")
		makeSrcs("fup", self.fupSources)
		lines.append("")

		lines.append("[KOP]")
		makeSrcs("kop", self.kopSources)
		lines.append("")

		lines.append("[SYMBOLS]")
		makeSrcs("sym_tab", self.symTabSources)
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
		lines.append("tunnel=%d" % linkSettings.getTunnel())
		lines.append("tunnel_local_port=%d" %\
			     linkSettings.getTunnelLocalPort())
		sshUser = linkSettings.getSSHUser()
		sshUser = strToBase64(sshUser, ignoreErrors=True)
		lines.append("ssh_user=%s" % sshUser)
		lines.append("ssh_port=%d" % linkSettings.getSSHPort())
		sshExecutable = linkSettings.getSSHExecutable()
		sshExecutable = strToBase64(sshExecutable, ignoreErrors=True)
		lines.append("ssh_executable=%s" % sshExecutable)
		lines.append("")

		lines.append("[HWMODS]")
		hwSettings = self.getHwmodSettings()
		loadedMods = sorted(hwSettings.getLoadedModules(),
				    key = lambda modDesc: modDesc.getModuleName())
		for modNr, modDesc in enumerate(loadedMods):
			modName = strToBase64(modDesc.getModuleName(),
					      ignoreErrors=True)
			lines.append("loaded_mod_%d=%s" % (modNr, modName))
			modParams = sorted(dictItems(modDesc.getParameters()),
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

	def __repr__(self):
		if self.projectFile:
			return 'Project("%s")' % self.projectFile
		return "Project(None)"
