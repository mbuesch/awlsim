#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

awlsim_base="$basedir/.."

set -e

if ! [ -x "$awlsim_base/awlsim-test" -a -x "$awlsim_base/setup.py" ]; then
	echo "basedir sanity check failed"
	exit 1
fi


die()
{
	echo "$*" >&2
	exit 1
}

usage()
{
	echo "build.sh [OPTIONS]"
	echo
	echo " -h|--help     Show help"
	echo " -v|--verbose  Verbose build"
	echo " -r|--rebuild  Clean the tree before starting build"
}

opt_verbose=0
opt_rebuild=0
while [ $# -ge 1 ]; do
	case "$1" in
	-h|--help)
		usage
		exit 0
		;;
	-v|--verbose)
		opt_verbose=1
		;;
	-r|--rebuild)
		opt_rebuild=1
		;;
	esac
	shift
done


do_build()
{
	nice -n 10 "$1" ./setup.py build &
	RET=$!
}

build()
{
	local name="$1"
	local interpreter="$2"

	echo "Running $name build..."
	if [ $opt_verbose -eq 0 ]; then
		do_build "$interpreter" >/dev/null
	else
		do_build "$interpreter"
	fi
}

cd "$awlsim_base"
if [ $opt_rebuild -ne 0 ]; then
	echo "Cleaning tree..."
	"$basedir"/cleantree.sh || die "Failed to clean tree."
fi
export AWLSIM_CYTHON_BUILD=1
build Cython3 python3
python3_build_pid=$RET
if ! wait $python3_build_pid; then
	echo "Cython3 build FAILED!"
	exit 1
fi

echo
echo "build done."
exit 0
