# -*- coding: utf-8 -*-
#
# AWL simulator - Template dialog
#
# Copyright 2014-2018 Michael Buesch <m@bues.ch>
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

from awlsim.common.templates import *

from awlsim.gui.util import *
from awlsim.gui.icons import *


class TemplateDialog(QDialog):
	def __init__(self, blockName, verboseBlockName=None, extra=None, parent=None):
		QDialog.__init__(self, parent)
		self.setLayout(QGridLayout())

		if not verboseBlockName:
			verboseBlockName = blockName

		self.setWindowTitle("Awlsim - Insert %s template" %\
				    verboseBlockName)

		hbox = QHBoxLayout()
		label = QLabel(self)
		label.setPixmap(getIcon("textsource").pixmap(QSize(48, 48)))
		hbox.addWidget(label)
		label = QLabel("Insert %s template" % verboseBlockName, self)
		font = label.font()
		font.setPointSize(max(12, font.pointSize()))
		label.setFont(font)
		label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
		hbox.addWidget(label)
		hbox.addStretch()
		self.layout().addLayout(hbox, 0, 0, 1, 2)

		label = QLabel("%s number:" % verboseBlockName, self)
		self.layout().addWidget(label, 1, 0)
		self.blockNr = QSpinBox(self)
		self.blockNr.setMinimum(1)
		self.blockNr.setMaximum(0xFFFF)
		self.blockNr.setValue(1)
		self.blockNr.setPrefix(blockName + " ")
		self.layout().addWidget(self.blockNr, 1, 1)

		if extra:
			label = QLabel("%s number:" % extra, self)
			self.layout().addWidget(label, 2, 0)
			self.extraNr = QSpinBox(self)
			self.extraNr.setMinimum(1)
			self.extraNr.setMaximum(0xFFFF)
			self.extraNr.setValue(1)
			self.extraNr.setPrefix(extra + " ")
			self.layout().addWidget(self.extraNr, 2, 1)

		self.verbose = QCheckBox("Generate &verbose code", self)
		self.verbose.setCheckState(Qt.Checked)
		self.layout().addWidget(self.verbose, 3, 0, 1, 2)

		self.layout().setRowStretch(4, 1)

		self.okButton = QPushButton("&Paste code", self)
		self.layout().addWidget(self.okButton, 5, 0, 1, 2)

		self.okButton.released.connect(self.accept)

	def getBlockNumber(self):
		return self.blockNr.value()

	def getExtraNumber(self):
		return self.extraNr.value()

	def getVerbose(self):
		return self.verbose.checkState() == Qt.Checked

	@classmethod
	def make_OB(cls, parent=None):
		return cls("OB", parent=parent)

	@classmethod
	def make_FC(cls, parent=None):
		return cls("FC", parent=parent)

	@classmethod
	def make_FB(cls, parent=None):
		return cls("FB", parent=parent)

	@classmethod
	def make_instanceDB(cls, parent=None):
		return cls("DB", "Instance-DB", extra="FB", parent=parent)

	@classmethod
	def make_globalDB(cls, parent=None):
		return cls("DB", parent=parent)

	@classmethod
	def make_UDT(cls, parent=None):
		return cls("UDT", parent=parent)

	@classmethod
	def make_FCcall(cls, parent=None):
		return cls("FC", "FC call", parent=parent)

	@classmethod
	def make_FBcall(cls, parent=None):
		return cls("FB", "FB call", extra="DB", parent=parent)
