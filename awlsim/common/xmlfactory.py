# -*- coding: utf-8 -*-
#
# XML factory - parser and composer
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

from awlsim.common.util import *

import xml.etree.ElementTree
import xml.sax.saxutils as saxutils


class _XmlFactoryBuilder(object):
	def __init__(self, xmlFactory):
		self.__factoryList = []
		self.__tags = []
		self.pushFactory(xmlFactory)

	def start(self, tagName, attrs):
		try:
			xmlFactory = self.__factoryList[-1]
		except IndexError:
			raise XmlFactory.Error("Starting tag, but "
				"no factory object is available.")
		tag = xmlFactory.Tag(name=tagName,
				     attrs=attrs)
		self.__tags.append(tag)
		xmlFactory.parser_beginTag(tag)

	def end(self, tagName):
		try:
			xmlFactory = self.__factoryList[-1]
		except IndexError:
			raise XmlFactory.Error("Closing tag, but "
				"no factory object is available.")
		tag = None
		while tag is None or tag.name != tagName:
			try:
				tag = self.__tags.pop()
			except IndexError:
				raise XmlFactory.Error("Closing tag <%s>, "
					"which is not open." % tagName)
		xmlFactory.parser_endTag(tag)

	def data(self, data):
		try:
			xmlFactory = self.__factoryList[-1]
		except IndexError:
			raise XmlFactory.Error("Receiving tag data, but "
				"no factory object is available.")
		xmlFactory.parser_data(data)

	def close(self):
		while self.__factoryList:
			self.popFactory(self.__factoryList[-1])
		self.__tags = []
		return None

	def pushFactory(self, xmlFactory):
		self.__factoryList.append(xmlFactory)
		xmlFactory.builder = self
		xmlFactory.parser_open(self.__tags[-1] if self.__tags else None)

	def popFactory(self, xmlFactory):
		try:
			oldFactory = self.__factoryList.pop()
			oldFactory.parser_close()
			assert(oldFactory is xmlFactory)
		except IndexError:
			pass

class XmlFactoryError(Exception):
	pass

class XmlFactory(object):
	"""XML parser and factory."""

	XML_VERSION	= "1.0"
	XML_ENCODING	= "UTF-8"

	Error = XmlFactoryError

	class Tag(object):
		class NoDefault: pass

		def __init__(self, name, attrs = None,
			     tags = None, data = None,
			     emitEmptyAttrs = False,
			     emitEmptyTag = False):
			self.name = name			# Tag name
			self.attrs = attrs or {}		# Tag attributes
			self.tags = tags or []			# Child tags
			self.data = data or ""			# Tag data
			self.emitEmptyAttrs = emitEmptyAttrs	# Emit attributes with empty data?
			self.emitEmptyTag = emitEmptyTag	# Emit tag, if it is completely empty?

		def hasAttr(self, name):
			return name in self.attrs

		def getAttr(self, name, default=NoDefault):
			try:
				return self.attrs[name]
			except KeyError:
				if default is self.NoDefault:
					raise XmlFactory.Error("Tag <%s> attribute "
						"'%s' does not exist." % (
						self.name, name))
			return default

		def getAttrInt(self, name, default=NoDefault):
			try:
				return int(self.attrs[name])
			except KeyError:
				if default is self.NoDefault:
					raise XmlFactory.Error("Tag <%s> attribute "
						"'%s' does not exist." % (
						self.name, name))
			except ValueError:
				if default is self.NoDefault:
					raise XmlFactory.Error("Tag <%s> attribute "
						"'%s' is not an integer." % (
						self.name, name))
			return default

		def getAttrBool(self, name, default=NoDefault):
			return bool(self.getAttrInt(name,
				default if default is self.NoDefault else int(bool(default))))

	def __init__(self, **kwargs):
		self.__kwargs = kwargs
		self.builder = None

	def __getattr__(self, name):
		with contextlib.suppress(KeyError):
			return self.__kwargs[name]
		raise AttributeError

	def parser_open(self, tag=None):
		pass

	def parser_close(self):
		pass

	def parser_beginTag(self, tag):
		printWarning("[XML-parser - %s] Unhandled tag: <%s>" % (
			     type(self).__name__, tag.name))

	def parser_endTag(self, tag):
		printWarning("[XML-parser - %s] Unhandled tag: </%s>" % (
			     type(self).__name__, tag.name))

	def parser_data(self, data):
		data = data.strip()
		if data:
			printWarning("[XML-parser - %s] Unhandled data: %s" % (
				     type(self).__name__, data))

	def composer_getTags(self):
		raise NotImplementedError

	def compose(self):
		self.builder = None
		def tags2text(tags, indent=0):
			ret = []
			for tag in tags:
				ind = "\t" * indent
				# Force convert attrs to str and remove empty attrs
				attrs = { str(aName) : str(aVal)
					  for aName, aVal in dictItems(tag.attrs)
					  if tag.emitEmptyAttrs or str(aVal)
				}
				# Convert atts to XML
				attrText = (" " + " ".join(
					"%s=%s" % (aName, saxutils.quoteattr(aVal))
					for aName, aVal in sorted(dictItems(attrs),
								  key=lambda a: a[0])
				)).rstrip()
				# Convert the child tags to XML
				if tag.tags:
					childTags = tags2text(tag.tags, indent + 1)
				else:
					childTags = []
				# Convert tags to XML
				if tag.data or childTags:
					ret.append(
						"%s<%s%s>%s" % (
						ind,
						tag.name,
						attrText,
						saxutils.escape(tag.data or ""))
					)
					ret.extend(childTags)
					ret.append("%s</%s>" % (
						ind,
						tag.name)
					)
				elif attrs or tag.emitEmptyTag:
					ret.append(
						"%s<%s%s />" % (
						ind,
						tag.name,
						attrText)
					)
			return ret
		lines = [ '<?xml version="%s" encoding="%s" standalone="yes"?>' % (
			  self.XML_VERSION, self.XML_ENCODING) ]
		lines.extend(tags2text(self.composer_getTags()))
		return "\n".join(lines).encode(self.XML_ENCODING)

	def parser_switchTo(self, otherFactory):
		self.builder.pushFactory(otherFactory)

	def parser_finish(self):
		self.builder.popFactory(self)

	def parse(self, xmlText):
		if not xmlText.decode(self.XML_ENCODING).strip():
			return False
		try:
			builder = _XmlFactoryBuilder(self)
			parser = xml.etree.ElementTree.XMLParser(target=builder)
			self.parser_open(None)
			parser.feed(xmlText)
			parser.close()
		except xml.etree.ElementTree.ParseError as e:
			raise XmlFactory.Error("Failed to parse "
				"XML data: %s" % str(e))
		return True
