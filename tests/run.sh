#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

die()
{
	echo "$*"
	exit 1
}

# $1=awl_file
run_test()
{
	local awl="$1"

	echo "Running test '$(basename "$awl")' ..."
	"$basedir/../awlsimcli" --quiet --onecycle --extended-insns "$awl" ||\
		die "Test failed"
}

if [ $# -eq 0 ]; then
	for awl in "$basedir"/*.awl; do
		run_test "$awl"
	done
else
	for opt in "$@"; do
		run_test "$basedir/$(basename "$opt")"
	done
fi
