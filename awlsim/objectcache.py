# -*- coding: utf-8 -*-
#
# Generic object cache
# Copyright 2012-2013 Michael Buesch <m@bues.ch>
#
# Licensed under the terms of the GNU General Public License version 2.
#


class ObjectCache(object):
	def __init__(self, createCallback):
		self.__createCallback = createCallback
		self.reset()

	def get(self, callbackData=None):
		try:
			return self.__cache.pop()
		except IndexError:
			return self.__createCallback(callbackData)

	def put(self, obj):
		self.__cache.append(obj)

	def reset(self):
		self.__cache = []
