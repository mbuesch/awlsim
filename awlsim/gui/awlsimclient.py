# -*- coding: utf-8 -*-
#
# AWL simulator - GUI simulator client access
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

from awlsim.gui.util import *

from awlsim.coreserver.client import *


class GuiAwlSimClient(AwlSimClient, QObject):
	# CPU-dump signal.
	# Parameter: The dump text.
	haveCpuDump = Signal(str)

	# Instruction dump signal.
	# Parameter: AwlSimMessage_INSNSTATE instance.
	haveInsnDump = Signal(AwlSimMessage_INSNSTATE)

	# Memory update signal.
	# Parameter: A list of MemoryArea instances.
	haveMemoryUpdate = Signal(list)

	def __init__(self):
		QObject.__init__(self)
		AwlSimClient.__init__(self)

	# Override sleep handler
	def sleep(self, seconds):
		end = time.monotonic() + seconds
		eventFlags = QEventLoop.AllEvents |\
			     QEventLoop.ExcludeUserInputEvents
		while time.monotonic() < end:
			QApplication.processEvents(eventFlags, 10)
			QThread.msleep(10)

	# Override cpudump handler
	def handle_CPUDUMP(self, dumpText):
		self.haveCpuDump.emit(dumpText)

	# Override memory update handler
	def handle_MEMORY(self, memAreas):
		self.haveMemoryUpdate.emit(memAreas)

	# Override memory update handler
	def handle_INSNSTATE(self, msg):
		self.haveInsnDump.emit(msg)
