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
export MICROPYPATH="$MICROPYPATH:$awlsim_base/libs/tiny_atexit"
export MICROPYPATH="$MICROPYPATH:$awlsim_base/libs/tiny_configparser"
export MICROPYPATH="$MICROPYPATH:$awlsim_base/libs/tiny_csv"
export MICROPYPATH="$MICROPYPATH:$awlsim_base/libs/tiny_datetime"
export MICROPYPATH="$MICROPYPATH:$awlsim_base/libs/tiny_platform"
export MICROPYPATH="$MICROPYPATH:$awlsim_base/libs/tiny_struct"
export MICROPYPATH="$MICROPYPATH:$awlsim_base/libs/tiny_xml"
export MICROPYPATH="$MICROPYPATH:$HOME/.micropython/lib"
exec micropython -X heapsize=512M "$@"
