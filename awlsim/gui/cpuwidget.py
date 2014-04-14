# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU widget
#
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
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

from awlsim.gui.util import *
from awlsim.gui.pseudohardware import *
from awlsim.gui.cpustate import *


class CpuWidget(QWidget):
	runStateChanged = Signal(int)

	EnumGen.start
	STATE_STOP	= EnumGen.item
	STATE_PARSE	= EnumGen.item
	STATE_INIT	= EnumGen.item
	STATE_LOAD	= EnumGen.item
	STATE_RUN	= EnumGen.item
	EnumGen.end

	def __init__(self, mainWidget, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))

		self.mainWidget = mainWidget
		self.sim = mainWidget.getSim()
		self.state = self.STATE_STOP
		self.__nextCpuWidgetUpdate = 0.0

		self.pseudoHw = GuiPseudoHardwareInterface(sim = self.sim,
							   cpuWidget = self)
		self.sim.registerHardware(self.pseudoHw)

		group = QGroupBox("CPU status", self)
		group.setLayout(QGridLayout(group))
		self.runButton = QRadioButton("RUN", group)
		group.layout().addWidget(self.runButton, 0, 0)
		self.stopButton = QRadioButton("STOP", group)
		group.layout().addWidget(self.stopButton, 1, 0)
		self.onlineViewCheckBox = QCheckBox("Online diag.", group)
		group.layout().addWidget(self.onlineViewCheckBox, 2, 0)
		self.layout().addWidget(group, 0, 0)

		group = QGroupBox("Add window", self)
		group.setLayout(QGridLayout(group))
		self.newCpuStateButton = QPushButton("CPU", group)
		group.layout().addWidget(self.newCpuStateButton, 0, 0)
		self.newLCDButton = QPushButton("LCD", group)
		group.layout().addWidget(self.newLCDButton, 0, 1)
		self.newDBButton = QPushButton("DB", group)
		group.layout().addWidget(self.newDBButton, 0, 2)
		self.newEButton = QPushButton("E (I)", group)
		group.layout().addWidget(self.newEButton, 1, 0)
		self.newAButton = QPushButton("A (Q)", group)
		group.layout().addWidget(self.newAButton, 1, 1)
		self.newMButton = QPushButton("M", group)
		group.layout().addWidget(self.newMButton, 1, 2)
		self.layout().addWidget(group, 0, 1)

		self.stateWs = StateWorkspace(self)
		self.stateWs.setScrollBarsEnabled(True)
		self.layout().addWidget(self.stateWs, 1, 0, 1, 2)

		self.stopButton.setChecked(Qt.Checked)

		self.runButton.toggled.connect(self.__runStateToggled)
		self.stopButton.toggled.connect(self.__runStateToggled)
		self.onlineViewCheckBox.stateChanged.connect(self.__updateOnlineViewState)
		self.newCpuStateButton.released.connect(self.__newWin_CPU)
		self.newDBButton.released.connect(self.__newWin_DB)
		self.newEButton.released.connect(self.__newWin_E)
		self.newAButton.released.connect(self.__newWin_A)
		self.newMButton.released.connect(self.__newWin_M)
		self.newLCDButton.released.connect(self.__newWin_LCD)

		self.__newWin_CPU()
		self.update()

	def __addWindow(self, win):
		self.stateWs.addWindow(win, Qt.Window)
		win.show()
		self.update()

	def __newWin_CPU(self):
		self.__addWindow(State_CPU(self.mainWidget.getSim(), self))

	def __newWin_DB(self):
		self.__addWindow(State_Mem(self.mainWidget.getSim(),
					   AbstractDisplayWidget.ADDRSPACE_DB,
					   self))

	def __newWin_E(self):
		self.__addWindow(State_Mem(self.mainWidget.getSim(),
					   AbstractDisplayWidget.ADDRSPACE_E,
					   self))

	def __newWin_A(self):
		self.__addWindow(State_Mem(self.mainWidget.getSim(),
					   AbstractDisplayWidget.ADDRSPACE_A,
					   self))

	def __newWin_M(self):
		self.__addWindow(State_Mem(self.mainWidget.getSim(),
					   AbstractDisplayWidget.ADDRSPACE_M,
					   self))

	def __newWin_LCD(self):
		self.__addWindow(State_LCD(self.mainWidget.getSim(), self))

	def update(self):
		for win in self.stateWs.windowList():
			win.update()

	# Get the queued CPU store requests
	def getQueuedStoreRequests(self):
		reqList = []
		for win in self.stateWs.windowList():
			reqList.extend(win.getQueuedStoreRequests())
		return reqList

	def __cycleExitCallback(self, cpu):
		if self.state == self.STATE_RUN:
			self.mainWidget.codeEdit.updateCpuStats_afterCycle(cpu)

	def __blockExitCallback(self, cpu):
		if self.state == self.STATE_RUN:
			self.mainWidget.codeEdit.updateCpuStats_afterBlock(cpu)

			# Special case: May update the CPU-state-widgets (if any)
			# on block exit.
			if cpu.now >= self.__nextCpuWidgetUpdate:
				self.__nextCpuWidgetUpdate = cpu.now + 0.15
				for win in self.stateWs.windowList():
					if isinstance(win, State_CPU):
						win.update()

	def __postInsnCallback(self, cpu):
		if self.state == self.STATE_RUN:
			self.mainWidget.codeEdit.updateCpuStats_afterInsn(cpu)

	def __screenUpdateCallback(self, cpu):
		self.__postInsnCallback(cpu)
		self.__blockExitCallback(cpu)
		self.__cycleExitCallback(cpu)
		QApplication.processEvents(QEventLoop.AllEvents, 100)

	def __run(self):
		sim = self.mainWidget.getSim()
		self.__updateOnlineViewState()
		self.__setState(self.STATE_PARSE)
		self.runButton.setChecked(True)
		self.runButton.setEnabled(False) # Redraws the radio button
		self.runButton.setEnabled(True)
		ob1_awl = self.mainWidget.getCodeEditWidget().getCode()
		if not ob1_awl.strip():
			MessageBox.error(self, "No AWL/STL code available. Cannot run.")
			self.stop()
			return
		try:
			parser = AwlParser()
			parser.parseData(ob1_awl)
			self.__setState(self.STATE_INIT)
			cpu = sim.getCPU()
			cpu.setBlockExitCallback(self.__blockExitCallback, cpu)
			cpu.setCycleExitCallback(self.__cycleExitCallback, cpu)
			cpu.setScreenUpdateCallback(
				self.__screenUpdateCallback, cpu)
			self.__setState(self.STATE_LOAD)
			sim.reset()
			sim.load(parser.getParseTree())
			sim.startup()
		except AwlParserError as e:
			MessageBox.handleAwlParserError(self, e)
			self.stop()
			sim.shutdown()
			return
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Error while loading code", e)
			self.stop()
			sim.shutdown()
			return
		except Exception:
			handleFatalException(self)
		self.__setState(self.STATE_RUN)
		try:
			while self.state == self.STATE_RUN:
				sim.runCycle()
				QApplication.processEvents(QEventLoop.AllEvents, 100)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Error while executing code", e)
			self.stop()
		except MaintenanceRequest as e:
			if e.requestType == MaintenanceRequest.TYPE_SHUTDOWN:
				print("Shutting down, as requested...")
				sim.shutdown()
				QApplication.exit(0)
				return
			else:
				assert(0)
		except Exception:
			handleFatalException(self)
		sim.shutdown()

	def stop(self):
		if self.state == self.STATE_STOP:
			return
		self.stopButton.setChecked(True)
		self.runButton.setEnabled(True)
		self.__setState(self.STATE_STOP)

	def run(self):
		if self.state != self.STATE_STOP:
			return
		self.runButton.setChecked(True)

	def getState(self):
		return self.state

	def __setState(self, newState):
		if newState != self.state:
			self.state = newState
			self.runStateChanged.emit(self.state)
			QApplication.processEvents(QEventLoop.AllEvents, 1000)

	def __runStateToggled(self):
		if self.runButton.isChecked():
			if self.state == self.STATE_STOP:
				self.__run()
		if self.stopButton.isChecked():
			if self.state != self.STATE_STOP:
				self.stop()

	def __updateOnlineViewState(self):
		en = self.onlineViewCheckBox.checkState() == Qt.Checked
		self.mainWidget.codeEdit.enableCpuStats(en)
		cpu = self.mainWidget.getSim().getCPU()
		if en:
			cpu.setPostInsnCallback(self.__postInsnCallback, cpu)
		else:
			cpu.setPostInsnCallback(None)


