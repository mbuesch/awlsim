#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

set -e

if ! [ -x "$basedir/awlsim-test" -a -x "$basedir/setup.py" ]; then
	echo "basedir sanity check failed"
	exit 1
fi

cd "$basedir"

find . \( \
	\( -name '__pycache__' \) -o \
	\( -name '*.pyo' \) -o \
	\( -name '*.pyc' \) -o \
	\( -name '*$py.class' \) \
       \) -delete

rm -rf build dist release-archives .pybuild
rm -f MANIFEST

rm -f debian/files \
      debian/*.debhelper \
      debian/*.log \
      debian/*.substvars \
      debian/debhelper-build-stamp
rm -rf debian/destdir-* \
       debian/python-awlsim \
       debian/python3-awlsim \
       debian/pypy-awlsim \
       debian/awlsim-client \
       debian/awlsim-server
