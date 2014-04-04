import awlsim.cython_helper as __cython

if __cython.shouldUseCython():
	try:
		from awlsim_cython.coreserver.all import *
	except ImportError as e:
		__cython.cythonImportError("coreserver", str(e))
if not __cython.shouldUseCython():
	from awlsim.coreserver.all import *
