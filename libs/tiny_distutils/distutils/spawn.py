__all__ = [ "find_executable", ]

import os

def find_executable(executable, path=None):
	if executable:
		import os.path
		if path is None:
			path = os.getenv("PATH", "")
		for p in path.split(":"):
			fullpath = os.path.join(p, executable)
			#FIXME this is also true for directories
			if os.access(fullpath, os.X_OK):
				return fullpath
	return None
