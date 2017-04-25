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
find . -name '*.awlpro' \
	-a -type f \
	-a \! -path '*/tests/*-legacy/*' \
	-a \! -path '*/submodules/*' \
	-a \! -path '*/.*/*' \
	-exec ./awlsim-proupgrade --loglevel 3 '{}' \;
