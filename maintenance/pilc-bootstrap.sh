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
	for mp in "$mp_shm" "$mp_proc" "$mp_bootimgfile" "$mp_rootimgfile"; do
		[ -n "$mp" -a -d "$mp" ] &&\
			umount "$mp" >/dev/null 2>&1
	done
	for mp in "$mp_bootimgfile" "$mp_rootimgfile"; do
		[ -n "$mp" -a -d "$mp" ] &&\
			rmdir "$mp" >/dev/null 2>&1
	done
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

	info "Mounting virtual filesystems..."
	mp_shm="$opt_target_dir/dev/shm"
	mkdir -p "$mp_shm" ||\
		die "Failed to create /dev/shm mountpoint."
	mount -t tmpfs tmpfs "$mp_shm" ||\
		die "Mounting /dev/shm failed."
	mp_proc="$opt_target_dir/proc"
	mkdir -p "$mp_proc" ||\
		die "Failed to create /proc mountpoint."
	mount -o bind /proc "$mp_proc" ||\
		die "Mounting /proc failed."
}

pilc_bootstrap_second_stage()
{
	info "Running second stage ($opt_arch)..."

	[ -x /pilc-bootstrap.sh ] ||\
		die "Second stage does not contain the bootstrap script."

	# debootstrap second stage.
	if [ $opt_skip_debootstrap2 -eq 0 ]; then
		info "Running debootstrap second stage..."
		/debootstrap/debootstrap --verbose --second-stage
	fi

	info "Writing apt configuration (mirror = $opt_mirror)..."
	echo "deb $opt_mirror $opt_suite main firmware" > /etc/apt/sources.list
	echo 'Acquire { Languages "none"; };' > /etc/apt/apt.conf.d/99no-translations

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
		linux-image-rpi-rpfv \
		locales \
		python \
		python3 \
		raspberrypi-bootloader-nokernel \
		systemd ||\
		die "apt-get install failed"
	apt-get -y clean ||\
		die "apt-get clean failed"
	echo -e 'debconf debconf/priority select high\n' \
		'debconf debconf/frontend select Dialog' |\
		debconf-set-selections ||\
		die "Failed to configure debconf"

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

	info "Building awlsim..."
	(
		cd /tmp/awlsim ||\
			die "Failed to cd"
		rm -rf /opt/awlsim
		if [ $opt_cython -eq 0 ]; then
			export NOCYTHON=1
		else
			export NOCYTHON=0
			export CYTHONPARALLEL=1
		fi
#		python2 ./setup.py build ||\
#			die "Failed to build awlsim (py2)."
#		python2 ./setup.py install --prefix=/opt/awlsim ||\
#			die "Failed to install awlsim (py2)."
		python3 ./setup.py build ||\
			die "Failed to build awlsim (py3)."
		python3 ./setup.py install --prefix=/opt/awlsim ||\
			die "Failed to install awlsim (py3)."
		cp examples/EXAMPLE.awlpro /home/pi/ ||\
			die "Failed to copy EXAMPLE.awlpro."
	) || die

	info "Extending pi user environment..."
	cat << EOF >> /home/pi/.bashrc

# PiLC
for __i in /opt/awlsim/lib/python*/site-packages/; do
	export PYTHONPATH="\$PYTHONPATH:\$__i"
done
export PATH="\$PATH:/opt/awlsim/bin"
EOF
}

pilc_bootstrap_third_stage()
{
	info "Running third stage..."

	info "Removing PiLC bootstrap script..."
	rm "$opt_target_dir/pilc-bootstrap.sh" ||\
		die "Failed to remove bootstrap script."

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
	mkfs.vfat -F 32 -i 7771B0BB -n boot -C "$bootimgfile" 61440 ||\
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
	mkfs.ext4 "$rootimgfile" 1327M ||\
		die "Failed to create root filesystem."
	mkdir "$mp_rootimgfile" ||\
		die "Failed to make root partition mount point."
	mount -o loop "$rootimgfile" "$mp_rootimgfile" ||\
		die "Failed to mount root partition."
	rsync -aHAX --progress --inplace \
		--exclude='boot/*' \
		--exclude='proc/*' \
		--exclude='dev/shm/*' \
		--exclude="$(basename "$opt_qemu")" \
		"$target_dir/" "$mp_rootimgfile/" ||\
		die "Failed to copy root files."
	umount "$mp_rootimgfile" ||\
		die "Failed to umount root partition."
	rmdir "$mp_rootimgfile" ||\
		die "Failed to remove root partition mount point."

	info "Creating image '$imgfile'..."
	dd if=/dev/zero of="$imgfile" bs=512 count=2848768 conv=sparse ||\
		die "Failed to create image file."
	parted -s "$imgfile" "mklabel msdos" ||\
		die "Failed to create partition table."
	parted -s "$imgfile" "mkpart primary fat32 8192s 131071s" ||\
		die "Failed to create boot partition."
	parted -s "$imgfile" "mkpart primary ext4 131072s 2848767s" ||\
		die "Failed to create root partition."

	info "Integrating boot image..."
	dd if="$bootimgfile" of="$imgfile"\
		seek=8192 bs=512 conv=notrunc,sparse ||\
		die "Failed to integrate boot partition."
	rm "$bootimgfile" ||\
		die "Failed to delete boot partition image."

	info "Integrating root image..."
	dd if="$rootimgfile" of="$imgfile"\
		seek=131072 bs=512 conv=notrunc,sparse ||\
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
