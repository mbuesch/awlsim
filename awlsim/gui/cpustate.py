# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU state widgets
#
# Copyright 2012-2015 Michael Buesch <m@bues.ch>
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

from awlsim.gui.valuelineedit import *
from awlsim.gui.blocktreewidget import *
from awlsim.gui.icons import *
from awlsim.gui.util import *


class StateWindow(QWidget):
	# Window-close signal
	closed = Signal(QWidget)
	# Config-change (address, type, etc...) signal
	configChanged = Signal(QWidget)

	COLOR_ACTIVE		= "#F0F000"
	COLOR_LIGHTACTIVE	= "#FFFFC0"

	def __init__(self, client, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		pixmap = QPixmap(16, 16)
		pixmap.fill(QColor(0, 0, 192))
		self.setWindowIcon(QIcon(pixmap))
		self.__client = client
		self.__forceMinimumSize = False

	def __updateSize(self):
		try:
			parent = self.parent()
		except RuntimeError:
			return
		if isinstance(parent, StateMdiSubWindow):
			widget = parent
		else:
			widget = self
		if self.__forceMinimumSize:
			widget.resize(widget.minimumSizeHint())
		else:
			size, hint = widget.size(), widget.minimumSizeHint()
			if size.width() < hint.width() or\
			   size.height() < hint.height():
				widget.resize(hint)
		self.__forceMinimumSize = False

	def _updateSize(self, forceMinimum = False):
		if forceMinimum:
			self.__forceMinimumSize = True
		QTimer.singleShot(0, self.__updateSize)

	# Get a list of MemoryArea instances for the memory
	# areas covered by this window.
	def getMemoryAreas(self):
		return []

	# Try to write memory to this window.
	# The window might reject the request, if this memory
	# doesn't belong to it.
	def setMemory(self, memArea):
		return False

	def setMemories(self, memAreas):
		for memArea in memAreas:
			self.setMemory(memArea)

	def closeEvent(self, ev):
		self.closed.emit(self)
		ev.accept()
		self.deleteLater()

	# Send a request to the CPU to write memory.
	def _writeCpuMemory(self, memAreas):
		try:
			self.__client.writeMemory(memAreas, sync = False)
		except AwlSimError as e:
			MessageBox.handleAwlSimError(self,
				"Failed to write to memory", e)
		except MaintenanceRequest as e:
			# writeMemory is asynchronous.
			# So this should not happen.
			assert(0)

class State_CPU(StateWindow):
	def __init__(self, client, parent=None):
		StateWindow.__init__(self, client, parent)
		self.setWindowTitle("CPU overview")
		self.setWindowIcon(getIcon("cpu"))

		self.label = QLabel(self)
		self.label.setFont(getDefaultFixedFont(10))
		self.label.setTextInteractionFlags(Qt.TextSelectableByMouse |
						   Qt.TextSelectableByKeyboard)
		self.layout().addWidget(self.label, 0, 0)

		self.label.setText("No CPU status available.\n"
				   "Please put the CPU into RUN mode.")

	def setDumpText(self, text):
		self.label.setText(text)
		self._updateSize()

class AbstractDisplayWidget(QWidget):
	EnumGen.start
	ADDRSPACE_E		= EnumGen.item
	ADDRSPACE_A		= EnumGen.item
	ADDRSPACE_M		= EnumGen.item
	ADDRSPACE_DB		= EnumGen.item
	EnumGen.end

	addrspace2name = {
		ADDRSPACE_E	: ("I", "Inputs"),
		ADDRSPACE_A	: ("Q", "Outputs"),
		ADDRSPACE_M	: ("M", "Flags"),
		ADDRSPACE_DB	: ("DB", "Data block"),
	}

	addrspace2memarea = {
		ADDRSPACE_E	: MemoryArea.TYPE_E,
		ADDRSPACE_A	: MemoryArea.TYPE_A,
		ADDRSPACE_M	: MemoryArea.TYPE_M,
		ADDRSPACE_DB	: MemoryArea.TYPE_DB,
	}

	changed = Signal()

	def __init__(self, stateWindow, addrSpace, addr, width, db, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		self.layout().setContentsMargins(QMargins(0, 10, 0, 0))

		self.stateWindow = stateWindow
		self.addrSpace = addrSpace
		self.addr = addr
		self.width = width
		self.db = db

	def clear(self):
		for i in range(self.width // 8):
			self.setByte(i, 0)

	def get(self):
		pass

	# Set a byte in this display widget.
	# offset -> The relative byte offset
	# value -> The byte value
	def setByte(self, offset, value):
		pass

	def _showValueValidity(self, valid):
		if valid:
			pal = self.palette()
			pal.setColor(QPalette.Text, Qt.black)
			self.setPalette(pal)
		else:
			pal = self.palette()
			pal.setColor(QPalette.Text, Qt.red)
			self.setPalette(pal)

class BitDisplayWidget(AbstractDisplayWidget):
	def __init__(self, stateWindow, addrSpace, addr, width, db,
		     parent=None):
		AbstractDisplayWidget.__init__(self, stateWindow, addrSpace,
					       addr, width, db, parent)

		self.__cbActColor = QColor(StateWindow.COLOR_ACTIVE)
		self.__pbActColor = QColor(StateWindow.COLOR_ACTIVE)
		self.__frActColor = QColor(StateWindow.COLOR_LIGHTACTIVE)

		self.__frames = {}
		self.cbs = {}
		self.pbs = {}
		self.prevButtonStates = {}
		y = 0
		for i in range(self.width - 1, -1, -1):
			frame = QFrame(self)
			frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
			frame.setLineWidth(2)
			frame.setLayout(QHBoxLayout())
			frame.setAutoFillBackground(True)
			frame.layout().setContentsMargins(QMargins(3, 0, 0, 0))
			self.__frames[i] = frame

			pb = QPushButton(self)
			pb.setMaximumSize(QSize(13, 13))
			frame.layout().addWidget(pb)
			self.pbs[i] = pb
			self.prevButtonStates[i] = False
			pb.pressed.connect(self.__buttonUpdate)
			pb.released.connect(self.__buttonUpdate)

			cb = QCheckBox(str(i), self)
			cb.setAutoFillBackground(False)
			frame.layout().addWidget(cb)
			self.cbs[i] = cb

			self.__cbOrigColor = cb.palette().color(QPalette.Base)
			self.__pbOrigColor = pb.palette().color(QPalette.Button)
			self.__frOrigColor = frame.palette().color(QPalette.Window)

			cb.stateChanged.connect(self.changed)
			cb.stateChanged.connect(
				lambda state, i=i: self.__updateColors(i, state))
			self.__updateColors(i, Qt.Unchecked)

			self.layout().addWidget(frame, y, (self.width - i - 1) % 8)
			if i and i % 8 == 0:
				y += 1

	def __updateColors(self, bitNr, newState):
		cb = self.cbs[bitNr]
		pb = self.pbs[bitNr]
		fr = self.__frames[bitNr]
		palCb = cb.palette()
		palPb = pb.palette()
		palFr = fr.palette()
		if newState == Qt.Checked:
			cbColor = self.__cbActColor
			pbColor = self.__pbActColor
			frColor = self.__frActColor
		else:
			cbColor = self.__cbOrigColor
			pbColor = self.__pbOrigColor
			frColor = self.__frOrigColor
		if palCb.color(QPalette.Base) != cbColor:
			palCb.setColor(QPalette.Base, cbColor)
			palPb.setColor(QPalette.Button, pbColor)
			palFr.setColor(QPalette.Window, frColor)
			cb.setPalette(palCb)
			pb.setPalette(palPb)
			fr.setPalette(palFr)

	def __buttonUpdate(self):
		for bitNr, pb in dictItems(self.pbs):
			pressed = bool(pb.isDown())
			if pressed == self.prevButtonStates[bitNr]:
				continue
			self.prevButtonStates[bitNr] = pressed

			if self.cbs[bitNr].checkState() == Qt.Checked:
				self.cbs[bitNr].setCheckState(Qt.Unchecked)
			else:
				self.cbs[bitNr].setCheckState(Qt.Checked)

	def get(self):
		value = 0
		for bitNr, cb in dictItems(self.cbs):
			if cb.checkState() == Qt.Checked:
				value |= (1 << bitNr)
		return value

	def setByte(self, offset, value):
		bitBase = ((self.width // 8) - 1 - offset) * 8
		for bitNr in range(bitBase, bitBase + 8):
			if value & 1:
				self.cbs[bitNr].setCheckState(Qt.Checked)
			else:
				self.cbs[bitNr].setCheckState(Qt.Unchecked)
			value >>= 1

class NumberDisplayWidget(AbstractDisplayWidget):
	def __init__(self, stateWindow, base, addrSpace, addr, width, db, parent=None):
		AbstractDisplayWidget.__init__(self, stateWindow, addrSpace,
					       addr, width, db, parent)

		self.base = base
		self.__currentValue = -1

		self.line = ValueLineEdit(self.__validateInput, self)
		self.layout().addWidget(self.line)

		self.line.valueChanged.connect(self.changed)

	def clear(self):
		AbstractDisplayWidget.clear(self)
		self.line.setText("invalid address")

	def __convertValue(self, textValue):
		try:
			if self.base == 2:
				textValue = textValue.replace('_', '').replace(' ', '')
			value = int(textValue, self.base)
			if self.base == 10:
				if value > (1 << (self.width - 1)) - 1 or\
				   value < -(1 << (self.width - 1)):
					raise ValueError
			else:
				if value > (1 << self.width) - 1:
					raise ValueError
		except ValueError as e:
			return None
		return value

	def __validateInput(self, inputString, pos):
		if self.__convertValue(inputString) is None:
			return QValidator.Intermediate
		return QValidator.Acceptable

	def get(self):
		value = self.__convertValue(self.line.text())
		if value is None:
			return 0
		return value

	def setByte(self, offset, value):
		mask = ~(0xFF << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (value << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (self.__currentValue & mask) | value
		if self.__currentValue != value:
			self.__currentValue = value
			self.__displayValue()

	def __displayValue(self):
		value = self.__currentValue
		if self.base == 2:
			string = intToDualString(value, self.width)
		elif self.base == 10:
			if self.width == 8:
				string = "%d" % byteToSignedPyInt(value)
			elif self.width == 16:
				string = "%d" % wordToSignedPyInt(value)
			elif self.width == 32:
				string = "%d" % dwordToSignedPyInt(value)
			else:
				assert(0)
		elif self.base == 16:
			if self.width == 8:
				string = "%02X" % (value & 0xFF)
			elif self.width == 16:
				string = "%04X" % (value & 0xFFFF)
			elif self.width == 32:
				string = "%08X" % (value & 0xFFFFFFFF)
			else:
				assert(0)
		else:
			assert(0)
		self.line.setText(string)

class HexDisplayWidget(NumberDisplayWidget):
	def __init__(self, stateWindow, addrSpace, addr, width, db, parent=None):
		NumberDisplayWidget.__init__(self, stateWindow, 16, addrSpace,
					     addr, width, db, parent)

class DecDisplayWidget(NumberDisplayWidget):
	def __init__(self, stateWindow, addrSpace, addr, width, db, parent=None):
		NumberDisplayWidget.__init__(self, stateWindow, 10, addrSpace,
					     addr, width, db, parent)

class BinDisplayWidget(NumberDisplayWidget):
	def __init__(self, stateWindow, addrSpace, addr, width, db, parent=None):
		NumberDisplayWidget.__init__(self, stateWindow, 2, addrSpace,
					     addr, width, db, parent)

class RealDisplayWidget(AbstractDisplayWidget):
	def __init__(self, stateWindow, addrSpace, addr, width, db, parent=None):
		AbstractDisplayWidget.__init__(self, stateWindow, addrSpace,
					       addr, width, db, parent)

		self.__currentValue = -1

		self.line = ValueLineEdit(self.__validateInput, self)
		self.layout().addWidget(self.line)

		self.line.valueChanged.connect(self.changed)

	def clear(self):
		AbstractDisplayWidget.clear(self)
		self.line.setText("invalid address")

	def __convertValue(self, textValue):
		try:
			value = pyFloatToDWord(float(textValue))
		except ValueError as e:
			return None
		return value

	def __validateInput(self, inputString, pos):
		if self.__convertValue(inputString) is None:
			return QValidator.Intermediate
		return QValidator.Acceptable

	def get(self):
		value = self.__convertValue(self.line.text())
		if value is None:
			return 0
		return value

	def setByte(self, offset, value):
		mask = ~(0xFF << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (value << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (self.__currentValue & mask) | value
		if self.__currentValue != value:
			self.__currentValue = value
			self.__displayValue()

	def __displayValue(self):
		value = self.__currentValue
		if self.width == 32:
			string = str(dwordToPyFloat(value))
		else:
			string = "Not DWORD"
		self.line.setText(string)

class State_Mem(StateWindow):
	def __init__(self, client, addrSpace, parent=None):
		StateWindow.__init__(self, client, parent)
		if addrSpace == AbstractDisplayWidget.ADDRSPACE_E:
			self.setWindowIcon(getIcon("inputs"))
		elif addrSpace == AbstractDisplayWidget.ADDRSPACE_A:
			self.setWindowIcon(getIcon("outputs"))
		elif addrSpace == AbstractDisplayWidget.ADDRSPACE_M:
			self.setWindowIcon(getIcon("flags"))
		elif addrSpace == AbstractDisplayWidget.ADDRSPACE_DB:
			self.setWindowIcon(getIcon("datablock"))

		self.addrSpace = addrSpace

		x = 0

		if addrSpace == AbstractDisplayWidget.ADDRSPACE_DB:
			self.dbSpin = QSpinBox(self)
			self.dbSpin.setPrefix("DB ")
			self.dbSpin.setMinimum(0)
			self.dbSpin.setMaximum(0xFFFF)
			self.layout().addWidget(self.dbSpin, 0, x)
			x += 1

		self.addrSpin = QSpinBox(self)
		self.addrSpin.setMinimum(0)
		self.addrSpin.setMaximum(0xFFFF)
		self.layout().addWidget(self.addrSpin, 0, x)
		x += 1

		self.widthCombo = QComboBox(self)
		self.widthCombo.addItem("Byte", 8)
		self.widthCombo.addItem("Word", 16)
		self.widthCombo.addItem("DWord", 32)
		self.layout().addWidget(self.widthCombo, 0, x)
		x += 1

		self.fmtCombo = QComboBox(self)
		self.fmtCombo.addItem("Checkboxes", "cb")
		self.fmtCombo.addItem("Dual", "bin")
		self.fmtCombo.addItem("Decimal", "dec")
		self.fmtCombo.addItem("Hexadecimal", "hex")
		self.fmtCombo.addItem("Real", "real")
		self.layout().addWidget(self.fmtCombo, 0, x)
		x += 1

		self.contentLayout = QGridLayout()
		self.contentLayout.setContentsMargins(QMargins())
		self.layout().addLayout(self.contentLayout, 1, 0, 1, x)

		self.contentWidget = None

		if addrSpace == AbstractDisplayWidget.ADDRSPACE_DB:
			self.dbSpin.valueChanged.connect(self.rebuild)
		self.addrSpin.valueChanged.connect(self.rebuild)
		self.widthCombo.currentIndexChanged.connect(self.rebuild)
		self.fmtCombo.currentIndexChanged.connect(self.rebuild)

		self.__changeBlocked = Blocker()
		self.rebuild()

	def rebuild(self):
		if self.contentWidget:
			self.contentLayout.removeWidget(self.contentWidget)
			self.contentWidget.deleteLater()
		self.contentWidget = None

		addr = self.addrSpin.value()
		index = self.fmtCombo.currentIndex()
		fmt = self.fmtCombo.itemData(index)
		index = self.widthCombo.currentIndex()
		width = self.widthCombo.itemData(index)
		if self.addrSpace == AbstractDisplayWidget.ADDRSPACE_DB:
			db = self.dbSpin.value()
		else:
			db = None

		if fmt == "real":
			# If REAL is selected with byte or word width,
			# change to dword width.
			if width != 32:
				index = self.widthCombo.findData(32)
				# This will re-trigger the "rebuild" slot.
				self.widthCombo.setCurrentIndex(index)
				return

		name, longName = AbstractDisplayWidget.addrspace2name[self.addrSpace]
		width2suffix = {
			8	: "B",
			16	: "W",
			32	: "D",
		}
		name += width2suffix[width]
		self.addrSpin.setPrefix(name + "  ")
		self.setWindowTitle(longName)

		if fmt == "cb":
			self.contentWidget = BitDisplayWidget(self,
							      self.addrSpace,
							      addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "hex":
			self.contentWidget = HexDisplayWidget(self,
							      self.addrSpace,
							      addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "dec":
			self.contentWidget = DecDisplayWidget(self,
							      self.addrSpace,
							      addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "bin":
			self.contentWidget = BinDisplayWidget(self,
							      self.addrSpace,
							      addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "real":
			self.contentWidget = RealDisplayWidget(self,
							       self.addrSpace,
							       addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		else:
			assert(0)
		self.contentWidget.changed.connect(self.__changed)
		self.contentWidget.setEnabled(True)
		self._updateSize(forceMinimum = True)

		self.configChanged.emit(self)

	def __changed(self):
		if self.__changeBlocked or not self.contentWidget:
			return
		value = self.contentWidget.get()
		width = self.widthCombo.itemData(self.widthCombo.currentIndex())

		memArea = self.__makeMemoryArea()
		memArea.data = bytearray(width // 8)
		WordPacker.toBytes(memArea.data, width, 0, value)

		self._writeCpuMemory((memArea,))

	def __makeMemoryArea(self):
		dbIndex = 0
		if self.addrSpace == AbstractDisplayWidget.ADDRSPACE_DB:
			dbIndex = self.dbSpin.value()
		addr = self.addrSpin.value()
		nrBits = self.widthCombo.itemData(self.widthCombo.currentIndex())

		return MemoryArea(memType = AbstractDisplayWidget.addrspace2memarea[self.addrSpace],
				  flags = 0,
				  index = dbIndex,
				  start = addr,
				  length = nrBits // 8)

	def getMemoryAreas(self):
		return ( self.__makeMemoryArea(), )

	def setMemory(self, memArea):
		if not self.contentWidget:
			return False
		thisArea = self.__makeMemoryArea()
		if not thisArea.overlapsWith(memArea):
			return False
		thisStart, thisEnd = thisArea.start, thisArea.start + thisArea.length - 1

		if memArea.flags & (memArea.FLG_ERR_READ | memArea.FLG_ERR_WRITE):
			self.contentWidget.setEnabled(False)
			self.contentWidget.clear()
			return False
		self.contentWidget.setEnabled(True)

		with self.__changeBlocked:
			addr = memArea.start
			for value in memArea.data:
				if addr > thisEnd:
					break
				if addr >= thisStart:
					self.contentWidget.setByte(addr - thisStart,
								   value)
				addr += 1
		self._updateSize()
		return True

class State_LCD(StateWindow):
	def __init__(self, client, parent=None):
		StateWindow.__init__(self, client, parent)
		self.setWindowTitle("LCD")
		self.setWindowIcon(getIcon("lcd"))

		self.displayedValue = 0

		self.addrSpin = QSpinBox(self)
		self.addrSpin.setPrefix("Q ")
		self.addrSpin.setMinimum(0)
		self.addrSpin.setMaximum(0xFFFF)
		self.layout().addWidget(self.addrSpin, 0, 0)

		self.widthCombo = QComboBox(self)
		self.widthCombo.addItem("Byte", 8)
		self.widthCombo.addItem("Word", 16)
		self.widthCombo.addItem("DWord", 32)
		self.layout().addWidget(self.widthCombo, 0, 1)

		self.endianCombo = QComboBox(self)
		self.endianCombo.addItem("Big-endian", "be")
		self.endianCombo.addItem("Little-endian", "le")
		self.layout().addWidget(self.endianCombo, 1, 0)

		self.fmtCombo = QComboBox(self)
		self.fmtCombo.addItem("BCD", "bcd")
		self.fmtCombo.addItem("Signed BCD", "signed-bcd")
		self.fmtCombo.addItem("Binary", "bin")
		self.fmtCombo.addItem("Signed binary", "signed-bin")
		self.layout().addWidget(self.fmtCombo, 1, 1)

		self.lcd = QLCDNumber(self)
		self.lcd.setMinimumHeight(50)
		self.layout().addWidget(self.lcd, 2, 0, 1, 2)

		self.addrSpin.valueChanged.connect(self.rebuild)
		self.widthCombo.currentIndexChanged.connect(self.rebuild)
		self.endianCombo.currentIndexChanged.connect(self.rebuild)
		self.fmtCombo.currentIndexChanged.connect(self.rebuild)

		self.__changeBlocked = Blocker()
		self.rebuild()

	def getDataWidth(self):
		index = self.widthCombo.currentIndex()
		return self.widthCombo.itemData(index)

	def getFormat(self):
		index = self.fmtCombo.currentIndex()
		return self.fmtCombo.itemData(index)

	def getEndian(self):
		index = self.endianCombo.currentIndex()
		return self.endianCombo.itemData(index)

	def rebuild(self):
		self._updateSize(forceMinimum = True)
		self.configChanged.emit(self)

	def __makeMemoryArea(self):
		nrBits = self.widthCombo.itemData(self.widthCombo.currentIndex())
		addr = self.addrSpin.value()

		return MemoryArea(memType = MemoryArea.TYPE_A,
				  flags = 0,
				  index = 0,
				  start = addr,
				  length = nrBits // 8)

	def getMemoryAreas(self):
		return ( self.__makeMemoryArea(), )

	def setMemory(self, memArea):
		thisArea = self.__makeMemoryArea()
		if not thisArea.overlapsWith(memArea):
			return False
		thisStart, thisEnd = thisArea.start, thisArea.start + thisArea.length - 1

		if memArea.flags & (memArea.FLG_ERR_READ | memArea.FLG_ERR_WRITE):
			#TODO
			return False

		with self.__changeBlocked:
			addr = memArea.start
			for value in memArea.data:
				if addr > thisEnd:
					break
				if addr >= thisStart:
					self.__setByte(addr - thisStart,
						       value)
				addr += 1
		self._updateSize()
		return True

	def __setByte(self, offset, value):
		width = self.getDataWidth()
		mask = ~(0xFF << (width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (value << (width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (self.displayedValue & mask) | value
		if self.displayedValue != value:
			self.displayedValue = value
			self.__displayValue()

	def __displayValue(self):
		addr = self.addrSpin.value()
		width = self.getDataWidth()
		fmt = self.getFormat()
		endian = self.getEndian()
		value = self.displayedValue

		if endian == "le":
			if width == 16:
				value = swapEndianWord(value)
			elif width == 32:
				value = swapEndianDWord(value)

		if fmt == "bcd":
			if width == 8:
				value = "%02X" % (value & 0xFF)
			elif width == 16:
				value = "%04X" % (value & 0xFFFF)
			elif width == 32:
				value = "%08X" % (value & 0xFFFFFFFF)
			else:
				assert(0)
		elif fmt == "signed-bcd":
			if width == 8:
				sign = '-' if (value & 0xF0) else ''
				value = "%s%01X" % (sign, value & 0x0F)
			elif width == 16:
				sign = '-' if (value & 0xF000) else ''
				value = "%s%03X" % (sign, value & 0x0FFF)
			elif width == 32:
				sign = '-' if (value & 0xF0000000) else ''
				value = "%s%07X" % (sign, value & 0x0FFFFFFF)
			else:
				assert(0)
		elif fmt == "bin":
			if width == 8:
				value = "%d" % (value & 0xFF)
			elif width == 16:
				value = "%d" % (value & 0xFFFF)
			elif width == 32:
				value = "%d" % (value & 0xFFFFFFFF)
			else:
				assert(0)
		elif fmt == "signed-bin":
			if width == 8:
				value = "%d" % byteToSignedPyInt(value)
			elif width == 16:
				value = "%d" % wordToSignedPyInt(value)
			elif width == 32:
				value = "%d" % dwordToSignedPyInt(value)
			else:
				assert(0)
		else:
			assert(0)
		with self.__changeBlocked:
			self.lcd.setDigitCount(len(value))
			self.lcd.display(value)

class _State_TimerCounter(StateWindow):
	def __init__(self, client, memAreaType, parent=None):
		StateWindow.__init__(self, client, parent)
		self.memAreaType = memAreaType

		self.indexSpin = QSpinBox(self)
		self.indexSpin.setMinimum(0)
		self.indexSpin.setMaximum(0xFFFF)
		self.layout().addWidget(self.indexSpin, 0, 0)

		self.formatCombo = QComboBox(self)
		self.layout().addWidget(self.formatCombo, 0, 1)

		hbox = QHBoxLayout()
		self.valueEdit = ValueLineEdit(self.__validateInput, self)
		hbox.addWidget(self.valueEdit)
		self.statusLabel = QLabel(self)
		self.__statusLabelOrigColor = self.statusLabel.palette().color(QPalette.Window)
		self.__statusLabelActColor = QColor(StateWindow.COLOR_ACTIVE)
		hbox.addWidget(self.statusLabel)
		self.resetButton = QPushButton("R", self)
		hbox.addWidget(self.resetButton)
		self.layout().addLayout(hbox, 1, 0, 1, 2)

		self.displayedStatus = 0

		self.indexSpin.valueChanged.connect(self.rebuild)
		self.formatCombo.currentIndexChanged.connect(self.rebuild)
		self.valueEdit.valueChanged.connect(self.__newValueEntered)
		self.resetButton.released.connect(self.reset)

		self.__changeBlocked = Blocker()
		self.setMinimumWidth(310)
		self.rebuild()

	def reset(self):
		self.__sendValue(0)

	def __updateStatus(self):
		self.statusLabel.setText("Q=%d" % self.displayedStatus)
		pal = self.statusLabel.palette()
		if self.displayedStatus == 0:
			color = self.__statusLabelOrigColor
			fill = False
		else:
			color = self.__statusLabelActColor
			fill = True
		if pal.color(QPalette.Window) != color:
			pal.setColor(QPalette.Window, color)
			self.statusLabel.setAutoFillBackground(fill)
			self.statusLabel.setPalette(pal)

	def rebuild(self):
		self.valueEdit.clear()
		self.displayedStatus = 0
		self.__updateStatus()
		self._updateSize(forceMinimum = True)
		self.configChanged.emit(self)

	def __makeMemoryArea(self):
		index = self.indexSpin.value()
		return MemoryArea(memType = self.memAreaType,
				  flags = 0,
				  index = index,
				  start = 0,
				  length = 32)

	def getMemoryAreas(self):
		return ( self.__makeMemoryArea(), )

	def setMemory(self, memArea):
		if memArea.memType != self.memAreaType or\
		   memArea.index != self.indexSpin.value():
			return False

		if memArea.flags & (memArea.FLG_ERR_READ | memArea.FLG_ERR_WRITE):
			self.valueEdit.setEnabled(False)
			self.valueEdit.clear()
			return False
		self.valueEdit.setEnabled(True)

		try:
			value = WordPacker.fromBytes(memArea.data, 32)
			status = (value >> 31) & 1
			value &= 0xFFFF
		except AwlSimError as e:
			return False
		text = self.valueToText(value)
		if text == self.valueEdit.text() and\
		   status == self.displayedStatus:
			return True

		self.displayedStatus = status
		self.__updateStatus()

		with self.__changeBlocked:
			self.valueEdit.setText(text)

		self._updateSize()
		return True

	def textToValue(self, text):
		raise NotImplementedError

	def valueToText(self, value):
		raise NotImplementedError

	def __validateInput(self, inputString, pos):
		if self.textToValue(inputString) is None:
			return QValidator.Intermediate
		return QValidator.Acceptable

	def __newValueEntered(self, newText):
		if self.__changeBlocked:
			return

		value = self.textToValue(newText)
		if value is not None:
			self.__sendValue(value)

	def __sendValue(self, value):
		memArea = self.__makeMemoryArea()
		memArea.data = bytearray(4)
		WordPacker.toBytes(memArea.data, 32, 0, value)
		self._writeCpuMemory((memArea,))

class State_Timer(_State_TimerCounter):
	def __init__(self, client, parent=None):
		_State_TimerCounter.__init__(self, client,
					     MemoryArea.TYPE_T,
					     parent)
		self.setWindowTitle("Timer")
		self.setWindowIcon(getIcon("timer"))

		self.indexSpin.setPrefix("T ")

		self.formatCombo.addItem("Dual", "bin")
		self.formatCombo.addItem("Hexadecimal", "hex")
		self.formatCombo.addItem("S5Time", "s5t")

		self._updateSize(forceMinimum = True)

	def textToValue(self, text):
		fmt = self.formatCombo.itemData(self.formatCombo.currentIndex())
		if fmt == "s5t":
			try:
				val = AwlDataType.tryParseImmediate_S5T(text)
				if val is None:
					return None
			except AwlSimError as e:
				return None
		elif fmt == "bin":
			try:
				val = AwlDataType.tryParseImmediate_Bin(text)
				if val is None:
					return None
				if val > 0xFFFF:
					return None
			except AwlSimError as e:
				return None
		elif fmt == "hex":
			try:
				val = AwlDataType.tryParseImmediate_HexWord(text)
				if val is None:
					return None
			except AwlSimError as e:
				return None
		else:
			assert(0)
		if (val & 0xF000) > 0x3000 or\
		   (val & 0x0F00) > 0x0900 or\
		   (val & 0x00F0) > 0x0090 or\
		   (val & 0x000F) > 0x0009:
			return None
		return val

	def valueToText(self, value):
		value &= 0xFFFF
		fmt = self.formatCombo.itemData(self.formatCombo.currentIndex())
		if fmt == "s5t":
			try:
				seconds = Timer.s5t_to_seconds(value)
				return "S5T#" + AwlDataType.formatTime(seconds, True)
			except AwlSimError as e:
				return ""
		elif fmt == "bin":
			text = "2#" + intToDualString(value, 16)
		elif fmt == "hex":
			text = "W#16#%04X" % value
		else:
			assert(0)
		return text

class State_Counter(_State_TimerCounter):
	def __init__(self, client, parent=None):
		_State_TimerCounter.__init__(self, client,
					     MemoryArea.TYPE_Z,
					     parent)
		self.setWindowTitle("Counter")
		self.setWindowIcon(getIcon("counter"))

		self.indexSpin.setPrefix("C ")

		self.formatCombo.addItem("BCD (counter)", "bcd")
		self.formatCombo.addItem("Dual", "bin")

		self._updateSize(forceMinimum = True)

	def textToValue(self, text):
		fmt = self.formatCombo.itemData(self.formatCombo.currentIndex())
		if fmt == "bin":
			try:
				val = AwlDataType.tryParseImmediate_Bin(text)
				if val is None:
					return None
				if val > 0xFFFF:
					return None
			except AwlSimError as e:
				return None
		elif fmt == "bcd":
			try:
				val = AwlDataType.tryParseImmediate_BCD_word(text)
				if val is None:
					return None
			except AwlSimError as e:
				return None
		else:
			assert(0)
		if val > 0x999 or\
		   (val & 0x0F00) > 0x0900 or\
		   (val & 0x00F0) > 0x0090 or\
		   (val & 0x000F) > 0x0009:
			return None
		return val

	def valueToText(self, value):
		value &= 0xFFFF
		fmt = self.formatCombo.itemData(self.formatCombo.currentIndex())
		if fmt == "bin":
			text = "2#" + intToDualString(value, 16)
		elif fmt == "bcd":
			text = "C#%X" % value
		else:
			assert(0)
		return text

class State_Blocks(StateWindow):
	def __init__(self, client, parent=None):
		StateWindow.__init__(self, client, parent)
		self.setWindowTitle("CPU online content (downloaded blocks)")
		self.setWindowIcon(getIcon("plugin"))

		self.__modelRef = client.getBlockTreeModelRef()

		self.blockTree = BlockTreeView(self.__modelRef.obj, self)
		self.layout().addWidget(self.blockTree, 0, 0)

		self.setMinimumSize(450, 320)
		self._updateSize()

	def closeEvent(self, ev):
		self.__modelRef.destroy()
		self.__modelRef = None
		StateWindow.closeEvent(self, ev)

class StateMdiArea(QMdiArea):
	pass

class StateMdiSubWindow(QMdiSubWindow):
	closed = Signal(QMdiSubWindow)

	def __init__(self, childWidget):
		QMdiSubWindow.__init__(self)
		self.setWidget(childWidget)
		childWidget.setParent(self)
		self.setAttribute(Qt.WA_DeleteOnClose)

	def closeEvent(self, ev):
		self.closed.emit(self)
		QMdiSubWindow.closeEvent(self, ev)
