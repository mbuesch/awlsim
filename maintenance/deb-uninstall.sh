#!/bin/sh


die()
{
	echo "$*" >&2
	exit 1
}

apt-get purge $(dpkg --get-selections | grep awlsim | cut -f1) ||\
	die "Failed to purge"

exit 0
