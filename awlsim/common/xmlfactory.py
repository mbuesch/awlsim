# -*- coding: utf-8 -*-
#
# AWL simulator - XML factory
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

from xml.etree.ElementTree import XMLParser


class _XmlFactoryBuilder(object):
	def __init__(self, xmlFactory):
		self.xmlFactory = xmlFactory

	def start(self, tagName, attrs):
		self.xmlFactory.beginXmlTag(
			self.xmlFactory.Tag(name=tagName,
					    attrs=attrs))

	def end(self, tagName):
		pass#TODO

	def data(self, data):
		pass#TODO

	def close(self):
		pass#TODO

class XmlFactory(object):
	class Tag(object):
		def __init__(self, name, attrs = None,
			     tags = None, data = None):
			self.name = name
			self.attrs = attrs or {}
			self.tags = tags or []
			self.data = data or ""

	def beginXmlTag(self, tag):
		raise NotImplementedError

	def endXmlTag(self, tag):
		raise NotImplementedError

	def xmlData(self, data):
		raise NotImplementedError

	@classmethod
	def toXmlTags(cls, dataObj):
		raise NotImplementedError

	@classmethod
	def toXml(cls, dataObj):
		def tags2text(tags, indent=0):
			ret = []
			for tag in tags:
				ind = "\t" * indent
				attrText = " ".join(
					"%s=\"%s\"" % (aName, aVal)
					for aName, aVal in tag.attrs.iteritems()
				)
				if tag.data:
					ret.append(
						"%s<%s%s />" % (
						ind, tag.name, attrText)
					)
				else:
					ret.append(
						"%s<%s%s>%s</%s>" % (
						ind, tag.name,
						attrText, tag.data, tag.name)
					)
				ret.extend(tags2text(tag.tags, indent + 1))
			return ret
		return "\n".join(tags2text(cls.toXmlTags(dataObj)))

	def fromXml(self, xmlText):
		builder = _XmlFactoryBuilder(self)
		parser = XMLParser(target=builder)
		parser.feed(xmlText)
		parser.close()
