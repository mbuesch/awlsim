from __future__ import division, absolute_import, print_function, unicode_literals

__useCython = None

def shouldUseCython():
	global __useCython
	import os

	if __useCython is None:
		try:
			__useCython = bool(int(os.getenv("AWLSIMCYTHON", "0")))
		except ValueError:
			__useCython = False
	return __useCython

def cythonImportError(modname, message):
	global __useCython
	import sys

	sys.stderr.write("WARNING: Failed to import awlsim CYTHON module '%s': "
			 "%s\n" % (modname, message))
	sys.stderr.write("--> Falling back to standard Python modules...\n")
	sys.stderr.flush()
	__useCython = False
