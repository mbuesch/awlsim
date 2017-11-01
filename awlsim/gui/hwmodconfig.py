# -*- coding: utf-8 -*-
#
# AWL simulator - GUI hardware module configuration widget
#
# Copyright 2015 Michael Buesch <m@bues.ch>
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

from awlsim.gui.configdialog import *
from awlsim.gui.util import *

from awlsim.core.hardware_loader import HwModLoader


class HwmodParamModel(QAbstractTableModel):
	# Signal: Emitted, if a new error appeared or an old error disappeared.
	newErrorText = Signal(str)

	def __init__(self):
		QAbstractTableModel.__init__(self)

		self.modDesc = None		# HwmodDescriptor
		self.modInterface = None	# HardwareInterface

	@property
	def __params(self):
		"""Return a list of tuples: (paramName, paramValue)"""
		if not self.modDesc:
			return []
		return sorted(dictItems(self.modDesc.getParameters()),
			      key = lambda p: p[0])

	def __getParamDesc(self, paramName):
		if self.modInterface:
			return self.modInterface.getParamDesc(paramName)
		return None

	def __verifyParams(self):
		if self.modInterface and self.modDesc:
			try:
				# Create a module instance.
				# This will raise errors on invalid parameters.
				self.modInterface(None, self.modDesc.getParameters())
			except AwlSimError as e:
				self.newErrorText.emit(str(e))
				return
		self.newErrorText.emit("")

	def setHwmod(self, modDesc):
		self.beginResetModel()

		try:
			if not modDesc:
				raise ValueError
			mod = HwModLoader.loadModule(modDesc.getModuleName())
			interface = mod.getInterface()
		except (AwlSimError, ValueError) as e:
			interface = None

		self.modInterface = interface
		self.modDesc = modDesc

		self.endResetModel()

	def deleteEntry(self, row):
		params = self.__params
		if row >= 0 and row < len(params):
			self.beginResetModel() # inefficient
			pName, pValue = params[row]
			self.modDesc.removeParameter(pName)
			self.endResetModel()
			self.__verifyParams()

	def rowCount(self, parent=QModelIndex()):
		return len(self.__params) + 1

	def columnCount(self, parent=QModelIndex()):
		return 2

	def data(self, index, role=Qt.DisplayRole):
		if not index:
			return None
		row, column = index.row(), index.column()
		if role in (Qt.DisplayRole, Qt.EditRole):
			params = self.__params
			if row >= len(params):
				return None
			if column == 0:
				return params[row][0]
			elif column == 1:
				paramDesc = self.__getParamDesc(params[row][0])
				if paramDesc and not paramDesc.userEditable:
					# Not user editable
					if params[row][1] is None:
						return "<set by system>"
				if params[row][1] is None:
					return ""
				return params[row][1]
		elif role in {Qt.BackgroundRole,
			      Qt.ForegroundRole}:
			params = self.__params
			if row < len(params):
				paramDesc = self.__getParamDesc(params[row][0])
				if paramDesc and not paramDesc.userEditable:
					# Not user editable
					if role == Qt.BackgroundRole:
						return QBrush(QColor("darkgrey"))
					return QBrush(QColor("black"))
				if column == 0:
					if paramDesc:
						# This is a standard parameter.
						if role == Qt.BackgroundRole:
							return QBrush(QColor("lightgrey"))
						return QBrush(QColor("black"))
		elif role in (Qt.ToolTipRole, Qt.WhatsThisRole):
			params = self.__params
			if row < len(params):
				paramDesc = self.__getParamDesc(params[row][0])
				if column == 0:
					if paramDesc and paramDesc.description:
						return paramDesc.description
					return "The parameter's name"
				elif column == 1:
					return "Value for '%s'" %\
						params[row][0]
			else:
				if column == 0:
					return "New parameter name"
		return None

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if role != Qt.DisplayRole:
			return None
		if orientation == Qt.Horizontal:
			return ("Parameter", "Value")[section]
		else:
			params = self.__params
			if section >= len(params):
				return "new"
			return "%d" % (section + 1)

	def setData(self, index, value, role=Qt.EditRole):
		if not index:
			return False
		row, column = index.row(), index.column()
		if role == Qt.EditRole:
			if not self.modDesc:
				return False
			params = self.__params
			if row >= len(params):
				if column == 0:
					# Add parameter
					value = value.strip()
					for pName, pValue in params:
						if pName == value:
							# Parameter does already exist
							return False
					self.beginResetModel() # inefficient
					self.modDesc.addParameter(value, "")
					self.endResetModel()
					self.__verifyParams()
					return True
			else:
				paramName = params[row][0]
				if column == 0:
					# Rename parameter
					for pName, pValue in params:
						if pName == value:
							# Parameter does already exist
							return False
					self.beginResetModel() # inefficient
					savedValue = params[row][1]
					self.modDesc.removeParameter(paramName)
					self.modDesc.addParameter(value, savedValue)
					self.endResetModel()
					self.__verifyParams()
					return True
				elif column == 1:
					# Set parameter value
					self.modDesc.setParameterValue(paramName, value)
					self.__verifyParams()
					return True
		return False

	def flags(self, index):
		if not index:
			return Qt.ItemIsEnabled
		row, column = index.row(), index.column()
		params = self.__params
		if row < len(params):
			paramDesc = self.__getParamDesc(params[row][0])
			if paramDesc and not paramDesc.userEditable:
				return Qt.ItemIsEnabled | Qt.ItemIsSelectable
		else:
			if column != 0:
				return Qt.ItemIsEnabled
		return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

class HwmodParamView(QTableView):
	def __init__(self, model=None, parent=None):
		QTableView.__init__(self, parent)

		if not model:
			model = HwmodParamModel()
		self.setModel(model)

		self.setColumnWidth(0, 170)
		self.setColumnWidth(1, 80)

	def deleteEntry(self, index=None):
		if not index:
			index = self.currentIndex()
		if not index:
			return
		self.model().deleteEntry(index.row())

	def keyPressEvent(self, ev):
		QTableView.keyPressEvent(self, ev)

		if ev.key() == Qt.Key_Delete:
			self.deleteEntry()

	def setHwmod(self, modDesc):
		self.model().setHwmod(modDesc)

class HwmodConfigWidget(QWidget):
	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())
		self.layout().setContentsMargins(QMargins())

		self.__loadedModDescs = []
		self.__modSelectChangeBlocked = Blocker()

		group = QGroupBox(self)
		group.setLayout(QGridLayout())

		label = QLabel("Available modules:", self)
		group.layout().addWidget(label, 0, 0)
		self.availList = QListWidget(self)
		self.availList.setMaximumWidth(180)
		group.layout().addWidget(self.availList, 1, 0)
		self.manualModName = QLineEdit(self)
		self.manualModName.setToolTip("Name of another module to add.\n"
			"Note: Typos in the module name will result in "
			"errors on CPU startup.")
		self.manualModName.setMaximumWidth(180)
		group.layout().addWidget(self.manualModName, 2, 0)

		vbox = QVBoxLayout()
		self.addButton = QPushButton(self)
		self.addButton.setIcon(getIcon("next"))
		self.addButton.setToolTip("Add the selected module to the "
			"project\nand mark it for download to the CPU.")
		vbox.addWidget(self.addButton)
		self.delButton = QPushButton(self)
		self.delButton.setIcon(getIcon("previous"))
		self.delButton.setToolTip("Remove the selected module from "
			"the project\nand mark it for removal from the CPU.")
		vbox.addWidget(self.delButton)
		group.layout().addLayout(vbox, 0, 1, 3, 1)

		label = QLabel("Loaded modules:", self)
		group.layout().addWidget(label, 0, 2)
		self.loadedList = QListWidget(self)
		self.loadedList.setMaximumWidth(180)
		group.layout().addWidget(self.loadedList, 1, 2, 2, 1)

		self.paramViewLabel = QLabel("Module parameters:", self)
		group.layout().addWidget(self.paramViewLabel, 0, 3)
		vbox = QVBoxLayout()
		self.paramView = HwmodParamView(None, self)
		self.paramView.setMinimumWidth(300)
		vbox.addWidget(self.paramView)
		self.paramErrorText = QLabel(self)
		self.paramErrorText.setWordWrap(True)
		vbox.addWidget(self.paramErrorText)
		group.layout().addLayout(vbox, 1, 3, 2, 1)

		self.layout().addWidget(group, 0, 0)

		self.layout().setRowStretch(1, 1)

		self.__handleLoadedSelectChange(None, None)
		self.__updateAddButton()
		self.setAvailableModules(HwModLoader.builtinHwModules)

		self.availList.currentItemChanged.connect(self.__handleAvailSelectChange)
		self.manualModName.textChanged.connect(self.__handleManualModChange)
		self.loadedList.currentItemChanged.connect(self.__handleLoadedSelectChange)
		self.addButton.released.connect(self.__handleAdd)
		self.delButton.released.connect(self.__handleDel)
		self.paramView.model().newErrorText.connect(self.__handleNewErrorText)

	def __updateAddButton(self):
		self.addButton.setEnabled(self.manualModName.text().strip() != "" or
					  self.availList.currentItem() is not None)

	def __handleAvailSelectChange(self, cur, prev):
		if not self.__modSelectChangeBlocked:
			with self.__modSelectChangeBlocked:
				self.manualModName.setText("")
				self.loadedList.setCurrentItem(None)
		self.__updateAddButton()

	def __handleManualModChange(self, text):
		if not self.__modSelectChangeBlocked:
			with self.__modSelectChangeBlocked:
				self.availList.setCurrentItem(None)
				self.loadedList.setCurrentItem(None)
		self.__updateAddButton()

	def __handleLoadedSelectChange(self, cur, prev):
		if cur:
			with self.__modSelectChangeBlocked:
				self.availList.setCurrentItem(None)
				self.manualModName.setText("")
			self.paramView.setHwmod(cur.data(Qt.UserRole))
		else:
			self.paramView.setHwmod(None)
		self.paramViewLabel.setEnabled(bool(cur))
		self.paramView.setEnabled(bool(cur))
		self.delButton.setEnabled(bool(cur))
		self.__handleNewErrorText("")

	def __handleAdd(self):
		manualModName = self.manualModName.text().strip()
		if manualModName:
			modDesc = HwmodDescriptor(manualModName)
			self.manualModName.clear()
		else:
			item = self.availList.currentItem()
			if not item:
				return
			modDesc = item.data(Qt.UserRole).dup()
		item = QListWidgetItem(modDesc.getModuleName(),
				       self.loadedList)
		item.setData(Qt.UserRole, modDesc)
		self.__loadedModDescs.append(modDesc)

	def __handleDel(self):
		item = self.loadedList.currentItem()
		if not item:
			return
		item = self.loadedList.takeItem(self.loadedList.row(item))
		modDesc = item.data(Qt.UserRole)
		self.__loadedModDescs.remove(modDesc)
		self.__handleLoadedSelectChange(self.loadedList.currentItem(), None)

	def __handleNewErrorText(self, text):
		if text.strip().startswith("["):
			text = text[text.find("]") + 1 : ]
		text = text.strip()
		if text:
			text = "Warning: " + text
		self.paramErrorText.setText(text)
		if text:
			self.paramErrorText.show()
		else:
			self.paramErrorText.hide()

	def setAvailableModules(self, mods):
		self.availList.clear()
		self.availableMods = mods
		for modName in mods:
			item = QListWidgetItem(modName, self.availList)
			try:
				interface = HwModLoader.loadModule(modName).getInterface()
			except AwlSimError as e:
				interface = None
			params = {}
			if interface:
				for paramDesc in interface.getParamDescs():
					if paramDesc.defaultValue is None:
						params[paramDesc.name] = None
						continue
					params[paramDesc.name] = str(paramDesc.defaultValue)
			modDesc = HwmodDescriptor(moduleName = modName,
						  parameters = params)
			item.setData(Qt.UserRole, modDesc)

	def loadFromProject(self, project):
		self.loadedList.clear()
		hwSettings = project.getHwmodSettings()
		self.__loadedModDescs = []
		for modDesc in hwSettings.getLoadedModules():
			modDesc = modDesc.dup()
			item = QListWidgetItem(modDesc.getModuleName())
			item.setData(Qt.UserRole, modDesc)
			self.loadedList.addItem(item)
			self.__loadedModDescs.append(modDesc)

	def storeToProject(self, project):
		hwSettings = project.getHwmodSettings()
		hwSettings.setLoadedModules(self.__loadedModDescs)
		return True

class HwmodConfigDialog(AbstractConfigDialog):
	def __init__(self, project, parent=None):
		AbstractConfigDialog.__init__(self,
			project = project,
			iconName = "hwmod",
			title = "Hardware module setup",
			centralWidget = HwmodConfigWidget(),
			parent = parent)

	def loadFromProject(self):
		self.centralWidget.loadFromProject(self.project)

	def storeToProject(self):
		if self.centralWidget.storeToProject(self.project):
			self.settingsChanged.emit()
