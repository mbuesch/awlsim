#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

awlsim_base="$basedir/.."

set -e

if ! [ -x "$awlsim_base/awlsim-test" -a -x "$awlsim_base/setup.py" ]; then
	echo "basedir sanity check failed"
	exit 1
fi

export CFLAGS="$CFLAGS -O0"
exec "$awlsim_base/maintenance/build.sh" "$@"
