QUOTE_MINIMAL = None

class Dialect(object):
	pass

def register_dialect(name, d):
	pass

class reader(object):
	def __init__(self, csvfile, dialect="excel", **fmtparams):
		self.i = 0
		self.lines = []
		for line in csvfile:
			elems = []
			elem = []
			inQuote = False
			skip = 0
			for i, c in enumerate(line):
				if skip > 0:
					skip -= 1
					continue
				if inQuote:
					if c == '"' and not line.startswith('""', i):
						inQuote = False
					elif c == '"' and line.startswith('""', i):
						elem.append(c)
						skip = 1
					else:
						elem.append(c)
				else:
					if c == '"':
						inQuote = True
					elif c == ';':
						elems.append("".join(elem))
						elem = []
					else:
						elem.append(c)
			if line:
				elems.append("".join(elem))
			self.lines.append(elems)

	def __iter__(self):
		self.i = 0
		return self

	def __next__(self):
		try:
			line = self.lines[self.i]
			self.i += 1
			return line
		except IndexError:
			raise StopIteration
