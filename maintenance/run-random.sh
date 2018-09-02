#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"


awlsim_base="$basedir/.."


echo "Running awlsim-test with random AWL instructions."
seed=$1
[ -z "$seed" ] && seed=1
while true; do
	echo "Running with seed=$seed ..."
	"$awlsim_base/misc/gen_insnbench.py" --seed $seed |\
		"$awlsim_base/awlsim-test" -D -L1 -4 - ||\
		break
	[ $seed -eq 4294967295 ] && exit 0
	seed="$(expr $seed + 1)"
done
exit 1
