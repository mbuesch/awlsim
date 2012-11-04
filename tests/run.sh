#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

die()
{
	echo "$*"
	exit 1
}

for awl in $basedir/*.awl; do
	echo "Running test '$(basename "$awl")' ..."
	python3 "$basedir/../awlsim.py" --quiet --onecycle "$awl" ||\
		die "Test failed"
done
