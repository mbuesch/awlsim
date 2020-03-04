# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU widget
#
# Copyright 2012-2019 Michael Buesch <m@bues.ch>
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

from awlsim.common.locale import _

from awlsim.gui.icons import *
from awlsim.gui.util import *


__all__ = [
	"CpuInspectToolBar",
	"CpuControlToolBar",
]


class OnlineSelectAction(QAction):
	def __init__(self, parent):
		QAction.__init__(self, getIcon("network"), "", parent)

		self.setCheckable(True)
		self.__handleToggle(self.isChecked())

		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		if checked:
			self.setText(_("Go offline"))
		else:
			self.setText(_("Go online (Connect to a CPU)"))

class RunSelectAction(QAction):
	def __init__(self, parent):
		QAction.__init__(self, getIcon("run"), "", parent)

		self.setCheckable(True)
		self.__handleToggle(self.isChecked())

		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		if checked:
			self.setText(_("Stop CPU (STOP mode)"))
			self.setIcon(getIcon("stop"))
		else:
			self.setText(_("Start CPU (RUN mode)"))
			self.setIcon(getIcon("run"))

class DiagSelectAction(QAction):
	def __init__(self, parent):
		QAction.__init__(self, getIcon("glasses"), "", parent)

		self.setCheckable(True)
		self.__handleToggle(self.isChecked())

		self.toggled.connect(self.__handleToggle)

	def __handleToggle(self, checked):
		if checked:
			self.setText(_("Disable online diagnosis"))
		else:
			self.setText(_("Enable online diagnosis"))

class CpuInspectToolBar(QToolBar):
	def __init__(self, parent=None):
		QToolBar.__init__(self, parent)
		self.setObjectName("CpuInspectToolBar")
		self.setWindowTitle(_("CPU inspection tool bar"))

		self.blocksAction = QAction(getIcon("plugin"),
					    _("Add inspection: Online blocks"),
					    self)
		self.addAction(self.blocksAction)
		self.inputsAction = QAction(getIcon("inputs"),
					    _("Add inspection: Input memory (I / E)"),
					    self)
		self.addAction(self.inputsAction)
		self.outputsAction = QAction(getIcon("outputs"),
					     _("Add inspection: Output memory (Q / A)"),
					     self)
		self.addAction(self.outputsAction)
		self.flagsAction = QAction(getIcon("flags"),
					   _("Add inspection: Flag memory (M)"),
					   self)
		self.addAction(self.flagsAction)
		self.dbAction = QAction(getIcon("datablock"),
					_("Add inspection: Data block (DB)"),
					self)
		self.addAction(self.dbAction)
		self.timerAction = QAction(getIcon("timer"),
					   _("Add inspection: Timer (T)"),
					   self)
		self.addAction(self.timerAction)
		self.counterAction = QAction(getIcon("counter"),
					     _("Add inspection: Counter (C / Z)"),
					     self)
		self.addAction(self.counterAction)
		self.cpuAction = QAction(getIcon("cpu"),
					 _("Add inspection: CPU overview"),
					 self)
		self.addAction(self.cpuAction)
		self.lcdAction = QAction(getIcon("lcd"),
					 _("Add inspection: LCD"),
					 self)
		self.addAction(self.lcdAction)

	def connectToCpuWidget(self, cpuWidget):
		self.blocksAction.triggered.connect(cpuWidget.newWin_Blocks)
		self.inputsAction.triggered.connect(cpuWidget.newWin_E)
		self.outputsAction.triggered.connect(cpuWidget.newWin_A)
		self.flagsAction.triggered.connect(cpuWidget.newWin_M)
		self.dbAction.triggered.connect(cpuWidget.newWin_DB)
		self.timerAction.triggered.connect(cpuWidget.newWin_T)
		self.counterAction.triggered.connect(cpuWidget.newWin_Z)
		self.cpuAction.triggered.connect(cpuWidget.newWin_CPU)
		self.lcdAction.triggered.connect(cpuWidget.newWin_LCD)

class CpuControlToolBar(QToolBar):
	def __init__(self, parent=None):
		QToolBar.__init__(self, parent)
		self.setObjectName("CpuControlToolBar")
		self.setWindowTitle(_("CPU control tool bar"))

		self.onlineAction = OnlineSelectAction(self)
		self.addAction(self.onlineAction)
		self.resetAction = QAction(getIcon("doc_delete"),
					   _("Reset the CPU"),
					   self)
		self.addAction(self.resetAction)
		self.downloadAction = QAction(getIcon("download"),
					      _("Download all sources to CPU"),
					      self)
		self.addAction(self.downloadAction)
		self.downloadSingleAction = QAction(getIcon("download_one"),
						    _("Download single source to CPU"),
						    self)
		self.addAction(self.downloadSingleAction)
		self.runAction = RunSelectAction(self)
		self.addAction(self.runAction)
		self.diagAction = DiagSelectAction(self)
		self.addAction(self.diagAction)

	def connectToCpuWidget(self, cpuWidget):
		self.onlineAction.toggled.connect(cpuWidget._onlineToggled)
		self.resetAction.triggered.connect(cpuWidget.resetCpu)
		self.downloadAction.triggered.connect(cpuWidget.download)
		self.downloadSingleAction.triggered.connect(cpuWidget.downloadSingle)
		self.runAction.toggled.connect(cpuWidget._runStateToggled)
		self.diagAction.toggled.connect(cpuWidget._onlineDiagToggled)

		cpuWidget.reqRunButtonState.connect(self.__setRun)
		cpuWidget.reqOnlineButtonState.connect(self.__setOnline)
		cpuWidget.reqOnlineDiagButtonState.connect(self.__setOnlineDiag)

	def __setRun(self, en):
		if en != self.runAction.isChecked():
			self.runAction.trigger()

	def __setOnline(self, en):
		if en != self.onlineAction.isChecked():
			self.onlineAction.trigger()

	def __setOnlineDiag(self, en):
		if en != self.diagAction.isChecked():
			self.diagAction.trigger()
