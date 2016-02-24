__all__ = [ "find_executable", ]

import os

def find_executable(executable, path=None):
	import os.path, stat
	if path is None:
		path = os.environ.get("PATH", "")
	for p in os.path.split(":"):
		fullpath = os.path.join(p, executable)
		if os.access(fullpath, stat.S_IXOTH):
			return fullpath
	return None
