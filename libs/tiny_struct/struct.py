from ustruct import *

error = ValueError

class Struct(object):
	def __init__(self, format):
		self.format = format
		self.size = calcsize(format)

	def pack(self, *x):
		return pack(self.format, *x)

	def unpack(self, buffer):
		return unpack(self.format, buffer)

	def unpack_from(self, buffer, offset=0):
		return unpack_from(self.format, buffer, offset)
