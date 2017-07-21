from __future__ import division, absolute_import, print_function, unicode_literals

import awlsim_loader.cython_helper as __cython

__importmod = "awlsim.awloptimizer"

if __cython.shouldUseCython(__importmod):			#@nocy
#if True:							#@cy
	__importcymod = __cython.cythonModuleName(__importmod)
	try:
		exec("from %s import *" % __importcymod)
	except ImportError as e:
		__cython.cythonImportError(__importcymod, str(e))
if not __cython.shouldUseCython(__importmod):			#@nocy
	exec("from %s import *" % __importmod)			#@nocy
