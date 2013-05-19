#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

die()
{
	echo "$*"
	exit 1
}

# $1=interpreter $2=awl_file
run_test()
{
	local interpreter="$1"
	local awl="$2"

	echo "Running test '$(basename "$awl")' ..."
	"$interpreter" "$basedir/../awlsimcli" --quiet --onecycle --extended-insns "$awl" ||\
		die "Test failed"
}

for interpreter in python3 python2.7 pypy; do
	which "$interpreter" >/dev/null 2>&1 || {
		echo "=== WARNING: '$interpreter' interpreter not found. Test skipped."
		echo
		continue
	}

	echo "=== Running tests with '$interpreter' interpreter."
	if [ $# -eq 0 ]; then
		for awl in "$basedir"/*.awl; do
			run_test "$interpreter" "$awl"
		done
	else
		for opt in "$@"; do
			run_test "$interpreter" "$basedir/$(basename "$opt")"
		done
	fi
	echo
done
