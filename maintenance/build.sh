#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

awlsim_base="$basedir/.."

set -e

if ! [ -x "$awlsim_base/awlsim-test" -a -x "$awlsim_base/setup.py" ]; then
	echo "basedir sanity check failed"
	exit 1
fi

cd "$awlsim_base"
python2 ./setup.py build &
python2_build_pid=$!
python3 ./setup.py build &
python3_build_pid=$!
if ! wait $python2_build_pid; then
	echo "Python 2 build FAILED!"
	exit 1
fi
if ! wait $python3_build_pid; then
	echo "Python 3 build FAILED!"
	exit 1
fi
echo
echo "build done."
exit 0
