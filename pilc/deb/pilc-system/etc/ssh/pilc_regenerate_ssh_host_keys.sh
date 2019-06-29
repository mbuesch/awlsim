#!/bin/sh

export PATH=/bin:/usr/bin:/sbin:/usr/sbin
export LC_ALL=C LANGUAGE=C LANG=C

if [ "$1" = "SECOND_STAGE" ]; then
	echo "Seeding /dev/urandom..."
	dd if=/dev/hwrng of=/dev/urandom count=16 bs=1024

	echo "Regenerating SSH keys..."
	rm -f /etc/ssh/ssh_host_*_key*
	if ssh-keygen -A -v; then
		echo "Starting SSH daemon..."
		rm -f /etc/ssh/sshd_not_to_be_run
		systemctl enable ssh
		systemctl start ssh
		echo "Disabling regeneration trigger..."
		systemctl disable pilc_regenerate_ssh_host_keys
		echo "Done."
	else
		echo "FAILED to regenerate SSH keys."
	fi
else
	nohup sh /etc/ssh/pilc_regenerate_ssh_host_keys.sh SECOND_STAGE >/var/log/pilc_regenerate_ssh_host_keys.log 2>&1 &
fi
exit 0
