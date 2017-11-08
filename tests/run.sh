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

# $1=executable_name
find_executable()
{
	local executable_name="$1"

	local executable_path="$(which "$executable_name")"
	[ -n "$executable_path" ] ||\
		die "$executable_name executable not found."\
		    "Please install $executable_name."
	RET="$executable_path"
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

	# Check if we want to run on Cython2/3 and set the environment
	# for Cython2/3.
	if [ "$interpreter" = "cython" -o "$interpreter" = "cython2" ] ||\
	   [ "$interpreter" = "python" -a "$AWLSIM_CYTHON" != "" ] ||\
	   [ "$interpreter" = "python2" -a "$AWLSIM_CYTHON" != "" ]; then
		# We want to run the test using Cython2

		for i in "$rootdir"/build/lib.linux-*-2.*; do
			export PYTHONPATH="$i"
			break
		done
		# Enforce cython module usage
		export AWLSIM_CYTHON=2
		# The actual interpreter is Python
		local interpreter=python2

	elif [ "$interpreter" = "cython3" ] ||\
	     [ "$interpreter" = "python3" -a "$AWLSIM_CYTHON" != "" ]; then
		# We want to run the test using Cython3

		for i in "$rootdir"/build/lib.linux-*-3.*; do
			export PYTHONPATH="$i"
			break
		done
		# Enforce cython module usage
		export AWLSIM_CYTHON=2
		# The actual interpreter is Python
		local interpreter=python3

	else
		# Neither Cython2 nor Cython3
		export PYTHONPATH=
		export AWLSIM_CYTHON=
	fi

	# Get extra PYTHONPATH from test case config file.
	local conf_pythonpath=
	if [ -n "$tested_file" ]; then
		local conf_pythonpath="$(get_conf "$awl" PYTHONPATH)"
		[ -n "$conf_pythonpath" ] &&\
			local conf_pythonpath="$(readlink -m "$rootdir/$conf_pythonpath")"
	fi

	# Export PYTHONPATHs
	export PYTHONPATH="$PYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export JYTHONPATH="$JYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export IRONPYTHONPATH="$IRONPYTHONPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"
	export MICROPYPATH="$MICROPYPATH:$EXTRA_PYTHONPATH:$conf_pythonpath"

	# Disable Python optimization so that assert statements are enabled.
	# Enable hash seed randomization.
	unset PYTHONSTARTUP
	unset PYTHONY2K
	unset PYTHONOPTIMIZE
	unset PYTHONDEBUG
	unset PYTHONDONTWRITEBYTECODE
	unset PYTHONINSPECT
	unset PYTHONIOENCODING
	unset PYTHONNOUSERSITE
	unset PYTHONUNBUFFERED
	unset PYTHONVERBOSE
	unset PYTHONWARNINGS
	export PYTHONHASHSEED=random

	# Disable CPU affinity
	unset AWLSIM_AFFINITY

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
	local actual_interpreter="$RET"

	# By default run once with all optimizers enabled.
	local optimizer_runs="$(get_conf "$awl" optimizer_runs all)"

	for optimizers in $optimizer_runs; do
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
			local max_runtime="$(get_conf "$awl" max_runtime -1)"

			command time -o "$test_time_file" -f '%E' --quiet \
			"$actual_interpreter" "$rootdir/awlsim-test" \
				--loglevel $loglevel \
				--extended-insns \
				--hardware debug:inputAddressBase=7:outputAddressBase=8:dummyParam=True \
				--cycle-limit "$cycle_limit" \
				--max-runtime "$max_runtime" \
				--optimizers "$optimizers" \
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
				"\nInterpreter        = $interpreter" \
				"\nOptimizers         = $optimizers" \
				"\nActual exit code   = $exit_code" \
				"\nExpected exit code = $expected_exit_code"
		fi
		if is_parallel_run; then
			[ $ok -ne 0 ] && echo "[$(basename "$awl"): O=$optimizers t=$(cat "$test_time_file") -> OK]  "
		else
			[ $ok -ne 0 ] && echo -n "[O=$optimizers t=$(cat "$test_time_file") -> OK]  "
		fi
		rm "$test_time_file"
	done
	is_parallel_run || echo

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

# $1=interpreter $2=test_file
run_nose_test()
{
	local interpreter="$1"
	local test_case="$2"
	shift; shift

	[ -z "$test_case" ] &&\
		die "Nose test case is missing"
	[ -d "$test_case" ] &&\
		die "Nose test case '$test_case' must not be a directory"
	[ -x "$test_case" ] &&\
		die "Nose test case '$test_case' must NOT be executable"

	# Select nosetests or nosetests3
	local interp_ver="$(get_interpreter_version "$interpreter")"
	local interp_major="$(echo "$interp_ver" | cut -d' ' -f 1)"
	if [ "$interp_major" = "2" ]; then
		local nose="$nosetests"
	else
		local nose="$nosetests3"
	fi

	# Resolve relative path
	[ "$(echo "$test_case" | cut -c1)" = '/' ] ||\
		local test_case="$(pwd)/$test_case"

	# Add nose libraries to pypy environment
	if [ "$(basename "$interpreter")" = "pypy" ]; then
		local p='import sys; print(":".join(p for p in sys.path if p.startswith("/usr/")))'
		EXTRA_PYTHONPATH="$("$interpreter" -c "$p"):$(python2 -c "$p"):$EXTRA_PYTHONPATH"
	fi
	# Add awlsim_tstlib.py to PYTHONPATH
	EXTRA_PYTHONPATH="$rootdir/tests:$EXTRA_PYTHONPATH"

	# Setup python environment
	setup_test_environment "$interpreter" "$test_case"
	local interpreter="$RET"

	# Run the nose test case
	cd "$rootdir" || die "Failed to cd to rootdir."
	"$interpreter" "$nose" --no-byte-compile "$test_case" ||\
		die "Nose test case '$(basename "$test_case")' failed."

	if is_parallel_run; then
		echo "[$(basename "$test_case"): OK]"
	else
		echo "[nose OK]"
	fi
	cleanup_test_environment
}

# $1=interpreter $2=testfile(.awl/.sh) ($3ff additional options to awlsim-test or testfile)
__run_test()
{
	local interpreter="$1"
	local testfile="$2"
	shift; shift

	# Don't run ourself
	[ "$(basename "$testfile")" = "run.sh" ] && return
	# Don't run the test helper library
	[ "$(basename "$testfile")" = "awlsim_tstlib.py" ] && return

	if is_parallel_run; then
		local nl=
	else
		local nl="-n"
	fi
	echo $nl "Running test '$(basename "$testfile")' with '$(basename "$interpreter")' ... "

	local prev_dir="$(pwd)"
	cd "$rootdir" || die "cd to $rootdir failed"

	# Check the file type and run the tester
	if [ "$(echo -n "$testfile" | tail -c4)" = ".awl" ]; then
		check_dos_text_encoding "$testfile"
		run_awl_test "$interpreter" "$testfile" "$@"
	elif [ "$(echo -n "$testfile" | tail -c7)" = ".awlpro" ]; then
		run_awl_test "$interpreter" "$testfile" "$@"
	elif [ "$(echo -n "$testfile" | tail -c3)" = ".sh" ]; then
		run_sh_test "$interpreter" "$testfile" "$@"
	elif [ "$(echo -n "$testfile" | tail -c3)" = ".py" ]; then
		run_nose_test "$interpreter" "$testfile" "$@"
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

		run_test "$interpreter" "$entry"
		check_job_failure && return
	done
	# run .awl tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c4)" = ".awl" ] || continue
		[ -e "$(dirname "$entry")/$(basename "$entry" .awl).awlpro" ] && continue
		[ -e "$(dirname "$entry")/$(basename "$entry" .awl).sh" ] && continue

		run_test "$interpreter" "$entry"
		check_job_failure && return
	done
	# run .sh tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c3)" = ".sh" ] || continue
		run_test "$interpreter" "$entry"
		check_job_failure && return
	done
	# run nose tests
	for entry in "$directory"/*; do
		[ -d "$entry" ] && continue
		[ "$(echo -n "$entry" | tail -c3)" = ".py" ] || continue
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
	cleanup_test_environment

	if [ $opt_quick -eq 0 ]; then
		local all_interp="python2 python3 pypy pypy3 cython2 cython3"
		if [ $opt_extended -ne 0 ]; then
			local all_interp="$all_interp jython"
		fi
	else
		local all_interp="python2 python3"
		if [ $opt_extended -ne 0 ]; then
			die "The options --quick and --extended are mutually exclusive."
		fi
	fi

	find_executable nosetests
	local nosetests="$RET"
	find_executable nosetests3
	local nosetests3="$RET"

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

		cleanup_test_environment

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

		[ -z "$interp_ver" ] &&\
			die "Failed to get '$interpreter' version."
		[ "$interp_major" -eq 2 -a "$interp_minor" -lt 7 ] &&\
			die "'$interpreter' interpreter version '$interp_ver_dot' too old."

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
			if [ $opt_extended -eq 0 ]; then
				echo " (full run)"
			else
				echo " (extended run)"
			fi
		else
			echo " (quick run)"
		fi
	fi
}

show_help()
{
	echo "awlsim unit test script"
	echo
	echo "Usage: run.sh [OPTIONS] [testdirectory/testscript.awl/.awlpro/.sh/.py]"
	echo
	echo "Options:"
	echo " -i|--interpreter INTER        Use INTER as interpreter for the tests"
	echo " -s|--softfail                 Do not abort on single test failures"
	echo " -j|--jobs NR                  Set the number of jobs to run in parallel."
	echo "                               0 means number-of-CPUs"
	echo "                               Default: 1"
	echo " -q|--quick                    Only run python2 and python3 tests"
	echo " -qq                           Shortcut for: -q -j 0"
	echo " -x|--extended                 Run tests on additional interpreters"
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
opt_extended=0
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
		;;
	-q|--quick)
		opt_quick=1
		;;
	-qq)
		opt_quick=1
		opt_jobs=0
		;;
	-x|--extended)
		opt_extended=1
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

[ -z "$opt_jobs" -o -n "$(printf '%s' "$opt_jobs" | tr -d '[0-9]')" ] &&\
	die "--jobs: '$opt_jobs' is not a positive integer number."
if [ $opt_jobs -eq 0 ]; then
	opt_jobs="$(getconf _NPROCESSORS_ONLN)"
	opt_jobs="$(expr $opt_jobs + 2)"
fi
[ -z "$opt_jobs" ] &&\
	die "Could not detect number of CPUs."


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
