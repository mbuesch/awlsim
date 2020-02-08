_exitfuncs = []

def _exitfunc():
	for f in _exitfuncs:
		f()

import sys
if hasattr(sys, "atexit"):
	sys.atexit(_exitfunc)

def register(f):
	_exitfuncs.append(f)
