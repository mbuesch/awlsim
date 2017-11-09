#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

awlsim_base="$basedir/.."

set -e

if ! [ -x "$awlsim_base/awlsim-test" -a -x "$awlsim_base/setup.py" ]; then
	echo "basedir sanity check failed"
	exit 1
fi

opt_verbose=0
if [ "$1" = "-v" ]; then
	opt_verbose=1
fi

run()
{
	nice -n 10 "$1" ./setup.py build &
	RET=$!
}

cd "$awlsim_base"
echo "Running build..."

if [ $opt_verbose -eq 0 ]; then
	run python2 >/dev/null
else
	run python2
fi
python2_build_pid=$RET

if [ $opt_verbose -eq 0 ]; then
	run python3 >/dev/null
else
	run python3
fi
python3_build_pid=$RET

if ! wait $python2_build_pid; then
	echo "Python 2 build FAILED!"
	exit 1
fi
if ! wait $python3_build_pid; then
	echo "Python 3 build FAILED!"
	exit 1
fi

echo
echo "build done."
exit 0
