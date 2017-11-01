# -*- coding: utf-8 -*-
#
# AWL simulator - FUP draw widget
#
# Copyright 2016 Michael Buesch <m@bues.ch>
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

from awlsim.common.xmlfactory import *

from awlsim.gui.icons import *
from awlsim.gui.util import *
from awlsim.gui.fup.fup_grid import *

import traceback


class FupContextMenu(QMenu):
	"""FUP/FBD draw widget context menu."""

	edit = Signal()
	remove = Signal()
	invertConn = Signal()
	addInput = Signal()
	addOutput = Signal()
	removeConn = Signal()
	disconnWire = Signal()
	customAction = Signal(int)

	NR_CUSTOM = 10

	def __init__(self, parent=None):
		QMenu.__init__(self, parent)

		self.gridX = 0
		self.gridY = 0

		self.__actEdit = self.addAction(getIcon("doc_edit"),
						"&Edit element...",
						self.__edit)
		self.__actDel = self.addAction(getIcon("doc_close"),
					       "&Remove element", self.__del)
		self.addSeparator()
		self.__actInvertConn = self.addAction(getIcon("doc_edit"),
						      "In&vert connection",
						      self.__invertConn)
		self.__actAddInp = self.addAction(getIcon("new"),
						  "Add input &connection",
						  self.__addInput)
		self.__actAddOut = self.addAction(getIcon("new"),
						  "Add &output connection",
						  self.__addOutput)
		self.__actDelConn = self.addAction(getIcon("doc_close"),
						   "Remove &connection",
						   self.__delConn)
		self.__actDisconnWire = self.addAction(getIcon("doc_close"),
						       "&Disconnect wire",
						       self.__disconnWire)
		self.addSeparator()
		self.__actCustom = []
		for i in range(self.NR_CUSTOM):
			self.__actCustom.append(
				self.addAction(getIcon("doc_edit"),
					       "custom %d" % i,
					       lambda i=i: self.__customAction(i))
			)

	def __edit(self):
		self.edit.emit()

	def __del(self):
		self.remove.emit()

	def __invertConn(self):
		self.invertConn.emit()

	def __addInput(self):
		self.addInput.emit()

	def __addOutput(self):
		self.addOutput.emit()

	def __delConn(self):
		self.removeConn.emit()

	def __disconnWire(self):
		self.disconnWire.emit()

	def __customAction(self, index):
		self.customAction.emit(index)

	def enableEdit(self, en=True):
		self.__actEdit.setVisible(en)

	def enableRemove(self, en=True):
		self.__actDel.setVisible(en)

	def enableInvertConn(self, en=True):
		self.__actInvertConn.setVisible(en)

	def enableAddInput(self, en=True):
		self.__actAddInp.setVisible(en)

	def enableAddOutput(self, en=True):
		self.__actAddOut.setVisible(en)

	def enableRemoveConn(self, en=True):
		self.__actDelConn.setVisible(en)

	def enableDisconnWire(self, en=True):
		self.__actDisconnWire.setVisible(en)

	def enableCustomAction(self, index, en=True, text=None, iconName=None):
		if index < 0 or index >= len(self.__actCustom):
			return
		action = self.__actCustom[index]
		action.setVisible(en)
		if text is not None:
			action.setText(text)
		if iconName is not None:
			action.setIcon(getIcon(iconName))

class FupDrawWidget(QWidget):
	"""FUP/FBD draw widget."""

	# Base pixel width/height of a grid cell.
	GRID_PIX_BASE = (90, 20)

	# Zoom factor limits
	MIN_ZOOM = 1.0
	MAX_ZOOM = 4.0

	# Signal: Something in the FUP diagram changed
	diagramChanged = Signal()

	def __init__(self, parent, interfWidget):
		"""parent => Parent QWidget().
		interfWidget => AwlInterfWidget() instance
		"""
		QWidget.__init__(self, parent)

		self.__interfWidget = interfWidget

		self.__suppressMousePress = 0
		self.__repaintBlocked = Blocker()

		self.__contextMenu = FupContextMenu(self)
		self.__contextMenu.remove.connect(self.removeElems)
		self.__contextMenu.edit.connect(self.editElems)
		self.__contextMenu.invertConn.connect(self.invertElemConn)
		self.__contextMenu.addInput.connect(self.addElemInput)
		self.__contextMenu.addOutput.connect(self.addElemOutput)
		self.__contextMenu.removeConn.connect(self.removeElemConn)
		self.__contextMenu.disconnWire.connect(self.disconnectConn)
		self.__contextMenu.customAction.connect(self.__elemCustomAction)

		self.__bgBrush = QBrush(QColor("#F5F5F5"))
		self.__gridPen = QPen(QColor("#E0E0E0"))
		self.__gridPen.setWidth(1)
		self.__textPen = QColor("#808080")
		self.__dragConnPenOpen = QPen(QColor("#FF0000"))
		self.__dragConnPenOpen.setWidth(4)
		self.__dragConnPenClosed = QPen(QColor("#000000"))
		self.__dragConnPenClosed.setWidth(4)
		self.__selRectPen = QPen(QColor("#0000FF"))
		self.__selRectPen.setWidth(3)

		# Start and end pixel coordinates of a selection rectangle.
		self.__selectStartPix = None
		self.__selectEndPix = None

		# Start grid coordinates of an element drag.
		self.__dragStart = None
		self.__checkWireCollAfterDrag = False

		# The dragged connection.
		self.__draggedConn = None

		self.__zoom = 1.0
		self.__wheelSteps = 0.0

		self.__gridMinSize = (12, 18)	# Smallest possible grid size
		self.__gridClearance = (3, 4)	# Left and bottom clearance

		self.__grid = FupGrid(self, self.__gridMinSize[0],
				      self.__gridMinSize[1])
		self.__grid.resizeEvent = self.__handleGridResize

		self.__handleZoomChange()

		self.setFocusPolicy(Qt.FocusPolicy(Qt.ClickFocus | Qt.WheelFocus | Qt.StrongFocus))
		self.setMouseTracking(True)
		self.setAcceptDrops(True)

	@property
	def interfDef(self):
		"""Get the block interface definition (AwlInterfDef() instance).
		"""
		return self.__interfWidget.interfDef

	def getFont(self, size=8, bold=False):
		"""Get a font.
		"""
		size = int(round(size * self.__zoom))
		return getDefaultFixedFont(size, bold=bold)

	@property
	def zoom(self):
		"""Get the current zoom level.
		Returns a float between MIN_ZOOM and MAX_ZOOM.
		1.0 corresponds to 100% zoom.
		"""
		return self.__zoom

	@zoom.setter
	def zoom(self, zoom):
		self.__zoom = zoom
		self.__handleZoomChange()

	def __handleZoomChange(self):
		"""Handle a change in zoom and trigger a redraw.
		"""
		self.__zoom = clamp(self.__zoom, self.MIN_ZOOM, self.MAX_ZOOM)

		self.__cellWidth = int(round(max(self.GRID_PIX_BASE[0] * self.__zoom,
						 self.GRID_PIX_BASE[0])))
		self.__cellHeight = int(round(max(self.GRID_PIX_BASE[1] * self.__zoom,
						  self.GRID_PIX_BASE[1])))

		self.__handleGridResize(self.__grid.width, self.__grid.height)

		self.repaint()
		self.diagramChanged.emit()

	def __handleGridResize(self, gridWidth, gridHeight):
		"""Handle a change in grid size and resize the widget.
		"""
		self.resize(gridWidth * self.__cellWidth,
			    gridHeight * self.__cellHeight)

	def __dynGridExpansion(self):
		"""Expand the grid, if required.
		"""
		maxWidth = maxHeight = 0
		if self.__grid.elems:
			maxWidth = max(e.x + e.width for e in self.__grid.elems)
			maxHeight = max(e.y + e.height for e in self.__grid.elems)
		gridWidth = max(maxWidth + self.__gridClearance[0],
				self.__gridMinSize[0])
		gridHeight = max(maxHeight + self.__gridClearance[1],
				 self.__gridMinSize[1])
		self.__grid.resize(gridWidth, gridHeight)

	def repaint(self):
		if not self.__repaintBlocked:
			QWidget.repaint(self)

	def __contentChanged(self):
		self.__dynGridExpansion()
		self.repaint()
		self.diagramChanged.emit()

	@property
	def grid(self):
		return self.__grid

	@property
	def cellPixHeight(self):
		return self.__cellHeight

	@property
	def cellPixWidth(self):
		return self.__cellWidth

	def addElem(self, elem):
		if self.__grid:
			if self.__grid.placeElem(elem):
				self.__grid.deselectAll()
				self.__grid.selectElem(elem)
				elem.establishAutoConns()
				self.__contentChanged()
				return True
		return False

	def removeElem(self, elem):
		if self.__grid:
			self.__grid.removeElem(elem)
			self.__contentChanged()

	def removeElems(self, elems=None):
		if self.__grid:
			if not elems:
				elems = self.__grid.selectedElems
			with self.__repaintBlocked:
				for elem in elems.copy():
					self.removeElem(elem)
			self.__contentChanged()

	def moveElem(self, elem, toGridX, toGridY,
		     relativeCoords=False,
		     checkOnly=False,
		     excludeCheckElems=set()):
		if self.__grid.moveElemTo(elem, toGridX, toGridY,
					  relativeCoords=relativeCoords,
					  checkOnly=checkOnly,
					  excludeCheckElems=excludeCheckElems):
			if not checkOnly:
				self.__contentChanged()
			return True
		return False

	def establishWire(self, fromConn, toConn):
		if fromConn and toConn:
			if fromConn.canConnectTo(toConn):
				with contextlib.suppress(ValueError):
					fromConn.connectTo(toConn)
					self.__contentChanged()

	def disconnectConn(self, conn=None):
		if self.__grid:
			if not conn:
				conn = self.__grid.clickedConn
			if conn:
				conn.disconnect()
				self.__contentChanged()

	def editElems(self, elems=None):
		if self.__grid:
			chg = 0
			if not elems:
				elems = self.__grid.selectedElems
			for elem in elems:
				chg += int(elem.edit(self))
			if chg:
				self.__contentChanged()

	def addElemInput(self, elem=None):
		if self.__grid:
			if not elem:
				elem = self.__grid.clickedElem
			if elem:
				if elem.addConn(FupConnIn()):
					self.__contentChanged()

	def addElemOutput(self, elem=None):
		if self.__grid:
			if not elem:
				elem = self.__grid.clickedElem
			if elem:
				if elem.addConn(FupConnOut()):
					self.__contentChanged()

	def invertElemConn(self, conn=None):
		if self.__grid:
			if not conn:
				conn = self.__grid.clickedConn
			if conn and conn.elem:
				if conn.elem.setConnInverted(conn,
							     not conn.inverted):
					self.__contentChanged()

	def removeElemConn(self, conn=None):
		if self.__grid:
			if not conn:
				conn = self.__grid.clickedConn
			if conn:
				if conn.removeFromElem():
					self.__contentChanged()

	def __elemCustomAction(self, index):
		if self.__grid:
			elem = self.__grid.clickedElem
			if elem:
				if elem.handleCustomAction(index):
					self.__contentChanged()

	def paintEvent(self, event=None):
		grid = self.__grid
		if not grid:
			return

		# Build a new collision cache.
		grid.collisionCacheClear()

		size = self.size()
		width, height = size.width(), size.height()
		p = QPainter(self)
		p.setFont(self.getFont(9))

		# Draw background
		p.fillRect(self.rect(), self.__bgBrush)

		# Draw the grid
		p.setPen(self.__gridPen)
		# vertical lines
		for x in range(0, width, self.__cellWidth):
			p.drawLine(x, 0, x, height)
			p.drawText(x, -5, self.__cellWidth, self.__cellHeight,
				   Qt.AlignCenter | Qt.AlignTop,
				   str((x // self.__cellWidth) + 1))
		# horizontal lines
		for y in range(0, height, self.__cellHeight):
			p.drawLine(0, y, width, y)
			p.drawText(5, y, self.__cellWidth, self.__cellHeight,
				   Qt.AlignLeft | Qt.AlignVCenter,
				   str((y // self.__cellHeight) + 1))

		# Draw the help text, if the grid is empty.
		if not grid.elems:
			p.setPen(self.__textPen)
			p.setFont(self.getFont(9))
			x, y = self.__cellWidth + 5, self.__cellHeight * 2 - 5
			p.drawText(x, y, width - x, height - y,
				   Qt.AlignLeft | Qt.AlignTop,
				   "Hints:\n"
				   "* To add elements drag&drop them from the FUP/FBD library to the grid\n"
				   "* Left-drag to connect inputs and outputs\n"
				   "* Middle-click to delete connections and wires\n"
				   "* Double-click onto inputs or outputs to create operand boxes\n"
				   "* Use CTRL + Scroll Wheel to zoom")

		# Draw the elements
		def drawElems(wantForeground, wantCollisions):
			prevX, prevY = 0, 0
			for elem in grid.elems:
				xAbs, yAbs = elem.pixCoords
				p.translate(xAbs - prevX, yAbs - prevY)
				prevX, prevY = xAbs, yAbs
				isForeground = elem.selected or elem.expanded
				if wantForeground == isForeground:
					elem.draw(p)
				if wantCollisions:
					grid.collisionCacheAdd(elem.getCollisionLines(p))
			p.translate(-prevX, -prevY)
		# Draw background elements
		drawElems(False, True)

		# Draw the connection wires
		for wire in grid.wires:
			wire.draw(p)

		# Draw foreground elements (selected/expanded)
		drawElems(True, False)

		# Draw the dragged connection
		draggedConn = self.__draggedConn
		if draggedConn and draggedConn.elem:
			xAbs, yAbs = draggedConn.pixCoords
			gridX, gridY = self.posToGridCoords(xAbs, yAbs)
			mousePos = self.mapFromGlobal(QCursor.pos())
			elem, _, _, _, _, elemRelX, elemRelY = self.posToElem(
					mousePos.x(), mousePos.y())
			# Check if we hit a possible target connection
			p.setPen(self.__dragConnPenOpen)
			if elem:
				targetConn = elem.getConnViaPixCoord(elemRelX, elemRelY)
				if targetConn and draggedConn.canConnectTo(targetConn):
					p.setPen(self.__dragConnPenClosed)
			p.drawLine(xAbs, yAbs, mousePos.x(), mousePos.y())

		# Draw selection rectangle
		if self.__selectStartPix and self.__selectEndPix:
			xAbs0 = min(self.__selectStartPix[0], self.__selectEndPix[0])
			yAbs0 = min(self.__selectStartPix[1], self.__selectEndPix[1])
			xAbs1 = max(self.__selectStartPix[0], self.__selectEndPix[0])
			yAbs1 = max(self.__selectStartPix[1], self.__selectEndPix[1])
			selWidth, selHeight = xAbs1 - xAbs0, yAbs1 - yAbs0
			r = 2
			p.setBrush(Qt.NoBrush)
			p.setPen(self.__selRectPen)
			p.drawRoundedRect(xAbs0, yAbs0,
					  selWidth, selHeight,
					  r, r)

	def gridCoordsToQRect(self, gridX, gridY):
		"""Convert grid coordinates to the pixel QRect surrounding that cell.
		"""
		width, height = self.__cellWidth, self.__cellHeight
		return QRect(gridX * width,
			     gridY * height,
			     width,
			     height)

	def posToGridCoords(self, pixX, pixY):
		"""Convert pixel coordinates to grid coordinates.
		"""
		return pixX // self.__cellWidth,\
		       pixY // self.__cellHeight

	def posToElem(self, pixX, pixY):
		"""Convert pixel coordinates to element and element coordinates.
		Returns:
		(FupElem, FupConn, FupElem.AREA_xxx, gridX, gridY, elemRelativePixX, elemRelativePixY)
		"""
		# Get the grid coordinates.
		gridX, gridY = self.posToGridCoords(pixX, pixY)
		# Get the element (if any).
		elem = self.__grid.getElemAt(gridX, gridY)
		# Get the coordinates relative to the element.
		elemRelX = pixX % self.__cellWidth
		elemRelY = pixY % self.__cellHeight
		if elem:
			elemRelX += (gridX - elem.x) * self.__cellWidth
			elemRelY += (gridY - elem.y) * self.__cellHeight
		# Get the connection and area (if any).
		conn, area = None, None
		if elem:
			area, areaIdx = elem.getAreaViaPixCoord(elemRelX, elemRelY)
			if area == FupElem.AREA_INPUT:
				conn = elem.getInput(areaIdx)
			elif area == FupElem.AREA_OUTPUT:
				conn = elem.getOutput(areaIdx)
		return elem, conn, area, gridX, gridY, elemRelX, elemRelY

	def mousePressEvent(self, event):
		if self.__suppressMousePress:
			self.__suppressMousePress -= 1
			return

		x, y = event.x(), event.y()
		modifiers = QGuiApplication.keyboardModifiers()

		def eventHandled():
			event.accept()
			self.repaint()

		# Get the element (if any)
		elem, conn, area, gridX, gridY, elemRelX, elemRelY = self.posToElem(x, y)
		self.__contextMenu.gridX = gridX
		self.__contextMenu.gridY = gridY

		# Store the clicked element for later use
		self.__grid.clickedElem = elem
		self.__grid.clickedConn = conn
		self.__grid.clickedArea = area

		# Handle left button press
		if event.button() == Qt.LeftButton:
			if elem:
				if area in {FupElem.AREA_BODY,
					    FupElem.AREA_BODYOPER}:
					# Start dragging of the selected element(s).
					self.__dragStart = (gridX, gridY)
					if not elem.selected:
						# Select this element.
						if not (modifiers & Qt.ControlModifier):
							self.__grid.deselectAll()
						self.__grid.selectElem(elem)
						eventHandled()
				if conn and (not conn.wire or conn.OUT):
					# Start dragging of the selected connection.
					self.__draggedConn = conn
					eventHandled()
			else:
				# Start a multi-selection
				if not (modifiers & Qt.ControlModifier):
					self.__grid.deselectAll()
				self.__selectStartPix = (x, y)
				self.__selectEndPix = None
				eventHandled()

		# Handle middle button press
		if event.button() == Qt.MidButton:
			self.disconnectConn(conn)
			eventHandled()

		# Handle right button press
		if event.button() == Qt.RightButton:
			if elem and not elem.selected:
				if not (modifiers & Qt.ControlModifier):
					self.__grid.deselectAll()
			self.__grid.selectElem(elem)
			eventHandled()
			# Open the context menu
			self.__contextMenu.enableRemove(elem is not None)
			self.__contextMenu.enableEdit(False)
			self.__contextMenu.enableInvertConn(False)
			self.__contextMenu.enableAddInput(False)
			self.__contextMenu.enableAddOutput(False)
			self.__contextMenu.enableRemoveConn(False)
			self.__contextMenu.enableDisconnWire(False)
			for i in range(self.__contextMenu.NR_CUSTOM):
				self.__contextMenu.enableCustomAction(i, False)
			if elem:
				elem.prepareContextMenu(self.__contextMenu, area, conn)
			self.__contextMenu.exec_(self.mapToGlobal(event.pos()))

		if not event.isAccepted():
			QWidget.mousePressEvent(self, event)

	def mouseReleaseEvent(self, event):
		x, y = event.x(), event.y()
		elem, conn, area, gridX, gridY, elemRelX, elemRelY = self.posToElem(x, y)

		def eventHandled():
			event.accept()
			self.repaint()

		# Handle end of multi-selection
		if self.__selectStartPix:
			self.__selectStartPix = None
			self.__selectEndPix = None
			eventHandled()

		# Handle end of element dragging
		if self.__dragStart:
			# Automatically connect close connections
			connected = any( elem.establishAutoConns()
					 for elem in self.__grid.selectedElems )
			self.__dragStart = None
			# Check wire collisions, if required
			if self.__checkWireCollAfterDrag:
				self.__checkWireCollAfterDrag = False
				self.__grid.checkWireCollisions()
				# Only repaint, if we are not going to repaint anyway.
				if not connected:
					eventHandled()
			if connected:
				self.__contentChanged()
				eventHandled()

		# Handle end of connection dragging
		draggedConn = self.__draggedConn
		if draggedConn:
			# Try to establish the dragged connection.
			if elem:
				targetConn = elem.getConnViaPixCoord(elemRelX, elemRelY)
				self.establishWire(draggedConn, targetConn)
			self.__draggedConn = None
			eventHandled()

		# Drop "clicked element" reference
		if not self.__contextMenu.isVisible():
			self.__grid.clickedElem = None
			self.__grid.clickedConn = None
			self.__grid.clickedArea = FupElem.AREA_NONE
			eventHandled()

		if not event.isAccepted():
			QWidget.mouseReleaseEvent(self, event)

	def mouseMoveEvent(self, event):
		x, y = event.x(), event.y()
		modifiers = QGuiApplication.keyboardModifiers()
		elem, conn, area, gridX, gridY, elemRelX, elemRelY = self.posToElem(x, y)

		def eventHandled():
			event.accept()
			self.repaint()

		# Temporarily expand elements on mouse-over
		if event.buttons() == Qt.NoButton:
			chg = 0
			if elem and area in {FupElem.AREA_BODY,
					     FupElem.AREA_BODYOPER}:
				if elem not in self.__grid.expandedElems:
					chg += int(self.__grid.unexpandAllElems())
					chg += int(self.__grid.expandElem(elem, True, area))
			else:
				chg += int(self.__grid.unexpandAllElems())
			if chg:
				eventHandled()

		# Handle multi-selection
		if self.__selectStartPix:
			self.__selectEndPix = (x, y)
			# Mark all elements within the rectangle as selected.
			startGridX, startGridY = self.posToGridCoords(*self.__selectStartPix)
			clear = not (modifiers & Qt.ControlModifier)
			self.__grid.selectElemsInRect(startGridX, startGridY,
						      gridX, gridY, clear=clear)
			eventHandled()

		# Handle element dragging
		if self.__dragStart:
			deltaX, deltaY = gridX - self.__dragStart[0],\
					 gridY - self.__dragStart[1]
			if deltaX or deltaY:
				with self.__repaintBlocked:
					selectedElems = self.__grid.selectedElems
					# Get all elements that have to be moved
					moveElems = selectedElems.copy()
					for elem in selectedElems:
						moveElems.update(elem.getRelatedElems())
					# First check if we can move all elements
					allOk = True
					for elem in moveElems:
						if not self.moveElem(elem, deltaX, deltaY,
								     relativeCoords=True,
								     checkOnly=True,
								     excludeCheckElems=moveElems):
							allOk = False
							break
					# If everything is Ok, move all elements.
					if allOk:
						for elem in moveElems:
							self.moveElem(elem, deltaX, deltaY,
								      relativeCoords=True,
								      checkOnly=False,
								      excludeCheckElems=moveElems)
						self.__dragStart = (gridX, gridY)
					# Dynamically expand or shrink the grid
					self.__dynGridExpansion()
				self.__checkWireCollAfterDrag = True
				eventHandled()

		# Handle connection dragging
		if self.__draggedConn:
			eventHandled()

		if not event.isAccepted():
			QWidget.mouseMoveEvent(self, event)

	def mouseDoubleClickEvent(self, event):
		x, y = event.x(), event.y()
		elem, conn, area, gridX, gridY, elemRelX, elemRelY = self.posToElem(x, y)

		def eventHandled():
			event.accept()
			self.repaint()

		# Force end of dragging.
		self.__dragStart = None
		self.__draggedConn = None

		# Handle left button double click
		if event.button() == Qt.LeftButton:
			if elem:
				if conn and not conn.isConnected:
					# Double click on an unconnected IN or OUT connection
					# adds a LOAD or ASSIGN operator element.
					connGridX, connGridY = self.posToGridCoords(*conn.pixCoords)
					newElem, newConn = None, None
					if conn.IN and not conn.OUT:
						newElem = FupElem_LOAD(connGridX - 1, connGridY)
						if newElem.outputs:
							newConn = newElem.outputs[0]
					elif conn.OUT and not conn.IN:
						newElem = FupElem_ASSIGN(connGridX + 1, connGridY)
						if newElem.inputs:
							newConn = newElem.inputs[0]
					if newElem and newConn:
						if self.addElem(newElem):
							with contextlib.suppress(ValueError):
								if not newConn.isConnected:
									newConn.connectTo(conn)
								newElem.edit(self)
							self.__contentChanged()
							eventHandled()
				elif conn and conn.isConnected:
					# Double click on a connected IN or OUT connection
					# inverts the connection.
					self.invertElemConn(conn)
					eventHandled()
				else:
					# Edit the element's contents
					if elem.edit(self):
						self.__contentChanged()
						eventHandled()

		# Suppress the next press event
		self.__suppressMousePress += 1

		if not event.isAccepted():
			QWidget.mouseDoubleClickEvent(self, event)

	def wheelEvent(self, ev):
		if ev.modifiers() & Qt.ControlModifier:
			# Ctrl + Scroll-wheel: Zoom
			if isQt4:
				numDegrees = ev.delta() / 8
			else:
				numDegrees = ev.angleDelta().y() / 8
			numSteps = numDegrees / 15

			self.__wheelSteps += numSteps
			self.__zoom += self.__wheelSteps / 10.0
			self.__wheelSteps = self.__wheelSteps % 1.0

			self.__handleZoomChange()

			ev.accept()
			return
		else:
			self.__wheelSteps = 0.0
			ev.ignore()
		QWidget.wheelEvent(self, ev)

	def keyPressEvent(self, event):
		if event.matches(QKeySequence.Delete):
			self.removeElems()
			return
		elif isQt5 and (event.matches(QKeySequence.Cancel) or\
				event.matches(QKeySequence.Deselect)):
			self.__grid.deselectAll()
			self.repaint()
			return
		elif event.matches(QKeySequence.SelectAll):
			for elem in self.__grid.elems:
				self.__grid.selectElem(elem)
			self.repaint()
			return

		QWidget.keyPressEvent(self, event)

	def keyReleaseEvent(self, event):
		QWidget.keyReleaseEvent(self, event)

	def __drop(self, event, checkOnly=False):
		"""Handle a drop event from a Drag&Drop action.
		"""
		def accept(gridX=None, gridY=None):
			if gridX is not None and gridY is not None and\
			   isinstance(event, QDragMoveEvent):
				return event.accept(self.gridCoordsToQRect(gridX, gridY))
			return event.accept()

		def ignore(gridX=None, gridY=None):
			if gridX is not None and gridY is not None and\
			   isinstance(event, QDragMoveEvent):
				return event.ignore(self.gridCoordsToQRect(gridX, gridY))
			return event.ignore()

		if not self.__grid:
			return ignore()

		# Convert the event position to the grid coordinates.
		pos = event.pos()
		gridX, gridY = self.posToGridCoords(pos.x(), pos.y())

		# Get the MIME data from the event.
		mime = event.mimeData()
		if not mime.hasFormat("application/x-awlsim-fup-elem"):
			return ignore()
		mimeData = mime.data("application/x-awlsim-fup-elem")
		if isQt4:
			mimeData = mimeData.data() # QByteArray to bytes/str
		mimeData = bytearray(mimeData)
		if not mimeData:
			return ignore()

#		print("FupDrawWidget.__drop() MIME data:\n" + mimeData.decode("UTF-8"))

		# Parse the MIME data.
		# The data is expected to be a FUP element in XML format.
		newElements = None
		try:
			fakeGrid = FupGridStub()
			elemFactory = FupElem_factory(grid=fakeGrid)
			elemFactory.parse(mimeData)
			newElements = fakeGrid.elements
		except XmlFactory.Error as e:
			return ignore()
		if not newElements:
			return ignore()

		# Recalculate the element positions.
		yOffs = 0
		for newElem in newElements:
			newElem.x = gridX
			newElem.y = gridY + yOffs
			yOffs += newElem.height

		# Check if all elements can be placed.
		for newElem in newElements:
			if not self.__grid.canPlaceElem(newElem):
				return ignore(gridX, gridY)

		# Insert the elements into the grid.
		if not checkOnly:
			for newElem in newElements:
				if not self.addElem(newElem):
					return ignore(gridX, gridY)
			self.setFocus(Qt.OtherFocusReason)

		return accept(gridX, gridY)

	def dragEnterEvent(self, event):
		try:
			self.__drop(event, checkOnly=True)
		except Exception as e:
			printError("Unexpected exception in "
				"FupDrawWidget.dragEnterEvent(): "
				"%s\n\n%s" % (
				str(e), traceback.format_exc()))

	def dragLeaveEvent(self, event):
		try:
			event.accept()
		except Exception as e:
			printError("Unexpected exception in "
				"FupDrawWidget.dragLeaveEvent(): "
				"%s\n\n%s" % (
				str(e), traceback.format_exc()))

	def dragMoveEvent(self, event):
		try:
			self.__drop(event, checkOnly=True)
		except Exception as e:
			printError("Unexpected exception in "
				"FupDrawWidget.dragMoveEvent(): "
				"%s\n\n%s" % (
				str(e), traceback.format_exc()))

	def dropEvent(self, event):
		try:
			self.__drop(event)
		except Exception as e:
			printError("Unexpected exception in "
				"FupDrawWidget.dropEvent(): "
				"%s\n\n%s" % (
				str(e), traceback.format_exc()))
