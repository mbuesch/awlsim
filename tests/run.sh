#!/bin/sh

# basedir is the root of the test directory in the package
basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

# rootdir is the root of the package
rootdir="$basedir/.."


failfile_write()
{
	(
		flock -x 9 || die "Failed to take lock"
		echo "$*" >> "$test_fail_file"
	) 9< "$test_fail_file"
}

die()
{
	echo "$*"

	# We might be in a sub-job. So write to fail-file.
	failfile_write "$*"

	exit 1
}

# $1=message
test_failed()
{
	echo "=== TEST FAILED ==="

	if [ $opt_softfail -eq 0 ]; then
		die "$@"
	else
		failfile_write "$*"
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
	[ -n "$jobs_tmp_file" ] &&\
		rm -f "$jobs_tmp_file"* >/dev/null 2>&1
}

cleanup_and_exit()
{
	cleanup
	exit 1
}

# Get a configuration option.
# $1=configured_file
# $2=option_name
# ($3=default_value)
get_conf()
{
	local configured_file="$1"
	local option_name="$2"
	local default_value="$3"

	local conf="${configured_file}.conf"
	local val="$default_value"
	if [ -r "$conf" ]; then
		local regex="^${option_name}="
		if grep -qEe "$regex" "$conf"; then
			local val="$(grep -Ee "$regex" "$conf" | cut -d'=' -f2)"
		fi
	fi
	printf '%s' "$val"
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

# Wait until there is at least one free job slot.
wait_for_free_job_slot()
{
	while true; do
		jobs -l > "$jobs_tmp_file" # can't use pipe on dash
		[ "$(cat "$jobs_tmp_file" | wc -l)" -lt $opt_jobs ] && break
		# Too many jobs. Waiting...
		sleep 0.1
	done
}

# $1 is the PID of the job to wait for.
wait_for_job_pid()
{
	local jobpid="$1"

	while true; do
		jobs -l > "$jobs_tmp_file" # can't use pipe on dash
		cat "$jobs_tmp_file" | tr -d '+-' |\
			sed -e 's/[[:blank:]]\+/\t/g' | cut -f2 |\
			grep -qe '^'"$jobpid"'$' || break
		# Job is still running...
		sleep 0.1
	done
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

# Check DOS file encoding.
# $1=file
check_dos_text_encoding()
{
	local file="$1"

	if [ x"$(du -b "$file" | cut -f1)" != x"0" ]; then
		# Check CR/LF
		file -L "$file" | grep -qe 'CRLF line terminators' || {
			die "ERROR: '$file' is not in DOS format."
		}
		# Check file encoding
		file -L "$file" | grep -qEe '(ISO-8859 text)|(ASCII text)' || {
			die "ERROR: '$file' invalid file encoding."
		}
	fi
}

# $1=interpreter [$2=tested_file]
setup_test_environment()
{
	local interpreter="$1"
	local tested_file="$2"

	if [ "$interpreter" = "cython" -o "$interpreter" = "cython2" ]; then
		for i in "$rootdir"/build/lib.linux-*-2.*; do
			export PYTHONPATH="$i"
			break
		done
		export AWLSIM_CYTHON=2
		local interpreter=python2
	elif [ "$interpreter" = "cython3" ]; then
		for i in "$rootdir"/build/lib.linux-*-3.*; do
			export PYTHONPATH="$i"
			break
		done
		export AWLSIM_CYTHON=2
		local interpreter=python3
	else
		export PYTHONPATH=
		export AWLSIM_CYTHON=
	fi

	local conf_pythonpath=
	if [ -n "$tested_file" ]; then
		local conf_pythonpath="$(get_conf "$awl" PYTHONPATH)"
		[ -n "$conf_pythonpath" ] &&\
			local conf_pythonpath="$(readlink -m "$rootdir/$conf_pythonpath")"
	fi

	export PYTHONPATH="$PYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export JYTHONPATH="$JYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export IRONPYTHONPATH="$IRONPYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export MICROPYPATH="$MICROPYPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"

	export PYTHONOPTIMIZE=

	RET="$interpreter"
}

cleanup_test_environment()
{
	export AWLSIM_CYTHON=

	export PYTHONPATH=
	export JYTHONPATH=
	export IRONPYTHONPATH=
	export MICROPYPATH=

	export EXTRA_PYTHONPATH=
}

# $1=interpreter $2=awl_file ($3ff additional options to awlsim-test)
run_awl_test()
{
	local interpreter="$1"
	local awl="$2"
	shift; shift

	setup_test_environment "$interpreter" "$awl"
	local interpreter="$RET"

	local test_time_file="$(mktemp --tmpdir=/tmp ${test_time_file_template}.XXXXXX)"

	local tries="$(get_conf "$awl" tries 1)"
	[ $tries -lt 1 ] && local tries=1

	local ok=0
	local exit_code=-1
	local expected_exit_code=-2
	while [ $tries -gt 0 -a $ok -eq 0 ]; do
		local ok=1
		local tries="$(expr "$tries" - 1)"
		local loglevel="$(get_conf "$awl" loglevel 2)"
		local expected_exit_code="$(get_conf "$awl" exit_code 0)"
		[ $expected_exit_code -eq 0 ] || local loglevel=0
		local cycle_limit="$(get_conf "$awl" cycle_limit 60)"

		command time -o "$test_time_file" -f '%E' --quiet \
		"$interpreter" "$rootdir/awlsim-test" \
			--loglevel $loglevel \
			--extended-insns \
			--hardware debug:inputAddressBase=7:outputAddressBase=8:dummyParam=True \
			--cycle-limit "$cycle_limit" \
			"$@" \
			"$awl"
		local exit_code=$?
		[ $exit_code -eq $expected_exit_code ] || {
			local ok=0
			[ $tries -gt 0 ] &&\
				echo "Test '$(basename "$awl")' FAILED, but retrying ($tries)..."
		}
	done
	if [ $ok -eq 0 ]; then
		test_failed "\nTest '$(basename "$awl")'   FAILED" \
			"\nActual exit code   = $exit_code" \
			"\nExpected exit code = $expected_exit_code"
	fi
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
	 setup_test_environment "$interpreter" "$sh_file"
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

	local prev_dir="$(pwd)"
	cd "$rootdir" || die "cd to $rootdir failed"

	# Check the file type and run the tester
	if [ "$(echo -n "$testfile" | tail -c4)" = ".awl" -o\
	     "$(echo -n "$testfile" | tail -c7)" = ".awlpro" ]; then
		check_dos_text_encoding "$testfile"
		run_awl_test "$interpreter" "$testfile" "$@"
	elif [ "$(echo -n "$testfile" | tail -c3)" = ".sh" ]; then
		run_sh_test "$interpreter" "$testfile" "$@"
	else
		die "Test file type of '$testfile' not recognized"
	fi

	cd "$prev_dir" || die "cd to $prev_dir failed"
}

run_test()
{
	if is_parallel_run; then
		# Run tests in parallel.
		wait_for_free_job_slot
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
		[ -e "$(dirname "$entry")/$(basename "$entry" .awlpro).sh" ] && continue

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
		[ -e "$(dirname "$entry")/$(basename "$entry" .awl).awlpro" ] && continue
		[ -e "$(dirname "$entry")/$(basename "$entry" .awl).sh" ] && continue

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

build_cython2()
{
	have_prog cython && have_prog python2 || {
		echo "=== WARNING: Cannot build cython2 modules"
		return 1
	}
	cd "$rootdir" || die "cd to $rootdir failed"
	echo "=== Building awlsim with python2"
	CFLAGS= CPPFLAGS= CXXFLAGS= LDFLAGS= \
	AWLSIM_CYTHON_PARALLEL=1 \
	nice -n 5 \
	python2 ./setup.py build || die "'python2 ./setup.py build' failed"
	return 0
}

build_cython3()
{
	have_prog cython3 && have_prog python3 || {
		echo "=== WARNING: Cannot build cython3 modules"
		return 1
	}
	cd "$rootdir" || die "cd to $rootdir failed"
	echo "=== Building awlsim with python3"
	CFLAGS= CPPFLAGS= CXXFLAGS= LDFLAGS= \
	AWLSIM_CYTHON_PARALLEL=1 \
	nice -n 5 \
	python3 ./setup.py build || die "'python3 ./setup.py build' failed"
	return 0
}

# $@=testfiles
do_tests()
{
	export EXTRA_PYTHONPATH=

	if [ $opt_quick -eq 0 ]; then
		local all_interp="python2 python3 pypy pypy3 jython ipy cython2 cython3"
	else
		local all_interp="python2 python3"
	fi

	local cython2_build_pid=
	local cython3_build_pid=
	if is_parallel_run; then
		# Trigger the build jobs, if required.
		local inter="$opt_interpreter $all_interp"
		if printf '%s' "$inter" | grep -Eqwe 'cython|cython2'; then
			wait_for_free_job_slot
			build_cython2 &
			local cython2_build_pid=$!
		fi
		if printf '%s' "$inter" | grep -qwe 'cython3'; then
			wait_for_free_job_slot
			build_cython3 &
			local cython3_build_pid=$!
		fi
	fi

	for interpreter in "$opt_interpreter" $all_interp; do
		[ -z "$interpreter" ] && continue

		if [ "$interpreter" = "cython" -o "$interpreter" = "cython2" ]; then
			have_prog cython && have_prog python2 || {
				warn_skipped "$interpreter"
				[ -n "$opt_interpreter" ] && break || continue
			}
			if is_parallel_run; then
				wait_for_job_pid $cython2_build_pid
			else
				build_cython2 || die "Cython2 build failed."
			fi
		elif [ "$interpreter" = "cython3" ]; then
			have_prog cython3 && have_prog python3 || {
				warn_skipped "$interpreter"
				[ -n "$opt_interpreter" ] && break || continue
			}
			if is_parallel_run; then
				wait_for_job_pid $cython3_build_pid
			else
				build_cython3 || die "Cython3 build failed."
			fi
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
				local opt="$(readlink -m "$opt")"
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
	echo
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
jobs_tmp_file="$(mktemp --tmpdir=/tmp awlsim-test-jobs.XXXXXX)"
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
		if [ $opt_jobs -eq 0 ]; then
			opt_jobs="$(getconf _NPROCESSORS_ONLN)"
			opt_jobs="$(expr $opt_jobs + 2)"
		fi
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
