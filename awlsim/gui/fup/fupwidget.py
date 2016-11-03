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
from awlsim.gui.util import *


FUP_DEBUG = 1


class FupFactory(XmlFactory):
	FUP_VERSION = 0

	def parser_open(self):
		self.inFup = False
		XmlFactory.parser_open(self)

	def parser_beginTag(self, tag):
		grid = self.fupWidget.draw.grid
		if self.inFup:
			if tag.name == "grid":
				self.parser_switchTo(grid.factory(grid=grid))
				return
		else:
			if tag.name == "FUP":
				version = tag.getAttrInt("version")
				if version != self.FUP_VERSION:
					raise self.Error("Invalid FUP version. "
						"Got %d, but expected %d." % (
						version, self.FUP_VERSION))
				self.inFup = True
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "FUP":
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		grid = self.fupWidget.draw.grid
		gridTags = grid.factory(grid=grid).composer_getTags()
		tags = [
			self.Tag(name="FUP",
				attrs={"version" : self.FUP_VERSION},
				tags=gridTags),
		]
		return tags

class FupWidget(QWidget):
	"""Main FUP/FBD widget."""

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.setLayout(QGridLayout())

		self.__source = FupSource(name = "FUP")
		self.__needSourceUpdate = True

		self.draw = FupDrawWidget(self)
		self.drawScroll = QScrollArea(self)
		self.drawScroll.setWidget(self.draw)
		self.layout().addWidget(self.drawScroll, 0, 0)

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
#XXX		self.__needSourceUpdate = False

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
