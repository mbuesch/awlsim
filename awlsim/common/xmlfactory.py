# -*- coding: utf-8 -*-
#
# XML factory - parser and composer
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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

from awlsim.common.enumeration import *
from awlsim.common.util import *

import xml.etree.ElementTree
import xml.sax.saxutils as saxutils


__all__ = [ "XmlFactory", ]


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

class _XmlFactoryError(Exception):
	pass

class XmlFactory(object):
	"""XML parser and factory."""

	XML_VERSION	= "1.0"
	XML_ENCODING	= "UTF-8"

	Error = _XmlFactoryError

	class Tag(object):
		"""An XML tag as it is being used for the
		XmlFactory parser and composer interfaces.
		"""

		__slots__ = (
			"name",
			"attrs",
			"tags",
			"data",
			"comment",
			"flags",
		)

		class NoDefault: pass

		EnumGen.start
		FLAG_ATTR_LINE_BREAK	= EnumGen.bitmask
		FLAG_EMIT_EMPTY_ATTRS	= EnumGen.bitmask
		FLAG_EMIT_EMPTY_TAG	= EnumGen.bitmask
		FLAG_USE_CDATA		= EnumGen.bitmask
		EnumGen.end

		def __init__(self,
			     name,			# Tag name
			     attrs=None,		# Tag attributes
			     tags=None,			# Child tags
			     data=None,			# Tag data
			     comment=None,		# Comment data
			     attrLineBreak=False,	# Use line breaks between attrs?
			     emitEmptyAttrs=False,	# Emit attributes with empty data?
			     emitEmptyTag=False,	# Emit tag, if it is completely empty?
			     useCDATA=False):		# Use CDATA for tag data?
			self.name = name or ""
			self.attrs = attrs or {}
			self.tags = tags or []
			self.data = data or ""
			self.comment = comment or ""
			self.flags = self.FLAG_ATTR_LINE_BREAK if attrLineBreak else 0
			self.flags |= self.FLAG_EMIT_EMPTY_ATTRS if emitEmptyAttrs else 0
			self.flags |= self.FLAG_EMIT_EMPTY_TAG if emitEmptyTag else 0
			self.flags |= self.FLAG_USE_CDATA if useCDATA else 0

		@property
		def attrLineBreak(self):
			return bool(self.flags & self.FLAG_ATTR_LINE_BREAK)

		@property
		def emitEmptyAttrs(self):
			return bool(self.flags & self.FLAG_EMIT_EMPTY_ATTRS)

		@property
		def emitEmptyTag(self):
			return bool(self.flags & self.FLAG_EMIT_EMPTY_TAG)

		@property
		def useCDATA(self):
			return bool(self.flags & self.FLAG_USE_CDATA)

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

		def getAttrFloat(self, name, default=NoDefault):
			try:
				return float(self.attrs[name])
			except KeyError:
				if default is self.NoDefault:
					raise XmlFactory.Error("Tag <%s> attribute "
						"'%s' does not exist." % (
						self.name, name))
			except ValueError:
				if default is self.NoDefault:
					raise XmlFactory.Error("Tag <%s> attribute "
						"'%s' is not an floating point value." % (
						self.name, name))
			return default


	class Comment(Tag):
		"""An XML comment.
		"""

		def __init__(self, text):
			super(XmlFactory.Comment, self).__init__(name=None,
								 comment=text)

	def __init__(self, **kwargs):
		self.builder = None
		self.__genXmlHeader = True
		self.__baseIndent = 0
		self.__lineBreakStr = "\n"
		self.__globalAttrLineBreak = False
		for kwarg, kwval in dictItems(kwargs):
			setattr(self, kwarg, kwval)

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

	def __tags2text(self, tags, indent=0):
		ret = []
		for tagIndex, tag in enumerate(tags):
			ind = "\t" * indent
			# Force convert attrs to str and remove empty attrs
			attrs = { str(aName) : str(aVal)
				  for aName, aVal in dictItems(tag.attrs)
				  if tag.emitEmptyAttrs or str(aVal)
			}
			# Convert attrs to XML
			if self.__globalAttrLineBreak or tag.attrLineBreak:
				attrSpacer = self.__lineBreakStr + ind +\
					     (" " * (1 + len(tag.name) + 1))
			else:
				attrSpacer = " "
			attrText = (" " + attrSpacer.join(
				"%s=%s" % (aName, saxutils.quoteattr(aVal))
				for aName, aVal in sorted(dictItems(attrs),
							  key=lambda a: a[0])
			)).rstrip()
			# Convert the child tags to XML
			if tag.tags:
				childTags = self.__tags2text(tag.tags, indent + 1)
			else:
				childTags = []
			# Add comment, if any.
			def addComment(comment):
				if comment.startswith("\n"):
					prefix = "" if (tagIndex == 0) else self.__lineBreakStr
					comment = comment[1:]
				else:
					prefix = ""
				ret.append("%s%s<!-- %s -->" % (
					   prefix, ind,
					   comment.replace("-->", " ->")))
			# Convert tags to XML
			data = tag.data
			if data or childTags:
				if tag.comment:
					addComment(tag.comment)
				if tag.name:
					if data:
						if tag.useCDATA:
							# Escape CDATA-end
							data = data.replace("]]>", "]]]]><![CDATA[>")
							# Create CDATA section
							data = "<![CDATA[%s]]>" % data
						else:
							data = saxutils.escape(tag.data)
					startStr = "%s<%s%s>%s" % (
						ind, tag.name,
						attrText, data)
					if childTags:
						ret.append(startStr)
						ret.extend(childTags)
						ret.append("%s</%s>" % (
							   ind, tag.name))
					else:
						ret.append("%s</%s>" % (
							   startStr, tag.name))
			elif attrs or tag.emitEmptyTag:
				if tag.comment:
					addComment(tag.comment)
				if tag.name:
					ret.append(
						"%s<%s%s />" % (
						ind,
						tag.name,
						attrText)
					)
		return ret

	def compose(self, genXmlHeader=True, baseIndent=0, lineBreakStr="\n", attrLineBreak=False):
		self.builder = None
		self.__genXmlHeader = genXmlHeader
		self.__baseIndent = baseIndent
		self.__lineBreakStr = lineBreakStr
		self.__globalAttrLineBreak = attrLineBreak

		lines = []
		if self.__genXmlHeader:
			lines.append('<?xml version="%s" encoding="%s" standalone="yes"?>' % (
				     self.XML_VERSION, self.XML_ENCODING))
		lines.extend(self.__tags2text(self.composer_getTags(),
					      self.__baseIndent))

		return (lineBreakStr.join(lines) + lineBreakStr).encode(self.XML_ENCODING)

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
