# -*- coding: utf-8 -*-
#
# Abstract spidev module interface implementation
#
# Copyright 2018 Michael Buesch <m@bues.ch>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


class Abstract_SpiDev(object):

	__slots__ = (
		"mode",
		"bits_per_word",
		"max_speed_hz",
		"_bus",
		"_device",
		"_opened",
	)

	def __init__(self, bus=-1, client=-1):
		self.mode = 0
		self.bits_per_word = 0
		self.max_speed_hz = 0
		self._opened = -1
		if bus >= 0:
			self.open(bus, client)

	@property
	def cshigh(self):
		raise NotImplementedError

	@cshigh.setter
	def cshigh(self, cshigh):
		raise NotImplementedError

	@property
	def threewire(self):
		raise NotImplementedError

	@threewire.setter
	def threewire(self, threewire):
		raise NotImplementedError

	@property
	def lsbfirst(self):
		raise NotImplementedError

	@lsbfirst.setter
	def lsbfirst(self, lsbfirst):
		raise NotImplementedError

	@property
	def loop(self):
		raise NotImplementedError

	@loop.setter
	def loop(self, loop):
		raise NotImplementedError

	@property
	def no_cs(self):
		raise NotImplementedError

	@no_cs.setter
	def no_cs(self, no_cs):
		raise NotImplementedError

	def open(self, bus, device):
		assert(bus >= 0)
		assert(device >= 0)
		self._bus = bus
		self._device = device
		self._opened = 42

	def close(self):
		if self._opened >= 0:
			self._opened = -1

	def fileno(self):
		raise NotImplementedError

	def readbytes(self, length):
		raise NotImplementedError

	def writebytes(self, data):
		raise NotImplementedError

	def xfer(self, data, speed_hz=0, delay_usecs=0, bits_per_word=0):
		raise NotImplementedError

	def xfer2(self, data, speed_hz=0, delay_usecs=0, bits_per_word=0):
		raise NotImplementedError

	def __enter__(self):
		pass

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()
		return False


