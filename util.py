# -*- coding: utf-8 -*-
#
# AWL simulator - utility functions
# Copyright 2012 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#


class AwlSimError(Exception):
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
