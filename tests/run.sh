#!/bin/sh

# basedir is the root of the test directory in the package
basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

# rootdir is the root of the package
rootdir="$basedir/.."

die()
{
	echo "$*"
	exit 1
}

# $1=message
test_failed()
{
	echo "=== TEST FAILED ==="

	(
		flock -x 9 || die "Failed to take lock"
		echo "$*" >> "$test_fail_file"
	) 9< "$test_fail_file"

	if [ $opt_softfail -eq 0 ]; then
		die "$@"
	else
		echo "$*"
		echo "^^^ TEST FAILED ^^^"
		[ $global_retval -eq 0 ] && global_retval=1
	fi
}

cleanup()
{
	wait

	rm -f "/tmp/$test_time_file_template"* >/dev/null 2>&1
	[ -n "$test_fail_file" ] &&\
		rm -f "$test_fail_file" >/dev/null 2>&1
	[ -n "$port_alloc_file" ] &&\
		rm -f "$port_alloc_file"* >/dev/null 2>&1
}

cleanup_and_exit()
{
	cleanup
	exit 1
}

# Allocate a new port number.
get_port()
{
	(
		flock -x 8 || die "Failed to take port lock"

		local port="$(cat "$port_alloc_file")"
		local next="$(expr "$port" + 1)"
		echo "$next" > "$port_alloc_file" ||\
			die "Failed to update port allocation file"

		echo -n "$port"
	) 8> "${port_alloc_file}.lock"
}

# Returns true (0), if there are more than 1 jobs.
is_parallel_run()
{
	[ $opt_jobs -gt 1 ]
}

# Get the number of currently running background test jobs.
nr_of_running_jobs()
{
	jobs -p | wc -l
}

# Returns true (0), if at least one background job failed.
check_job_failure()
{
	is_parallel_run &&\
	[ -e "$test_fail_file" ] &&\
	[ "0" != "$(du -s "$test_fail_file" | cut -f1)" ]
}

# $1=interpreter
# Returns version on stdout as:  MAJOR MINOR PATCHLEVEL
get_interpreter_version()
{
	local interpreter="$1"

	[ "$interpreter" = "cython" -o "$interpreter" = "cython2" ] && local interpreter=python2
	[ "$interpreter" = "cython3" ] && local interpreter=python3

	"$interpreter" -c 'import sys; print("%d %d %d" % sys.version_info[0:3]);' 2>/dev/null
}

# $1=program_name
have_prog()
{
	local program="$1"

	which "$program" >/dev/null 2>&1
}

# $1=interpreter
setup_test_environment()
{
	local interpreter="$1"

	if [ "$interpreter" = "cython" -o "$interpreter" = "cython2" ]; then
		for i in "$rootdir"/build/lib.linux-*-2.*; do
			export PYTHONPATH="$i"
			break
		done
		export AWLSIMCYTHON=2
		local interpreter=python2
	elif [ "$interpreter" = "cython3" ]; then
		for i in "$rootdir"/build/lib.linux-*-3.*; do
			export PYTHONPATH="$i"
			break
		done
		export AWLSIMCYTHON=2
		local interpreter=python3
	else
		export PYTHONPATH=
		export AWLSIMCYTHON=
	fi
	RET="$interpreter"
}

cleanup_test_environment()
{
	export PYTHONPATH=
	export AWLSIMCYTHON=
}

# $1=interpreter $2=awl_file ($3ff additional options to awlsim-test)
run_awl_test()
{
	local interpreter="$1"
	local awl="$2"
	shift; shift

	setup_test_environment "$interpreter"
	local interpreter="$RET"

	local test_time_file="$(mktemp --tmpdir=/tmp ${test_time_file_template}.XXXXXX)"

	local ok=1
	command time -o "$test_time_file" -f '%E' \
	"$interpreter" "$rootdir/awlsim-test" --loglevel 2  --extended-insns \
		--hardware debug:inputAddressBase=7:outputAddressBase=8:dummyParam=True \
		--cycle-time 60 \
		"$@" \
		"$awl" || {
			test_failed "Test '$(basename "$awl")' FAILED"
			local ok=0
	}
	if is_parallel_run; then
		[ $ok -ne 0 ] && echo "[$(basename "$awl"): OK $(cat "$test_time_file")]"
	else
		[ $ok -ne 0 ] && echo "[OK: $(cat "$test_time_file")]"
	fi
	rm "$test_time_file"
	cleanup_test_environment
}

# $1=interpreter $2=sh_file
run_sh_test()
{
	local interpreter="$1"
	local sh_file="$2"
	shift; shift

	[ -x "$sh_file" ] && die "SH-file '$sh_file' must NOT be executable"

	[ "$(echo "$sh_file" | cut -c1)" = '/' ] || local sh_file="$(pwd)/$sh_file"

	# Source the test file
	. "$basedir/sh-test.defaults"
	. "$sh_file"

	# Run the test
	(
	 setup_test_environment "$interpreter"
	 local interpreter="$RET"
	 local test_dir="$(dirname "$sh_file")"
	 local test_name="$(basename "$sh_file" .sh)"
	 sh_test "$interpreter" "$test_dir" "$test_name"
	 cleanup_test_environment
	)
	local result=$?

	[ $result -eq 0 ] || die "Test failed with error code $result"
	if is_parallel_run; then
		echo "[$(basename "$sh_file"): OK]"
	else
		echo "[OK]"
	fi
}

# $1=interpreter $2=testfile(.awl/.sh) ($3ff additional options to awlsim-test or testfile)
__run_test()
{
	local interpreter="$1"
	local testfile="$2"
	shift; shift

	# Don't run ourself
	[ "$(basename "$testfile")" = "run.sh" ] && return

	if is_parallel_run; then
		local nl=
	else
		local nl="-n"
	fi
	echo $nl "Running test '$(basename "$testfile")' with '$(basename "$interpreter")' ... "

	# Check the file type and run the tester
	if [ "$(echo -n "$testfile" | tail -c4)" = ".awl" -o\
	     "$(echo -n "$testfile" | tail -c7)" = ".awlpro" ]; then
		run_awl_test "$interpreter" "$testfile" "$@"
	elif [ "$(echo -n "$testfile" | tail -c3)" = ".sh" ]; then
		run_sh_test "$interpreter" "$testfile" "$@"
	else
		die "Test file type of '$testfile' not recognized"
	fi
}

run_test()
{
	if is_parallel_run; then
		# Run tests in parallel.
		while [ $(nr_of_running_jobs) -ge $opt_jobs ]; do
			# Too many jobs. Waiting...
			sleep 0.1
		done
		__run_test "$@" &
	else
		# Run tests one-by-one.
		__run_test "$@"
	fi
}

# $1=interpreter, $2=directory
run_test_directory()
{
	local interpreter="$1"
	local directory="$2"

	echo "--- Entering directory '$directory'"
	# run .awlpro tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c7)" = ".awlpro" ] || continue

		local extra=
		[ "$(basename "$entry")" = "EXAMPLE.awlpro" -o\
		  "$(basename $(dirname "$entry"))" = "999-projects" ] &&\
			local extra="--max-runtime 1.0"

		run_test "$interpreter" "$entry" $extra
		check_job_failure && return
	done
	# run .awl tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c4)" = ".awl" ] || continue
		[ -e "${entry}pro" ] && continue

		local extra=
		[ "$(basename $(dirname "$entry"))" = "999-projects" ] &&\
			local extra="--max-runtime 1.0"

		run_test "$interpreter" "$entry" $extra
		check_job_failure && return
	done
	# run .sh tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c3)" = ".sh" ] || continue
		run_test "$interpreter" "$entry"
		check_job_failure && return
	done
	# Recurse into subdirectories
	for entry in "$directory"/*; do
		[ -d "$entry" ] || continue
		run_test_directory "$interpreter" "$entry"
	done
	echo "--- Leaving directory '$directory'"
}

# $1=interpreter
warn_skipped()
{
	local interpreter="$1"

	echo "=== WARNING: '$interpreter' interpreter not found. Test skipped."
	echo
}

# $@=testfiles
do_tests()
{
	if [ $opt_quick -eq 0 ]; then
		local all_interp="python2 python3 pypy pypy3 jython ipy cython2 cython3"
	else
		local all_interp="python2 python3"
	fi

	for interpreter in "$opt_interpreter" $all_interp; do
		[ -z "$interpreter" ] && continue

		if [ "$interpreter" = "cython" -o "$interpreter" = "cython2" ]; then
			[ "$interpreter" = "cython2" ] && ! have_prog "cython2" &&\
				interpreter="cython" # Fallback
			have_prog "$interpreter" && have_prog python2 || {
				warn_skipped "$interpreter"
				[ -n "$opt_interpreter" ] && break || continue
			}
			cd "$rootdir" || die "cd to $rootdir failed"
			echo "=== Building awlsim with python2"
			CYTHONPARALLEL=1 \
			python2 ./setup.py build || die "'python2 ./setup.py build' failed"
		elif [ "$interpreter" = "cython3" ]; then
			have_prog "$interpreter" && have_prog python3 || {
				warn_skipped "$interpreter"
				[ -n "$opt_interpreter" ] && break || continue
			}
			cd "$rootdir" || die "cd to $rootdir failed"
			echo "=== Building awlsim with python3"
			CYTHONPARALLEL=1 \
			python3 ./setup.py build || die "'python3 ./setup.py build' failed"
		else
			have_prog "$interpreter" || {
				warn_skipped "$interpreter"
				[ -n "$opt_interpreter" ] && break || continue
			}
		fi

		local interp_ver="$(get_interpreter_version "$interpreter")"
		local interp_ver_dot="$(echo "$interp_ver" | tr ' ' '.')"
		local interp_major="$(echo "$interp_ver" | cut -d' ' -f 1)"
		local interp_minor="$(echo "$interp_ver" | cut -d' ' -f 2)"

		[ -z "$interp_ver" ] && {
			echo "=== WARNING: Failed to get '$interpreter' version. Test skipped."
			echo
			[ -n "$opt_interpreter" ] && break || continue
		}
		[ "$interp_major" -eq 2 -a "$interp_minor" -lt 7 ] && {
			echo "=== WARNING: '$interpreter' interpreter version '$interp_ver_dot' too old. Test skipped."
			echo
			[ -n "$opt_interpreter" ] && break || continue
		}

		echo "=== Running tests with '$interpreter'"
		if [ $# -eq 0 ]; then
			run_test_directory "$interpreter" "$basedir"
		else
			for opt in "$@"; do
				if [ -d "$opt" ]; then
					run_test_directory "$interpreter" "$opt"
				else
					run_test "$interpreter" "$opt"
				fi
				check_job_failure && break
			done
		fi
		echo

		check_job_failure && break
		[ -n "$opt_interpreter" ] && break
	done

	if is_parallel_run; then
		# This is a parallel run. Wait for all jobs.
		echo "Waiting for background jobs..."
		wait
		# Print the fail information.
		if check_job_failure; then
			echo
			echo "===== FAILURES in parallel run: ====="
			cat "$test_fail_file"
			echo "====================================="
			global_retval=1
		fi
	fi

	# Print summary
	if [ $global_retval -eq 0 ]; then
		echo -n "All tests succeeded"
	else
		echo -n "Some tests FAILED"
	fi
	if [ -n "$opt_interpreter" ]; then
		echo " (with interpreter '$opt_interpreter')"
	else
		if [ $opt_quick -eq 0 ]; then
			echo " (full run)"
		else
			echo " (quick run)"
		fi
	fi
}

show_help()
{
	echo "awlsim unit test script"
	echo
	echo "Usage: run.sh [OPTIONS] [testscript.awl/.sh]"
	echo
	echo "Options:"
	echo " -i|--interpreter INTER        Use INTER as interpreter for the tests"
	echo " -s|--softfail                 Do not abort on single test failures"
	echo " -j|--jobs NR                  Set the number of jobs to run in parallel."
	echo "                               0 means number-of-CPUs"
	echo "                               Default: 1"
	echo " -q|--quick                    Only run python2 and python3 tests"
}

trap cleanup_and_exit INT TERM
trap cleanup EXIT
test_time_file_template="awlsim-test-time.$$"
test_fail_file="$(mktemp --tmpdir=/tmp awlsim-test-fail.XXXXXX)"
port_alloc_file="$(mktemp --tmpdir=/tmp awlsim-test-port.XXXXXX)"
touch "${port_alloc_file}.lock"
echo 4096 > "$port_alloc_file" || die "Failed to initialize port file"

opt_interpreter=
opt_softfail=0
opt_quick=0
opt_renice=
opt_jobs=1

while [ $# -ge 1 ]; do
	[ "$(printf '%s' "$1" | cut -c1)" != "-" ] && break

	case "$1" in
	-h|--help)
		show_help
		exit 0
		;;
	-i|--interpreter)
		shift
		opt_interpreter="$1"
		have_prog "$opt_interpreter" ||\
			die "Interpreter '${opt_interpreter}' not found"
		;;
	-s|--softfail)
		opt_softfail=1
		;;
	-j|--jobs)
		shift
		opt_jobs="$1"
		[ -z "$opt_jobs" -o -n "$(printf '%s' "$opt_jobs" | tr -d '[0-9]')" ] &&\
			die "--jobs: '$opt_jobs' is not a positive integer number."
		[ $opt_jobs -eq 0 ] && opt_jobs="$(getconf _NPROCESSORS_ONLN)"
		[ -z "$opt_jobs" ] &&\
			die "Could not detect number of CPUs."
		;;
	-q|--quick)
		opt_quick=1
		;;
	-n|--renice)
		shift
		opt_renice="$1"
		;;
	*)
		echo "Unknown option: $1"
		exit 1
		;;
	esac
	shift
done

do_renice()
{
	renice "$1" "$$"
}

if [ -n "$opt_renice" ]; then
	do_renice "$opt_renice" || die "Failed to renice"
else
	# Try to renice. Ignore failure.
	do_renice 10
fi

global_retval=0
do_tests "$@"

exit $global_retval
