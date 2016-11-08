from __future__ import division, absolute_import, print_function, unicode_literals

__USE_CYTHON_NO		= 0 # Do not use Cython.
__USE_CYTHON_TRY	= 1 # Try to use Cython, if available.
__USE_CYTHON_FORCE	= 2 # Use Cython. Abort if not available.
__USE_CYTHON_VERBOSE	= 3 # Use Cython. Abort if not available. Be verbose.
__useCython = None

def cythonModuleName(modname):
	elems = modname.split(".")
	elems[0] = elems[0] + "_cython"
	return ".".join(elems)

def __checkCython():
	global __useCython
	import os

	if __useCython is None:
		try:
			__useCython = int(os.getenv("AWLSIM_CYTHON",
						    str(__USE_CYTHON_NO)))
			if __useCython not in (__USE_CYTHON_NO,
					       __USE_CYTHON_TRY,
					       __USE_CYTHON_FORCE,
					       __USE_CYTHON_VERBOSE):
				raise ValueError
		except ValueError:
			__useCython = __USE_CYTHON_NO

def shouldUseCython(modname=None):
	__checkCython()
	if __useCython == __USE_CYTHON_VERBOSE and modname:
		print("Awlsim-cython: Importing '%s' instead of '%s'" %\
		      (cythonModuleName(modname), modname))
	return __useCython != __USE_CYTHON_NO

def cythonImportError(modname, message):
	global __useCython
	import sys

	def perr(msg):
		if sys.stderr:
			sys.stderr.write(msg)
			sys.stderr.flush()

	if __useCython == __USE_CYTHON_TRY:
		perr("WARNING: Failed to import awlsim CYTHON module '%s': %s\n"
		     "--> Falling back to standard Python modules...\n" %\
		     (modname, message))
		__useCython = __USE_CYTHON_NO
	elif __useCython in (__USE_CYTHON_FORCE, __USE_CYTHON_VERBOSE):
		perr("ERROR: Failed to import awlsim CYTHON module '%s': %s\n"
		     "Aborting.\n" %\
		     (modname, message))
		sys.exit(1)
