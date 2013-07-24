#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

die()
{
	echo "$*"
	exit 1
}

cleanup()
{
	[ -f "$test_time_file" ] && {
		rm -f "$test_time_file"
		test_time_file=
	}
}

# $1=interpreter $2=awl_file
run_test()
{
	local interpreter="$1"
	local awl="$2"

	echo -n "Running test '$(basename "$awl")' ..."
	command time -o "$test_time_file" -f '%E' \
	"$interpreter" "$basedir/../awlsimcli" --quiet --onecycle --extended-insns \
		--hardware dummy:param0=value0:param1=value1 "$awl" ||\
		die "Test failed"
	echo " [$(cat "$test_time_file")]"
}

# $1=interpreter, $2=directory
run_test_directory()
{
	local interpreter="$1"
	local directory="$2"

	echo "--- Entering directory '$directory'"
	for entry in "$directory"/*; do
		[ -d "$entry" ] && {
			run_test_directory "$interpreter" "$entry"
			continue
		}
		[ "$(echo -n "$entry" | tail -c4)" = ".awl" ] || continue
		run_test "$interpreter" "$entry"
	done
	echo "--- Leaving directory '$directory'"
}

# $@=testfiles
do_tests()
{
	for interpreter in "$opt_interpreter" python3 python2.7 pypy; do
		[ -z "$interpreter" ] && continue
		which "$interpreter" >/dev/null 2>&1 || {
			echo "=== WARNING: '$interpreter' interpreter not found. Test skipped."
			echo
			continue
		}

		echo "=== Running tests with '$interpreter' interpreter."
		if [ $# -eq 0 ]; then
			run_test_directory "$interpreter" "$basedir"
		else
			for opt in "$@"; do
				if [ -d "$opt" ]; then
					run_test_directory "$interpreter" "$opt"
				else
					run_test "$interpreter" "$opt"
				fi
			done
		fi
		echo

		[ -n "$opt_interpreter" ] && break
	done
}

trap cleanup EXIT INT TERM
test_time_file="$(mktemp --tmpdir=/tmp awlsim-test-time.XXXXXX)"

opt_interpreter=

while [ $# -ge 1 ]; do
	[ "$(echo "$1" | cut -c1)" != "-" ] && break

	case "$1" in
	-i|--interpreter)
		shift
		opt_interpreter="$1"
		which "$opt_interpreter" >/dev/null 2>&1 ||\
			die "Interpreter '${opt_interpreter}' not found"
		;;
	*)
		echo "Unknown option: $1"
		exit 1
		;;
	esac
	shift
done

do_tests "$@"

exit 0
