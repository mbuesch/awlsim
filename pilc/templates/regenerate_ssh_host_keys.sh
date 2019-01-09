#!/bin/sh

export PATH=/bin:/usr/bin:/sbin:/usr/sbin
export LC_ALL=C LANGUAGE=C LANG=C

if [ "$1" = "SECOND_STAGE" ]; then
	dd if=/dev/hwrng of=/dev/urandom count=1 bs=4096
	rm -f /etc/ssh/ssh_host_*_key*
	if dpkg-reconfigure openssh-server; then
		rm -f /etc/ssh/sshd_not_to_be_run
		systemctl enable ssh
		systemctl disable regenerate_ssh_host_keys
		systemctl start ssh
	fi
else
	nohup sh /etc/ssh/regenerate_ssh_host_keys.sh SECOND_STAGE >/var/log/regenerate_ssh_host_keys.log 2>&1 &
fi
exit 0
