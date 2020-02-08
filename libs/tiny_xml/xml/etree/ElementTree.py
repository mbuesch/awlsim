from xml.sax.saxutils import unescape

__all__ = [ "ParseError", "XMLParser", ]

def unescapeattr(d):
	return unescape(d.replace("&#9;", "\t").replace("&#13;", "\r").replace("&#10;", "\n"))

class ParseError(Exception):
	pass

class XMLParser(object):
	class __Tag(object):
		def __init__(self,
			     skip=0,
			     state="tagname"):
			self.name = ""
			self.data = []
			self.attrs = {}
			self.attrName = []
			self.attrData = []
			self.attrQuote = '"'
			self.end = False

			self.skip = skip
			self.state = state

	def __init__(self, html=0, target=None, encoding=None):
		assert target, "'target' must be provided. Standard TreeBuilder currently not implemented."
		self.target = target

	def feed(self, text):
		tag = None
		tree = []
		if not isinstance(text, str):
			text = text.decode("UTF-8")
		for i, c in enumerate(text):
			if tag and tag.skip > 0:
				tag.skip -= 1
				continue

			if tag and tag.end:
				if tag.state not in ("comment", "head", "cdata"):
					self.target.data(unescape("".join(tag.data)))
					self.target.end(tag.name)
				tree.pop()
				prevTag = tree[-1] if tree else None
				if tag.state == "cdata" and prevTag:
					prevTag.data.extend(tag.data)
				tag = prevTag
				# Fall through

			if tag and tag.state == "comment":
				if text.startswith("-->", i):
					tag.skip = 2
					tag.end = True
				continue
			if tag and tag.state == "head":
				if text.startswith("?>", i):
					tag.skip = 1
					tag.end = True
				continue
			if tag and tag.state == "cdata":
				if text.startswith("]]>", i):
					tag.skip = 2
					tag.end = True
				else:
					tag.data.append(c)
				continue
			if tag and tag.state == "attrname":
				if c == "=":
					if text.startswith('="', i):
						tag.attrQuote = '"'
					elif text.startswith("='", i):
						tag.attrQuote = "'"
					else:
						raise ParseError("Invalid attribute quoting.")
					tag.skip = 1 # skip quote
					tag.state = "attrdata"
					tag.attrData = []
				else:
					tag.attrName.append(c)
				continue
			if tag and tag.state == "attrdata":
				if c == tag.attrQuote:
					tag.state = "taghead"
					tag.attrs["".join(tag.attrName)] = unescapeattr("".join(tag.attrData))
					tag.attrName = []
					tag.attrData = []
				else:
					tag.attrData.append(c)
				continue
			if tag and tag.state == "taghead":
				if c == ">":
					self.target.start(tag.name, tag.attrs)
					tag.state = "data"
				elif text.startswith("/>", i):
					self.target.start(tag.name, tag.attrs)
					tag.skip = 1
					tag.end = True
				elif not c.isspace():
					tag.attrName = [c]
					tag.state = "attrname"
				continue
			if tag and tag.state == "tagname":
				if c.isspace() or c == ">":
					if c == ">":
						tag.state = "data"
						self.target.start(tag.name, tag.attrs)
					else:
						tag.state = "taghead"
				else:
					tag.name += c
				continue

			if text.startswith("<!--", i):
				tag = self.__Tag(state="comment", skip=3)
				tree.append(tag)
				continue
			if text.startswith("<?", i):
				tag = self.__Tag(state="head", skip=1)
				tree.append(tag)
				continue
			if text.startswith("<![CDATA[", i):
				tag = self.__Tag(state="cdata", skip=8)
				tree.append(tag)
				continue
			if c == "<" and not text.startswith("</", i):
				tag = self.__Tag()
				tree.append(tag)
				continue

			if tag and tag.state == "data":
				if text.startswith("</" + tag.name + ">", i):
					tag.skip = len("</" + tag.name + ">") - 1
					tag.end = True
				elif text.startswith("</", i):
					raise ParseError("Invalid end tag")
				else:
					tag.data.append(c)
				continue

			if c.strip():
				raise ParseError("Trailing characters.")

	def close(self):
		pass
