#!/bin/sh


die()
{
	echo "$*" >&2
	exit 1
}

install()
{
	for i in "$@"; do
		printf '%s' "$i" | grep -qe dbgsym && continue
		echo "Installing $1 ..."
		dpkg -i "$i" || die "FAILED: dpkg -i $i"
	done
}

basedir="$1"
[ -d "$basedir" ] || die "Usage:  deb-install.sh PACKAGEDIR"

for interp in python python3 cython cython3 pypy; do
	install "$basedir"/$interp-awlsim_*_*.deb
	install "$basedir"/$interp-awlsimhw-*_*_*.deb
	if [ "$interp" != cython ] &&\
	   [ "$interp" != cython3 ] &&\
	   [ "$interp" != pypy ]; then
		install "$basedir"/$interp-awlsim-gui_*_*.deb
	fi
done
install "$basedir"/awlsim-*_*_*.deb

exit 0
