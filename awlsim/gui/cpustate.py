# -*- coding: utf-8 -*-
#
# AWL simulator - GUI CPU state widgets
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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


class StateWindow(QWidget):
	# Window-close signal
	closed = Signal(QWidget)
	# Config-change (address, type, etc...) signal
	configChanged = Signal(QWidget)

	def __init__(self, client, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))
		pixmap = QPixmap(16, 16)
		pixmap.fill(QColor(0, 0, 192))
		self.setWindowIcon(QIcon(pixmap))
		self.client = client

	def update(self):
		size, hint = self.size(), self.minimumSizeHint()
		if size.width() < hint.width() or\
		   size.height() < hint.height():
			self.resize(hint)

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

class State_CPU(StateWindow):
	def __init__(self, client, parent=None):
		StateWindow.__init__(self, client, parent)
		self.setWindowTitle("CPU Details")

		self.label = QLabel(self)
		font = self.label.font()
		font.setFamily("Mono")
		font.setFixedPitch(True)
		font.setKerning(False)
		self.label.setFont(font)
		self.layout().addWidget(self.label, 0, 0)

		self.label.setText("No CPU status available, yet.")

	def setDumpText(self, text):
		self.label.setText(text)
		self.update()

class AbstractDisplayWidget(QWidget):
	ADDRSPACE_E		= AwlOperator.MEM_E
	ADDRSPACE_A		= AwlOperator.MEM_A
	ADDRSPACE_M		= AwlOperator.MEM_M
	ADDRSPACE_DB		= AwlOperator.MEM_DB

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

	def __init__(self, client, addrSpace, addr, width, db, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout(self))

		self.client = client
		self.addrSpace = addrSpace
		self.addr = addr
		self.width = width
		self.db = db

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
	def __init__(self, client, addrSpace, addr, width, db,
		     parent=None,
		     displayPushButtons=True):
		AbstractDisplayWidget.__init__(self, client, addrSpace,
					       addr, width, db, parent)

		self.cbs = {}
		self.pbs = {}
		self.prevButtonStates = {}
		y = 0
		for i in range(self.width - 1, -1, -1):
			cb = QCheckBox(str(i), self)
			self.layout().addWidget(cb, y + 0, (self.width - i - 1) % 8)
			self.cbs[i] = cb
			cb.stateChanged.connect(self.changed)
			if displayPushButtons:
				pb = QPushButton("", self)
				self.layout().addWidget(pb, y + 1, (self.width - i - 1) % 8)
				self.pbs[i] = pb
				self.prevButtonStates[i] = False
				pb.pressed.connect(self.__buttonUpdate)
				pb.released.connect(self.__buttonUpdate)
			if i and i % 8 == 0:
				y += 2

		self.update()

	def __buttonUpdate(self):
		for bitNr, pb in self.pbs.items():
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
		for bitNr, cb in self.cbs.items():
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
	def __init__(self, client, base, addrSpace, addr, width, db, parent=None):
		AbstractDisplayWidget.__init__(self, client, addrSpace,
					       addr, width, db, parent)

		self.base = base
		self.displayedValue = -1

		self.line = QLineEdit(self)
		self.line.setAlignment(Qt.AlignRight)
		self.layout().addWidget(self.line)

		self.line.returnPressed.connect(self.__returnPressed)
		self.line.textChanged.connect(self.__textChanged)

		self.update()

	def __returnPressed(self):
		self.changed.emit()

	def __convertValue(self):
		try:
			textValue = self.line.text()
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

	def __textChanged(self):
		self._showValueValidity(self.__convertValue() is not None)

	def get(self):
		value = self.__convertValue()
		if value is None:
			return self.displayedValue
		return value

	def setByte(self, offset, value):
		mask = ~(0xFF << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (value << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (self.displayedValue & mask) | value
		if self.displayedValue != value:
			self.displayedValue = value
			self.__displayValue()

	def __displayValue(self):
		value = self.displayedValue
		if self.base == 2:
			string = []
			for bitnr in range(self.width - 1, -1, -1):
				string.append('1' if ((value >> bitnr) & 1) else '0')
				if bitnr and bitnr % 4 == 0:
					string.append('_')
			string = ''.join(string)
		elif self.base == 10:
			if self.width == 8:
				value &= 0xFF
				if value & 0x80:
					value = -((~value + 1) & 0xFF)
				string = "%d" % value
			elif self.width == 16:
				value &= 0xFFFF
				if value & 0x8000:
					value = -((~value + 1) & 0xFFFF)
				string = "%d" % value
			elif self.width == 32:
				value &= 0xFFFFFFFF
				if value & 0x80000000:
					value = -((~value + 1) & 0xFFFFFFFF)
				string = "%d" % value
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
	def __init__(self, client, addrSpace, addr, width, db, parent=None):
		NumberDisplayWidget.__init__(self, client, 16, addrSpace,
					     addr, width, db, parent)

class DecDisplayWidget(NumberDisplayWidget):
	def __init__(self, client, addrSpace, addr, width, db, parent=None):
		NumberDisplayWidget.__init__(self, client, 10, addrSpace,
					     addr, width, db, parent)

class BinDisplayWidget(NumberDisplayWidget):
	def __init__(self, client, addrSpace, addr, width, db, parent=None):
		NumberDisplayWidget.__init__(self, client, 2, addrSpace,
					     addr, width, db, parent)

class RealDisplayWidget(AbstractDisplayWidget):
	def __init__(self, client, addrSpace, addr, width, db, parent=None):
		AbstractDisplayWidget.__init__(self, client, addrSpace,
					       addr, width, db, parent)

		self.displayedValue = -1

		self.line = QLineEdit(self)
		self.line.setAlignment(Qt.AlignRight)
		self.layout().addWidget(self.line)

		self.line.returnPressed.connect(self.__returnPressed)
		self.line.textChanged.connect(self.__textChanged)

		self.update()

	def __returnPressed(self):
		self.changed.emit()

	def __convertValue(self):
		try:
			value = pyFloatToDWord(float(self.line.text()))
		except ValueError as e:
			return None
		return value

	def __textChanged(self):
		self._showValueValidity(self.__convertValue() is not None)

	def get(self):
		value = self.__convertValue()
		if value is None:
			return self.displayedValue
		return value

	def setByte(self, offset, value):
		mask = ~(0xFF << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (value << (self.width - 8 - (offset * 8))) & 0xFFFFFFFF
		value = (self.displayedValue & mask) | value
		if self.displayedValue != value:
			self.displayedValue = value
			self.__displayValue()

	def __displayValue(self):
		value = self.displayedValue
		if self.width == 32:
			string = str(dwordToPyFloat(value))
		else:
			string = "Not DWORD"
		self.line.setText(string)

class State_Mem(StateWindow):
	def __init__(self, client, addrSpace, parent=None):
		StateWindow.__init__(self, client, parent)

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

		self.__changeBlocked = 0
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
			self.contentWidget = BitDisplayWidget(self.client,
							      self.addrSpace,
							      addr, width, db, self,
							      displayPushButtons=True)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "hex":
			self.contentWidget = HexDisplayWidget(self.client,
							      self.addrSpace,
							      addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "dec":
			self.contentWidget = DecDisplayWidget(self.client,
							      self.addrSpace,
							      addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "bin":
			self.contentWidget = BinDisplayWidget(self.client,
							      self.addrSpace,
							      addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		elif fmt == "real":
			self.contentWidget = RealDisplayWidget(self.client,
							       self.addrSpace,
							       addr, width, db, self)
			self.contentLayout.addWidget(self.contentWidget)
		else:
			assert(0)
		self.contentWidget.changed.connect(self.__changed)
		self.contentWidget.setEnabled(True)
		self.update()
		QTimer.singleShot(0, self.__finalizeRebuild)

		self.configChanged.emit(self)

	def __finalizeRebuild(self):
		self.resize(self.sizeHint())

	def __changed(self):
		if self.__changeBlocked or not self.contentWidget:
			return
		value = self.contentWidget.get()
		width = self.widthCombo.itemData(self.widthCombo.currentIndex())

		memArea = self.__makeMemoryArea()
		memArea.data = bytearray(width // 8)
		WordPacker.toBytes(memArea.data, width, 0, value)

		self.client.writeMemory((memArea,))

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
			return False

		self.__changeBlocked += 1
		addr = memArea.start
		for value in memArea.data:
			if addr > thisEnd:
				break
			if addr >= thisStart:
				self.contentWidget.setByte(addr - thisStart,
							   value)
			addr += 1
		self.__changeBlocked -= 1
		self.update()
		return True

class State_LCD(StateWindow):
	def __init__(self, client, parent=None):
		StateWindow.__init__(self, client, parent)
		self.setWindowTitle("LCD")

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

		self.__changeBlocked = 0
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
		self.update()
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

		self.__changeBlocked += 1
		addr = memArea.start
		for value in memArea.data:
			if addr > thisEnd:
				break
			if addr >= thisStart:
				self.__setByte(addr - thisStart,
					       value)
			addr += 1
		self.__changeBlocked -= 1
		self.update()
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
		self.__changeBlocked += 1
		self.lcd.setDigitCount(len(value))
		self.lcd.display(value)
		self.__changeBlocked -= 1

class StateWorkspace(QWorkspace):
	def __init__(self, parent=None):
		QWorkspace.__init__(self, parent)
