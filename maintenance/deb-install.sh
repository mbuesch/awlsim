#!/bin/sh


die()
{
	echo "$*" >&2
	exit 1
}

install()
{
	for i in "$@"; do
		if printf '%s' "$i" | grep -qe dbgsym; then
			continue
		fi
		if ! [ -f "$i" ]; then
			echo "Warning: $i does not exist. Skipping..."
			continue
		fi
		echo "Installing $i ..."
		dpkg -i "$i" || die "FAILED: dpkg -i $i"
	done
}

basedir="$1"
[ -d "$basedir" ] || die "Usage:  deb-install.sh PACKAGEDIR"

for interp in python3 cython3 pypy; do
	install "$basedir"/$interp-awlsim_*_*.deb
	install "$basedir"/$interp-awlsimhw-*_*_*.deb
	if [ "$interp" = "python3" ]; then
		install "$basedir"/$interp-awlsim-gui_*_*.deb
	fi
done
install "$basedir"/awlsim-*_*_*.deb

exit 0
