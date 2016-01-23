#!/bin/sh
#
# PiLC bootstrap
#
# Copyright 2016 Michael Buesch <m@bues.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

# The repository root is basedir.
basedir="$basedir/.."


die()
{
	echo "=== $*" >&2
	exit 1
}

info()
{
	echo "--- $*"
}

# print the first of its arguments.
first()
{
	echo "$1"
}

# $1=program_name
have_program()
{
	which "$1" >/dev/null 2>&1
}

# $1=program_name, ($2=description)
assert_program()
{
	local bin="$1"
	local desc="$2"
	[ -n "$desc" ] || desc="$bin"
	have_program "$bin" || die "$bin not found. Please install $desc."
}

term_signal()
{
	die "Terminating signal received"
}

cleanup()
{
	info "Cleaning up..."
	for mp in "$mp_shm" "$mp_proc" "$mp_sys" "$mp_bootimgfile" "$mp_rootimgfile"; do
		[ -n "$mp" -a -d "$mp" ] &&\
			umount "$mp" >/dev/null 2>&1
	done
	for mp in "$mp_bootimgfile" "$mp_rootimgfile"; do
		[ -n "$mp" -a -d "$mp" ] &&\
			rmdir "$mp" >/dev/null 2>&1
	done
}

boot_config_file()
{
	cat <<EOF
# For more options and information see
# http://www.raspberrypi.org/documentation/configuration/config-txt.md
# Some settings may impact device functionality. See link above for details

# uncomment if you get no picture on HDMI for a default "safe" mode
#hdmi_safe=1

# uncomment this if your display has a black border of unused pixels visible
# and your display can output without overscan
#disable_overscan=1

# uncomment the following to adjust overscan. Use positive numbers if console
# goes off screen, and negative if there is too much border
#overscan_left=16
#overscan_right=16
#overscan_top=16
#overscan_bottom=16

# uncomment to force a console size. By default it will be display's size minus
# overscan.
#framebuffer_width=1280
#framebuffer_height=720

# uncomment if hdmi display is not detected and composite is being output
#hdmi_force_hotplug=1

# uncomment to force a specific HDMI mode (this will force VGA)
#hdmi_group=1
#hdmi_mode=1

# uncomment to force a HDMI mode rather than DVI. This can make audio work in
# DMT (computer monitor) modes
#hdmi_drive=2

# uncomment to increase signal to HDMI, if you have interference, blanking, or
# no display
#config_hdmi_boost=4

# uncomment for composite PAL
#sdtv_mode=2

#uncomment to overclock the arm. 700 MHz is the default.
#arm_freq=800

# Uncomment some or all of these to enable the optional hardware interfaces
#dtparam=i2c_arm=on
#dtparam=i2s=on
#dtparam=spi=on

# Uncomment this to enable the lirc-rpi module
#dtoverlay=lirc-rpi

# Additional overlays and parameters are documented /boot/overlays/README

# Enable audio (loads snd_bcm2835)
dtparam=audio=on
EOF
}

pilc_bootstrap_first_stage()
{
	echo "Running first stage..."

	[ "$(id -u)" = "0" ] || die "Permission denied. Must be root."

	# Check host tools (first/third stage).
	assert_program debootstrap
	assert_program git
	assert_program chroot
	assert_program rsync
	assert_program parted
	assert_program mkfs.vfat
	assert_program mkfs.ext4
	assert_program 7z
	[ -x "$opt_qemu" ] ||\
		die "The qemu binary '$opt_qemu' is not executable."

	# debootstrap first stage.
	if [ $opt_skip_debootstrap1 -eq 0 ]; then
		info "Running debootstrap first stage..."
		debootstrap --arch="$opt_arch" --foreign --verbose \
			--keyring="$basedir/maintenance/raspbian.public.key.gpg" \
			"$opt_suite" "$opt_target_dir" "$opt_mirror" \
			|| die "debootstrap failed"
		mkdir -p "$opt_target_dir/usr/share/keyrings" ||\
			die "Failed to create keyrings dir."
		cp /usr/share/keyrings/debian-archive-keyring.gpg \
		   "$opt_target_dir/usr/share/keyrings/debian-archive-keyring.gpg" ||\
			die "Failed to copy debian-archive-keyring.gpg."
	fi
	[ -d "$opt_target_dir" ] ||\
		die "Target directory '$opt_target_dir' does not exist."

	# Copy qemu.
	local qemu_bin="$opt_target_dir/$opt_qemu"
	if ! [ -x "$qemu_bin" ]; then
		info "Copying qemu binary from '$opt_qemu' to '$qemu_bin'..."
		mkdir -p "$(dirname "$qemu_bin")" ||\
			die "Failed to make qemu base directory."
		cp "$opt_qemu" "$qemu_bin" ||\
			die "Failed to copy qemu binary."
	fi

	info "Copying PiLC bootstrap script..."
	cp "$basedir/maintenance/pilc-bootstrap.sh" "$opt_target_dir/" ||\
		die "Failed to copy bootstrap script."

	info "Checking out awlsim..."
	local checkout_dir="$opt_target_dir/tmp/awlsim"
	rm -rf "$checkout_dir"
	git clone --no-checkout "$basedir/.git" "$checkout_dir" ||\
		die "Failed to clone"
	(
		cd "$checkout_dir" ||\
			die "Failed to cd"
		git checkout -b __build "$opt_branch" ||\
			die "Failed to check out branch."
		rm -r ".git" ||\
			die "Failed to remove .git directory."
	) || die

	# Second stage will mount a few filesystems.
	# Keep track to umount them in cleanup.
	mp_proc="$opt_target_dir/proc"
	mp_sys="$opt_target_dir/sys"
	mp_shm="$opt_target_dir/dev/shm"
}

pilc_bootstrap_second_stage()
{
	info "Running second stage ($opt_arch)..."

	[ -x /pilc-bootstrap.sh ] ||\
		die "Second stage does not contain the bootstrap script."

	# Set up environment.
	export LC_ALL=C
	export LANGUAGE=C
	export LANG=C

	# debootstrap second stage.
	if [ $opt_skip_debootstrap2 -eq 0 ]; then
		info "Running debootstrap second stage..."
		/debootstrap/debootstrap --verbose --second-stage
	fi

	info "Mounting /proc..."
	mkdir -p /proc ||\
		die "Failed to create /proc mountpoint."
	mount -t proc proc /proc ||\
		die "Mounting /proc failed."

	info "Mounting /sys..."
	mkdir -p /sys ||\
		die "Failed to create /sys mountpoint."
	mount -t sysfs sysfs /sys ||\
		die "Mounting /sys failed."

	info "Mounting /dev/shm..."
	mkdir -p /dev/shm ||\
		die "Failed to create /dev/shm mountpoint."
	mount -t tmpfs tmpfs /dev/shm ||\
		die "Mounting /dev/shm failed."

	info "Writing apt configuration (mirror = $opt_mirror)..."
	echo "deb $opt_mirror $opt_suite main firmware" > /etc/apt/sources.list ||\
		die "Failed to set sources.list"
	echo 'Acquire { Languages "none"; };' > /etc/apt/apt.conf.d/99no-translations ||\
		die "Failed to set apt.conf.d"

	info "Creating /etc/fstab"
	mkdir -p /config ||\
		die "Failed to create /config"
	cat > /etc/fstab <<EOF
proc		/proc			proc		auto,defaults		0 0
debugfs		/sys/kernel/debug	debugfs		auto,defaults		0 0
configfs	/config			configfs	auto,defaults		0 0
tmpfs		/tmp			tmpfs		auto,mode=1777		0 0
/dev/mmcblk0p2	/			ext4		auto,noatime,errors=remount-ro	0 1
/dev/mmcblk0p1	/boot			vfat		auto,noatime		0 0
EOF

	info "Writing misc /etc stuff..."
	echo "PiLC" > /etc/hostname ||\
		die "Failed to set hostname"
	printf 'PiLC GNU/Linux (based on Raspbian) \\n \\l\n\n' > /etc/issue ||\
		die "Failed to create /etc/issue"
	printf 'PiLC GNU/Linux (based on Raspbian)\n' > /etc/issue.net ||\
		die "Failed to create /etc/issue.net"
	sed -i -e 's|PRETTY_NAME=.*|PRETTY_NAME="PiLC"|' \
		/etc/os-release ||\
		die "Failed to set os-release PRETTY_NAME."
	sed -i -e 's|NAME=.*|NAME="PiLC"|' \
		/etc/os-release ||\
		die "Failed to set os-release NAME."
	sed -i -e 's|ID=.*|ID=pilc|' \
		/etc/os-release ||\
		die "Failed to set os-release ID."
	sed -i -e 's|ID_LIKE=.*|ID_LIKE=raspbian|' \
		/etc/os-release ||\
		die "Failed to set os-release ID_LIKE."
	sed -i -e 's|HOME_URL=.*|HOME_URL="http://bues.ch/h/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release HOME_URL."
	sed -i -e 's|SUPPORT_URL=.*|SUPPORT_URL="http://bues.ch/h/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release SUPPORT_URL."
	sed -i -e 's|BUG_REPORT_URL=.*|BUG_REPORT_URL="http://bues.ch/h/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release BUG_REPORT_URL."
	sed -i -e 's|#FSCKFIX=no|FSCKFIX=yes|' \
		/etc/default/rcS ||\
		die "Failed to set FSCKFIX=yes"

	info "Updating packages..."
	echo -e 'debconf debconf/priority select high\n' \
		'debconf debconf/frontend select Noninteractive' |\
		debconf-set-selections ||\
		die "Failed to configure debconf"
	apt-get -y update ||\
		die "apt-get update failed"
	apt-get -y dist-upgrade ||\
		die "apt-get dist-upgrade failed"

	info "Installing packages..."
	apt-get -y install \
		aptitude \
		build-essential \
		console-setup \
		cython \
		cython3 \
		debconf-utils \
		fake-hwclock \
		htop \
		linux-image-rpi-rpfv \
		linux-image-rpi2-rpfv \
		locales \
		openssh-server \
		openssh-blacklist \
		openssh-blacklist-extra \
		pypy \
		python \
		python3 \
		raspberrypi-bootloader-nokernel \
		screen \
		sudo \
		systemd \
		tmux ||\
		die "apt-get install failed"
	apt-get -y clean ||\
		die "apt-get clean failed"
	echo -e 'debconf debconf/priority select high\n' \
		'debconf debconf/frontend select Dialog' |\
		debconf-set-selections ||\
		die "Failed to configure debconf"

	info "Removing ssh keys..."
	if [ -e "$(first /etc/ssh/ssh_host_*_key*)" ]; then
		rm /etc/ssh/ssh_host_*_key* ||\
			die "Failed to remove ssh keys."
	fi
	echo 1 > /etc/ssh/sshd_not_to_be_run ||\
		die "Failed to create /etc/ssh/sshd_not_to_be_run"
	echo 1 > /etc/ssh/ssh_create_keys ||\
		die "Failed to create /etc/ssh/ssh_create_keys"

	info "Creating /etc/rc.local..."
	cat > /etc/rc.local <<EOF
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#

set -e

if [ -e /etc/ssh/ssh_create_keys ]; then
	/bin/rm -f /etc/ssh/ssh_host_*_key*
	LC_ALL=C LANGUAGE=C LANG=C /usr/sbin/dpkg-reconfigure openssh-server
	/bin/rm /etc/ssh/sshd_not_to_be_run
	/bin/rm /etc/ssh/ssh_create_keys
	/etc/init.d/ssh start
fi

exit 0
EOF
	[ $? -eq 0 ] || die "Failed to create /etc/rc.local"

	info "Creating users/groups..."
	userdel -f pi
	groupdel pi
	rm -rf /home/pi
	groupadd -g 1000 pi ||\
		die "Failed to create group pi."
	useradd -u 1000 -d /home/pi -m -g pi\
		-G pi,lp,dialout,cdrom,floppy,audio,dip,src,video,plugdev,netdev\
		-s /bin/bash\
		pi ||\
		die "Failed to create user pi."
	printf 'raspberry\nraspberry\n' | passwd pi ||\
		die "Failed to set 'pi' password."
	echo 'pi ALL=(ALL:ALL) ALL' > "/etc/sudoers.d/00-pi" ||\
		die "Failed to create /etc/sudoers.d/00-pi"

	info "Building awlsim..."
	(
		local awlsim_prefix=/opt/awlsim
		cd /tmp/awlsim ||\
			die "Failed to cd"
		rm -rf "$awlsim_prefix"
		if [ $opt_cython -eq 0 ]; then
			export NOCYTHON=1
		else
			export NOCYTHON=0
			export CYTHONPARALLEL=1
		fi
#		python2 ./setup.py build ||\
#			die "Failed to build awlsim (py2)."
#		python2 ./setup.py install --prefix="$awlsim_prefix" ||\
#			die "Failed to install awlsim (py2)."
		python3 ./setup.py build ||\
			die "Failed to build awlsim (py3)."
		python3 ./setup.py install --prefix="$awlsim_prefix" ||\
			die "Failed to install awlsim (py3)."
		cp examples/EXAMPLE.awlpro /home/pi/ ||\
			die "Failed to copy EXAMPLE.awlpro."
		rm "$awlsim_prefix/bin/"*.bat ||\
			die "Failed to remove all .bat files."
		for i in "$awlsim_prefix"/bin/*; do
			echo "$i" | grep -qEe 'linuxcnc|gui' && continue
			ln -s "$i" "/home/pi/$(basename "$i")" ||\
				die "Failed to create awlsim link '$i'"
		done
	) || die
	rm -r /tmp/awlsim ||\
		die "Failed to remove awlsim checkout."

	info "Extending pi user environment..."
	cat >> /home/pi/.bashrc <<EOF

# PiLC
for __i in /opt/awlsim/lib/python*/site-packages/; do
	export PYTHONPATH="\$PYTHONPATH:\$__i"
done
export PATH="\$PATH:/opt/awlsim/bin"
EOF
	[ $? -eq 0 ] || die "Failed to extend /home/pi/.bashrc"

	info "Umounting /dev/shm..."
	umount /dev/shm || die "Failed to umount /dev/shm"
	info "Umounting /sys..."
	umount /sys || die "Failed to umount /sys"
	info "Umounting /proc..."
	umount /proc || die "Failed to umount /proc"
}

pilc_bootstrap_third_stage()
{
	info "Running third stage..."

	info "Removing PiLC bootstrap script..."
	rm "$opt_target_dir/pilc-bootstrap.sh" ||\
		die "Failed to remove bootstrap script."

	info "Configuring boot..."
	cat > "$opt_target_dir/boot/cmdline.txt" <<EOF
dwc_otg.lpm_enable=0 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet
EOF
	[ $? -eq 0 ] || die "Failed to create /boot/cmdline.txt"
	boot_config_file > "$opt_target_dir/boot/config.txt" ||\
		die "Failed to create /boot/config.txt"
	local img="$(first "$opt_target_dir/boot/"vmlinuz-*-rpi)"
	if [ -e "$img" ]; then
		mv "$img" "$opt_target_dir/boot/kernel.img" ||\
			die "Failed to create kernel.img"
	fi
	local img="$(first "$opt_target_dir/boot/"initrd.img-*-rpi)"
	if [ -e "$img" ]; then
		mv "$img" "$opt_target_dir/boot/initrd.img" ||\
			die "Failed to create initrd.img"
	fi
	local img="$(first "$opt_target_dir/boot/"vmlinuz-*-rpi2)"
	if [ -e "$img" ]; then
		mv "$img" "$opt_target_dir/boot/kernel7.img" ||\
			die "Failed to create kernel7.img"
	fi
	local img="$(first "$opt_target_dir/boot/"initrd.img-*-rpi2)"
	if [ -e "$img" ]; then
		mv "$img" "$opt_target_dir/boot/initrd7.img" ||\
			die "Failed to create initrd7.img"
	fi

	# Prepare image paths.
	local target_dir="$(readlink -m "${opt_target_dir}")"
	[ -n "$target_dir" ] || die "Failed to resolve target dir."
	local imgfile="${target_dir}.img"
	local bootimgfile="${imgfile}.boot"
	mp_bootimgfile="${bootimgfile}.mp"
	local rootimgfile="${imgfile}.root"
	mp_rootimgfile="${rootimgfile}.mp"
	rm -f "$rootimgfile" "$bootimgfile"
	rmdir "$mp_bootimgfile" "$mp_rootimgfile" 2>/dev/null

	info "Creating boot image..."
	mkfs.vfat -F 32 -i 7771B0BB -n boot -C "$bootimgfile" \
		$(expr \( 64 \* 1024 \) - \( 4 \* 1024 \) ) ||\
		die "Failed to create boot partition file system."
	mkdir "$mp_bootimgfile" ||\
		die "Failed to make boot partition mount point."
	mount -o loop "$bootimgfile" "$mp_bootimgfile" ||\
		die "Failed to mount boot partition."
	rsync -aHAX --progress --inplace\
		"$target_dir/boot/" "$mp_bootimgfile/" ||\
		die "Failed to copy boot files."
	umount "$mp_bootimgfile" ||\
		die "Failed to umount boot partition."
	rmdir "$mp_bootimgfile" ||\
		die "Failed to remove boot partition mount point."

	info "Creating root image..."
	mkfs.ext4 "$rootimgfile" $(expr \( 1391 - 64 \) \* 1024 ) ||\
		die "Failed to create root filesystem."
	mkdir "$mp_rootimgfile" ||\
		die "Failed to make root partition mount point."
	mount -o loop "$rootimgfile" "$mp_rootimgfile" ||\
		die "Failed to mount root partition."
	rsync -aHAX --progress --inplace \
		--exclude='boot/*' \
		--exclude='proc/*' \
		--exclude='sys/*' \
		--exclude='dev/shm/*' \
		--exclude="$(basename "$opt_qemu")" \
		"$target_dir/" "$mp_rootimgfile/" ||\
		die "Failed to copy root files."
	umount "$mp_rootimgfile" ||\
		die "Failed to umount root partition."
	rmdir "$mp_rootimgfile" ||\
		die "Failed to remove root partition mount point."

	info "Creating image '$imgfile'..."
	dd if=/dev/zero of="$imgfile" bs=1M count=1391 conv=sparse ||\
		die "Failed to create image file."
	parted "$imgfile" <<EOF
            unit b
            mklabel msdos
            mkpart primary fat32 $(expr 4 \* 1024 \* 1024) $(expr 64 \* 1024 \* 1024 - 1)
            mkpart primary ext4 $(expr 64 \* 1024 \* 1024) 100%
EOF
	[ $? -eq 0 ] || die "Failed to create partitions."

	info "Integrating boot image..."
	dd if="$bootimgfile" of="$imgfile"\
		seek=4 bs=1M conv=notrunc,sparse ||\
		die "Failed to integrate boot partition."
	rm "$bootimgfile" ||\
		die "Failed to delete boot partition image."

	info "Integrating root image..."
	dd if="$rootimgfile" of="$imgfile"\
		seek=64 bs=1M conv=notrunc,sparse ||\
		die "Failed to integrate root partition."
	rm "$rootimgfile" ||\
		die "Failed to delete root partition image."

	info "Compressing image..."
	local imgfile_zip="${imgfile}.7z"
	rm -f "$imgfile_zip"
	7z -mx=9 a "$imgfile_zip" "$imgfile" ||\
		die "Failed to compress partition image."
}

usage()
{
	echo "pilc-bootstrap.sh [OPTIONS] TARGET_DIR"
	echo
	echo "Options:"
	echo " --branch|-b BRANCH      Select the awlsim branch."
	echo "                         Default: $default_branch"
	echo " --no-cython|-C          Do not build Cython modules."
	echo "                         Default: Build cython modules"
	echo " --mirror|-m URL         Select the mirror."
	echo "                         Default: $default_mirror"
	echo " --suite|-s SUITE        Select the suite."
	echo "                         Default: $default_suite"
	echo " --arch|-a ARCH          Select the default arch."
	echo "                         Default: $default_arch"
	echo " --qemu-bin|-q PATH      Select qemu-user-static binary."
	echo "                         Default: $default_qemu"
	echo
	echo " --skip-debootstrap1|-1  Skip debootstrap first stage."
	echo " --skip-debootstrap2|-2  Skip debootstrap second stage."
}

# canonicalize basedir
basedir="$(readlink -e "$basedir")"
[ -n "$basedir" ] || die "Failed to canonicalize base directory."

# Mountpoints. Will be umounted on cleanup.
mp_shm=
mp_proc=
mp_sys=
mp_bootimgfile=
mp_rootimgfile=

trap term_signal TERM INT

if [ -z "$__PILC_BOOTSTRAP_SECOND_STAGE__" ]; then
	# First stage

	trap cleanup EXIT

	default_branch="master"
	default_mirror="http://mirrordirector.raspbian.org/raspbian/"
	default_suite="jessie"
	default_arch="armhf"
	default_qemu="/usr/bin/qemu-arm-static"

	opt_target_dir=
	opt_branch="$default_branch"
	opt_cython=1
	opt_mirror="$default_mirror"
	opt_suite="$default_suite"
	opt_arch="$default_arch"
	opt_qemu="$default_qemu"
	opt_skip_debootstrap1=0
	opt_skip_debootstrap2=0

	while [ $# -ge 1 ]; do
		case "$1" in
		--help|-h)
			usage
			exit 0
			;;
		--branch|-b)
			shift
			opt_branch="$1"
			[ -n "$opt_branch" ] || die "No branch given"
			;;
		--no-cython|-C)
			opt_cython=0
			;;
		--mirror|-m)
			shift
			opt_mirror="$1"
			[ -n "$opt_mirror" ] || die "No mirror given"
			;;
		--suite|-s)
			shift
			opt_suite="$1"
			[ -n "$opt_suite" ] || die "No suite given"
			;;
		--arch|-a)
			shift
			opt_arch="$1"
			[ -n "$opt_arch" ] || die "No arch given"
			;;
		--qemu-bin|-q)
			shift
			opt_qemu="$1"
			[ -x "$opt_qemu" ] || die "No valid qemu binary given"
			;;
		--skip-debootstrap1|-1)
			opt_skip_debootstrap1=1
			;;
		--skip-debootstrap2|-2)
			opt_skip_debootstrap2=1
			;;
		*)
			opt_target_dir="$*"
			break
			;;
		esac
		shift
	done
	[ -n "$opt_target_dir" ] ||\
		die "No TARGET_DIR"
	[ -d "$opt_target_dir" -o ! -e "$opt_target_dir" ] ||\
		die "$opt_target_dir is not a directory"

	# Run first stage.
	pilc_bootstrap_first_stage

	info "Starting second stage."
	# Export options for use by second stage.
	export opt_target_dir
	export opt_branch
	export opt_cython
	export opt_mirror
	export opt_suite
	export opt_arch
	export opt_qemu
	export opt_skip_debootstrap1
	export opt_skip_debootstrap2
	export __PILC_BOOTSTRAP_SECOND_STAGE__=1
	chroot "$opt_target_dir" "/pilc-bootstrap.sh" ||\
		die "Chroot failed."

	# Run third stage.
	pilc_bootstrap_third_stage

	info ""
	info "Successfully bootstrapped PiLC."

	exit 0
else
	# Run second stage
	pilc_bootstrap_second_stage

	exit 0
fi
