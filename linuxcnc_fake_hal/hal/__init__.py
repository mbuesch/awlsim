HAL_BIT		= 1
HAL_U32		= 2
HAL_S32		= 3
HAL_FLOAT	= 4
HAL_IN		= 5
HAL_OUT		= 6
HAL_RO		= 7
HAL_RW		= 8

class component(object):
	def __init__(self, name):
		pass

	def newpin(self, p, t, d):
		pass

	def newparam(self, p, t, d):
		pass

	def ready(self):
		pass

	def __getitem__(self, k):
		return 0

	def __setitem__(self, k, v):
		pass
