# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#

import os
import random
import struct


class AwlSimError(Exception):
	pass

class AwlParserError(Exception):
	pass

def awlFileRead(filename):
	try:
		fd = open(filename, "r", encoding="latin_1")
		data = fd.read()
		fd.close()
	except IOError as e:
		raise AwlParserError("Failed to read '%s': %s" %\
			(filename, str(e)))
	return data

def awlFileWrite(filename, data):
	data = "\r\n".join(data.splitlines()) + "\r\n"
	for count in range(1000):
		tmpFile = "%s-%d-%d.tmp" %\
			(filename, random.randint(0, 0xFFFF), count)
		if not os.path.exists(tmpFile):
			break
	else:
		raise AwlParserError("Could not create temporary file")
	try:
		fd = open(tmpFile, "w", encoding="latin_1")
		fd.write(data)
		fd.flush()
		fd.close()
		if os.name.lower() != "posix":
			# Can't use safe rename on non-POSIX.
			# Must unlink first.
			os.unlink(filename)
		os.rename(tmpFile, filename)
	except (IOError, OSError) as e:
		raise AwlParserError("Failed to write file:\n" + str(e))
	finally:
		try:
			os.unlink(tmpFile)
		except (IOError, OSError):
			pass

def byteToSignedPyInt(byte):
	if byte & 0x80:
		return -((~byte + 1) & 0xFF)
	return byte & 0xFF

def wordToSignedPyInt(word):
	if word & 0x8000:
		return -((~word + 1) & 0xFFFF)
	return word & 0xFFFF

def dwordToSignedPyInt(dword):
	if dword & 0x80000000:
		return -((~dword + 1) & 0xFFFFFFFF)
	return dword & 0xFFFFFFFF

def pyFloatToDWord(pyfl):
	buf = struct.pack('>f', pyfl)
	return (buf[0] << 24) |\
	       (buf[1] << 16) |\
	       (buf[2] << 8) |\
	       buf[3]

def dwordToPyFloat(dword):
	buf = bytes( ((dword >> 24) & 0xFF,
		      (dword >> 16) & 0xFF,
		      (dword >> 8) & 0xFF,
		      dword & 0xFF) )
	return struct.unpack('>f', buf)[0]
