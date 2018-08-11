# -*- coding: utf-8 -*-
#
# AWL simulator - object reference manager
#
# Copyright 2015-2018 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.exceptions import *


__all__ = [
	"ObjRef",
	"ObjRefManager",
]


class ObjRef(object):
	"""Object reference.
	This represents a reference from 'obj' to the ObjRefManager 'manager'.
	"""

	__slots__ = (
		"__name",
		"__obj",
		"__manager",
	)

	@classmethod
	def make(cls, name=None,
		 manager=None, ref=None, inheritRef=False,
		 obj=None):
		"""Make a new ObjRef instance.
		name -> A name string (or callable returning a string).
		manager -> An ObjRefManager instance.
		ref -> An ObjRef instance.
		inheritRef -> If False and ref is not None, a new ref is created.
			      If True and ref is not None, the ref is inherited.
		obj -> The object that is associated with this ref.
		"""
		if name is None:
			# Default name
			name = lambda _self: ("ObjRef(manager=(%s), obj=(%s))" %
					      (str(_self.manager), str(_self.obj)))

		if manager is not None and ref is not None:
			raise RuntimeError

		if manager is not None:
			return cls(name, manager, obj)
		elif ref is not None:
			oldRef = ref
			newRef = cls(name, oldRef.__manager, obj)
			if inheritRef and oldRef.alive:
				oldRef.destroy()
			return newRef
		else:
			return None

	def __init__(self, name, manager, obj = None):
		"""Contruct object reference.
		name: Informational name string or callable returing a string.
		manager: An ObjRefManager instance.
		obj: The object that is associated with this ref (optional).
		"""
		self.__name = name
		self.__obj = obj
		self.__manager = manager
		if self.__manager is not None:
			self.__manager._addRef(self)

	def destroy(self):
		"""Destroy (unref) this reference.
		This removes the reference from the manager.
		"""
		if self.alive:
			try:
				self.__manager.refDestroyed(self)
			finally:
				self.__name = None
				self.__obj = None
				self.__manager = None

	@property
	def name(self):
		"""The reference name string.
		"""
		if callable(self.__name):
			return self.__name(self)
		return self.__name

	@property
	def obj(self):
		"""The object that is associated with this ref.
		"""
		return self.__obj

	@property
	def manager(self):
		"""Get the manager that this ref belongs to.
		"""
		return self.__manager

	@property
	def alive(self):
		"""True, if this reference is alive.
		False, if this reference was destroyed.
		"""
		return self.__manager is not None

	def __repr__(self): #@nocov
		return str(self.name)

class ObjRefManager(object):
	"""Object reference manager.
	The manager belongs to the object that actually is referenced.
	"""

	__slots__ = (
		"__name",
		"__oneDestroyedCallback",
		"__allDestroyedCallback",
		"__refs",
	)

	def __init__(self, name,
		     oneDestroyedCallback=None,
		     allDestroyedCallback=None):
		"""Contruct reference manager.
		name: Informational name string or callable returing a string.
		oneDestroyedCallback: Optional callback. Called, if one ref was destroyed.
		allDestroyedCallback: Optional callback. Called, if all refs were destroyed.
		"""
		self.__name = name
		self.__oneDestroyedCallback = oneDestroyedCallback
		self.__allDestroyedCallback = allDestroyedCallback
		self.__refs = set()

	@property
	def name(self):
		"""The manager name string.
		"""
		if callable(self.__name):
			return self.__name(self)
		return self.__name

	@property
	def hasReferences(self):
		"""Returns true, if this manager holds references.
		"""
		return bool(self.__refs)

	@property
	def refs(self):
		"""Get a set of all references (ObjRef()s) to this object.
		"""
		return frozenset(self.__refs)

	def getRefForObj(self, obj):
		"""Get the ObjRef() that is managed by this manager for 'obj'.
		"""
		for ref in self.__refs:
			if ref.obj is obj:
				return ref
		return None

	def _addRef(self, objRef):
		self.__refs.add(objRef)

	def refDestroyed(self, objRef):
		"""Callback: Called if one reference was destroyed.
		Override this method or set oneDestroyedCallback,
		if you want to be notified.
		"""
		self.__refs.remove(objRef)
		if self.__oneDestroyedCallback:
			self.__oneDestroyedCallback(objRef)
		if not self.__refs:
			self.allRefsDestroyed()

	def allRefsDestroyed(self):
		"""Callback: Called if all references were destroyed.
		Override this method or set allDestroyedCallback,
		if you want to be notified.
		"""
		if self.__allDestroyedCallback:
			self.__allDestroyedCallback()

	def __repr__(self): #@nocov
		return str(self.name)
