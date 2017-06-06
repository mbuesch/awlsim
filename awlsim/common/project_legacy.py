# -*- coding: utf-8 -*-
#
# AWL simulator - project V0 legacy format read support
#
# Copyright 2014-2017 Michael Buesch <m@bues.ch>
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
from awlsim.common.sources import *
from awlsim.common.hwmod import *
from awlsim.common.util import *
from awlsim.common.exceptions import *

from awlsim.library.libselection import *

if isPy2Compat:
	from ConfigParser import SafeConfigParser as _ConfigParser
	from ConfigParser import Error as _ConfigParserError
else:
	from configparser import ConfigParser as _ConfigParser
	from configparser import Error as _ConfigParserError

import datetime


__all__ = [ "LegacyProjectParser", ]


class LegacyProjectParser(object):
	"""Legacy project parser.
	Legacy format is v0 INI-style file format.
	"""

	@classmethod
	def parse(cls, projectClass, text, projectFile):
		from awlsim.common.project import GuiSettings
		from awlsim.common.project import CoreLinkSettings
		from awlsim.common.project import HwmodSettings

		projectDir = os.path.dirname(projectFile)

		createDate = None
		modifyDate = None
		awlSources = []
		fupSources = []
		kopSources = []
		symTabSources = []
		libSelections = []
		specs = S7CPUSpecs()
		conf = S7CPUConfig()
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
				try:
					createDate = datetime.datetime.strptime(dStr,
								projectClass.DATETIME_FMT)
				except (ValueError, TypeError) as e:
					createDate = None
				modifyDate = createDate
			if p.has_option("AWLSIM_PROJECT", "create_date"):
				dStr = p.get("AWLSIM_PROJECT", "create_date")
				try:
					createDate = datetime.datetime.strptime(dStr,
								projectClass.DATETIME_FMT)
				except (ValueError, TypeError) as e:
					createDate = None
			if p.has_option("AWLSIM_PROJECT", "modify_date"):
				dStr = p.get("AWLSIM_PROJECT", "modify_date")
				try:
					modifyDate = datetime.datetime.strptime(dStr,
								projectClass.DATETIME_FMT)
				except (ValueError, TypeError) as e:
					modifyDate = None

			def getSrcs(srcList, section, prefix, SrcClass):
				for i in range(0xFFFF):
					option = "%s_file_%d" % (prefix, i)
					if not p.has_option(section, option):
						break
					path = p.get(section, option)
					src = SrcClass.fromFile(
						name=path,
						filepath=RelPath(projectDir).fromRelative(path),
						compatReEncode=True)
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
				conf.setConfiguredMnemonics(mnemonics)
			if p.has_option("CPU", "nr_accus"):
				nrAccus = p.getint("CPU", "nr_accus")
				specs.setNrAccus(nrAccus)
			if p.has_option("CPU", "clock_memory_byte"):
				clockMemByte = p.getint("CPU", "clock_memory_byte")
				conf.setClockMemByte(clockMemByte)
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

		return projectClass(projectFile = projectFile,
				    createDate = createDate,
				    modifyDate = modifyDate,
				    awlSources = awlSources,
				    fupSources = fupSources,
				    kopSources = kopSources,
				    symTabSources = symTabSources,
				    libSelections = libSelections,
				    cpuSpecs = specs,
				    cpuConf = conf,
				    obTempPresetsEn = obTempPresetsEn,
				    extInsnsEn = extInsnsEn,
				    guiSettings = guiSettings,
				    coreLinkSettings = linkSettings,
				    hwmodSettings = hwmodSettings)
