# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU widget
#
# Copyright 2012-2020 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *
from awlsim.gui.cpustate import *
from awlsim.gui.awlsimclient import *
from awlsim.gui.icons import *
from awlsim.gui.runstate import *


class CpuWidget(QWidget):
	"""CPU state display widget.
	"""

	def __init__(self, mainWidget, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		self.layout().setContentsMargins(QMargins(7, 0, 0, 0))

		self.mainWidget = mainWidget

		client = self.getSimClient()
		client.haveCpuDump.connect(self.__handleCpuDump)
		client.haveMemoryUpdate.connect(self.__handleMemoryUpdate)
		client.guiRunState.stateChanged.connect(self.__handleGuiRunStateChange)

		self.stateMdi = StateMdiArea(client=client, parent=self)
		self.stateMdi.setViewMode(QMdiArea.SubWindowView)
		self.stateMdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.stateMdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.layout().addWidget(self.stateMdi, 0, 0)

		self.stateMdi.subWinAdded.connect(
			lambda w: self.__uploadMemReadAreas())
		self.stateMdi.subWinClosed.connect(
			lambda w: self.__stateMdiWindowClosed(w))
		self.stateMdi.settingsChanged.connect(
			lambda: self.__uploadMemReadAreas())
		self.stateMdi.contentChanged.connect(
			lambda: self.mainWidget.setDirty(self.mainWidget.DIRTY_SLIGHT))
		self.stateMdi.openByIdentHash.connect(
			lambda mdiWin, identHash: self.mainWidget.openByIdentHash(identHash))

	def getSimClient(self):
		return self.mainWidget.getSimClient()

	def __stateMdiWindowClosed(self, mdiWin):
		QTimer.singleShot(0, self.__uploadMemReadAreas)

	def newWin_CPU(self):
		win = State_CPU(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_DB(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_DB)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_E(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_E)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_A(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_A)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_M(self):
		win = State_Mem(self.getSimClient(),
				AbstractDisplayWidget.ADDRSPACE_M)
		self.stateMdi.addCpuStateWindow(win)

	def newWin_T(self):
		win = State_Timer(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_Z(self):
		win = State_Counter(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_LCD(self):
		win = State_LCD(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	def newWin_Blocks(self):
		win = State_Blocks(self.getSimClient())
		self.stateMdi.addCpuStateWindow(win)

	# Upload the used memory area descriptors to the core.
	def __uploadMemReadAreas(self):
		client = self.getSimClient()
		wantDump = False
		memAreas = []
		for mdiWin in self.stateMdi.subWindowList():
			win = mdiWin.widget()
			memAreas.extend(win.getMemoryAreas())
			if isinstance(win, State_CPU):
				wantDump = True
		try:
			client.setMemoryReadRequests(memAreas,
						     repetitionPeriod = 0.1,
						     sync = True)
			client.setPeriodicDumpInterval(300 if wantDump else 0)
		except AwlSimError as e:
			with MessageBox.awlSimErrorBlocked:
				client.guiRunState.setState(GuiRunState.STATE_EXCEPTION)
			MessageBox.handleAwlSimError(self,
				"Error in awlsim core", e)
			return False
		except MaintenanceRequest as e:
			client.handleMaintenance(e)
			return False
		return True

	def __handleCpuDump(self, dumpText):
		for mdiWin in self.stateMdi.subWindowList():
			win = mdiWin.widget()
			if isinstance(win, State_CPU):
				win.setDumpText(dumpText)

	def __handleMemoryUpdate(self, memAreas):
		for mdiWin in self.stateMdi.subWindowList():
			win = mdiWin.widget()
			win.setMemories(memAreas)

	def __handleGuiRunStateChange(self, newState):
		client = self.getSimClient()

		if newState == GuiRunState.STATE_RUN:
			# Upload the GUI requests.
			if not self.__uploadMemReadAreas():
				client.action_goStop()

	def sizeHint(self):
		return QSize(550, 200)
