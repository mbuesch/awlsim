# -*- coding: utf-8 -*-
#
# AWL simulator - FUP widget
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

from awlsim.gui.fup.fupdrawwidget import *
from awlsim.gui.interfedit.interfwidget import *
from awlsim.gui.util import *


FUP_DEBUG = 0


class FupFactory(XmlFactory):
	FUP_VERSION = 0

	def parser_open(self, tag=None):
		self.inFup = False
		self.inGrids = False
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		blockTypeEdit = self.fupWidget.interf.blockTypeEdit
		interfModel = self.fupWidget.interf.interfView.model()
		grid = self.fupWidget.draw.grid
		if self.inFup:
			if self.inGrids:
				if tag.name == "grid":
					self.parser_switchTo(grid.factory(grid=grid))
					return
			else:
				if tag.name == "blockdecl":
					self.parser_switchTo(blockTypeEdit.factory(
						blockTypeWidget=blockTypeEdit))
					return
				if tag.name == "interface":
					self.parser_switchTo(interfModel.factory(
						model=interfModel))
					return
				if tag.name == "grids":
					self.inGrids = True
					return
		else:
			if tag.name == "FUP":
				version = tag.getAttrInt("version")
				if version != self.FUP_VERSION:
					raise self.Error("Unsupported FUP version. "
						"Got %d, but expected %d." % (
						version, self.FUP_VERSION))
				self.inFup = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inFup:
			if self.inGrids:
				if tag.name == "grids":
					self.inGrids = False
					return
			else:
				if tag.name == "FUP":
					self.inFup = False
					self.parser_finish()
					return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		childTags = []

		blockTypeEdit = self.fupWidget.interf.blockTypeEdit
		childTags.extend(blockTypeEdit.factory(
			blockTypeWidget=blockTypeEdit).composer_getTags())

		interfModel = self.fupWidget.interf.interfView.model()
		childTags.extend(interfModel.factory(
			model=interfModel).composer_getTags())

		grid = self.fupWidget.draw.grid
		childTags.append(self.Tag(name="grids",
					  tags=grid.factory(grid=grid).composer_getTags()))

		tags = [
			self.Tag(name="FUP",
				attrs={"version" : str(self.FUP_VERSION)},
				tags=childTags),
		]
		return tags

class FupWidget(QWidget):
	"""Main FUP/FBD widget."""

	diagramChanged = Signal()

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())

		self.__source = FupSource(name = "FUP")
		self.__needSourceUpdate = True

		self.splitter = QSplitter(Qt.Vertical)

		self.interf = AwlInterfWidget(self)
		self.interf.contentChanged.connect(self.diagramChanged)
		self.splitter.addWidget(self.interf)

		self.draw = FupDrawWidget(self)
		self.draw.diagramChanged.connect(self.diagramChanged)

		self.drawScroll = QScrollArea(self)
		self.drawScroll.setWidget(self.draw)
		self.splitter.addWidget(self.drawScroll)

		self.layout().addWidget(self.splitter, 0, 0)

		self.diagramChanged.connect(self.__handleDiagramChange)

	def __handleDiagramChange(self):
		self.__needSourceUpdate = True

	def __updateSource(self):
		# Generate XML
		try:
			xmlBytes = FupFactory(fupWidget=self).compose()
		except FupFactory.Error as e:
			raise AwlSimError("Failed to create FUP source: "
				"%s" % str(e))
		if FUP_DEBUG:
			print("Composed FUP XML:")
			print(xmlBytes.decode(FupFactory.XML_ENCODING))
		self.__source.sourceBytes = xmlBytes
		self.__needSourceUpdate = False

	def getSource(self):
		if self.__needSourceUpdate:
			self.__updateSource()
		return self.__source

	def setSource(self, source):
		self.__source = source.dup()
		self.__source.sourceBytes = b""
		# Parse XML
		if FUP_DEBUG:
			print("Parsing FUP XML:")
			print(source.sourceBytes.decode(FupFactory.XML_ENCODING))
		try:
			factory = FupFactory(fupWidget=self).parse(source.sourceBytes)
		except FupFactory.Error as e:
			raise AwlSimError("Failed to parse FUP source: "
				"%s" % str(e))
		pass#TODO
		self.__needSourceUpdate = True
