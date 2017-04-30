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
for path in ./build/lib.*-*-3.*; do
	export PYTHONPATH="$path/:$PYTHONPATH"
done
export PYTHONPATH=".:$PYTHONPATH"
export AWLSIM_CYTHON=2
exec python3 "$@"
