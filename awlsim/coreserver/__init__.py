from __future__ import division, absolute_import, print_function, unicode_literals

import awlsim.cython_helper as __cython

if __cython.shouldUseCython():
	try:
		from awlsim_cython.coreserver.all_modules import *
	except ImportError as e:
		__cython.cythonImportError("coreserver", str(e))
if not __cython.shouldUseCython():
	from awlsim.coreserver.all_modules import *
