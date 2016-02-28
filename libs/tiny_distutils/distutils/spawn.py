__all__ = [ "find_executable", ]

import os

def find_executable(executable, path=None):
	if executable:
		import os.path
		if path is None:
			path = os.getenv("PATH", "")
		for p in path.split(":"):
			fullpath = os.path.join(p, executable)
			if os.access(fullpath, os.X_OK) and\
			   not os.path.isdir(fullpath):
				return fullpath
	return None
