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
python2 ./setup.py build
python3 ./setup.py build
echo
echo "build done."
