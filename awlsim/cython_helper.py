from __future__ import division, absolute_import, print_function, unicode_literals

__USE_CYTHON_NO		= 0 # Do not use Cython.
__USE_CYTHON_TRY	= 1 # Try to use Cython, if available.
__USE_CYTHON_FORCE	= 2 # Use Cython. Abort if not available.
__useCython = None

def shouldUseCython():
	global __useCython
	import os

	if __useCython is None:
		try:
			__useCython = int(os.getenv("AWLSIMCYTHON",
						    str(__USE_CYTHON_NO)))
			if __useCython not in (__USE_CYTHON_NO,
					       __USE_CYTHON_TRY,
					       __USE_CYTHON_FORCE):
				raise ValueError
		except ValueError:
			__useCython = __USE_CYTHON_NO
	return __useCython

def cythonImportError(modname, message):
	global __useCython
	import sys

	if __useCython == __USE_CYTHON_TRY:
		sys.stderr.write("WARNING: Failed to import awlsim CYTHON module '%s': "
				 "%s\n" % (modname, message))
		sys.stderr.write("--> Falling back to standard Python modules...\n")
		sys.stderr.flush()
		__useCython = False
	elif __useCython == __USE_CYTHON_FORCE:
		sys.stderr.write("ERROR: Failed to import awlsim CYTHON module '%s': "
				 "%s\n" % (modname, message))
		sys.stderr.write("Aborting.\n")
		sys.stderr.flush()
		sys.exit(1)
	else:
		assert(0)
