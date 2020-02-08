def escape(data, entities={}):
	assert not entities
	return data.replace("&", "&amp;").replace(">", "&gt;").replace("<", "&lt;")

def unescape(data, entities={}):
	assert not entities
	return data.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def quoteattr(data, entities={}):
	assert not entities
	data = escape(data).replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;")
	if '"' in data:
		if "'" in data:
			return '"' + data.replace('"', "&quot;") + '"'
		else:
			return "'" + data + "'"
	else:
		return '"' + data + '"'
