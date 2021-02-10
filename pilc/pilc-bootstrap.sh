#!/bin/sh
#
# PiLC bootstrap
#
# Copyright 2016-2020 Michael Buesch <m@bues.ch>
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


DEFAULT_SUITE=buster
MAIN_MIRROR_32="http://mirrordirector.raspbian.org/raspbian/"
MAIN_MIRROR_ARCHIVE="http://archive.raspberrypi.org/debian/"
MAIN_MIRROR_64="http://deb.debian.org/debian/"
MAIN_MIRROR_64_SECURITY="http://deb.debian.org/debian-security/"

KEYRING_VERSION="20120528.2"
KEYRING_BASEURL="$MAIN_MIRROR_32/pool/main/r/raspbian-archive-keyring"
KEYRING_TGZ_FILE="raspbian-archive-keyring_${KEYRING_VERSION}.tar.gz"
KEYRING_TGZ_SHA256="fdf50f775b60901a2783f21a6362e2bf5ee6203983e884940b163faa1293c002"

PPL_VERSION="0.1.1"
PPL_FILE="ppl_v$PPL_VERSION.zip"
PPL_MIRROR="./libs/pixtend/v1/ppl/$PPL_FILE"
PPL_SHA256="103edcdbc377f8b478fcbc89117cbad143500c611cb714568f55513cece220d4"

PPL2_VERSION="0.1.3"
PPL2_FILE="pplv2_v$PPL2_VERSION.zip"
PPL2_MIRROR="./libs/pixtend/v2/pplv2/$PPL2_FILE"
PPL2_SHA256="cab6e7cd9062ffbf81a8f570ea0cad663addd8fe22e31cb75e887ae89e425651"


info()
{
	echo "--- $*"
}

error()
{
	echo "=== ERROR: $*" >&2
}

warning()
{
	echo "=== WARNING: $*" >&2
}

die()
{
	error "$*"
	exit 1
}

# print the first of its arguments.
first()
{
	echo "$1"
}

# print the last of its arguments.
last()
{
	while [ $# -gt 1 ]; do shift; done
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
	for mp in "$mp_shm" "$mp_proc_binfmt_misc" "$mp_proc" "$mp_sys" "$mp_bootimgfile" "$mp_rootimgfile"; do
		[ -n "$mp" -a -d "$mp" ] &&\
			umount -l "$mp" >/dev/null 2>&1
	done
	for mp in "$mp_bootimgfile" "$mp_rootimgfile"; do
		[ -n "$mp" -a -d "$mp" ] &&\
			rmdir "$mp" >/dev/null 2>&1
	done
}

do_install()
{
	install "$@" || die "Failed install $*"
}

do_systemctl()
{
	info "systemctl $*"
	systemctl "$@" || die "Failed to systemctl $*"
}

write_image()
{
	local image="$1"
	local dev="$2"

	[ -b "$dev" ] || die "$dev is not a block device"
	mount | grep -q "$dev" && die "$dev is mounted. Refusing to write to it!"

	if have_program blkdiscard; then
		info "Discarding $dev ..."
		blkdiscard -f "$dev" ||\
			error "blkdiscard failed."
	else
		warning "Skipping discard. blkdiscard not installed."
	fi

	info "Writing $image to $dev ..."

	dd if="$image" of="$dev" bs=32M status=progress ||\
		die "Failed to write image."
}

download()
{
	local target="$1"
	local mirror="$2"
	local sha256="$3"

	info "Downloading $mirror..."
	rm -f "$target"
	if printf '%s' "$mirror" | grep -qe '^\./'; then
		# "mirror" starts with ./
		# This is a local file in the repository.
		cp "$basedir/$mirror" "$target" || die "Failed to fetch $mirror"
	else
		# Download the file
		wget -O "$target" "$mirror" || die "Failed to fetch $mirror"
	fi
	[ "$(sha256sum -b "$target" | cut -f1 -d' ')" = "$sha256" ] ||\
		die "SHA256 verification of $target failed"
}

extract_archive()
{
	local archive="$1"
	local extract_dir="$2"
	local make_extract_dir="$3"

	if [ $make_extract_dir -ne 0 ]; then
		mkdir "$extract_dir" ||\
			die "Failed to create directory $extract_dir"
	fi
	if printf '%s' "$archive" | grep -qEe '\.zip$'; then
		if [ $make_extract_dir -ne 0 ]; then
			unzip -d "$extract_dir" "$archive" ||\
				die "Failed to unpack $archive"
		else
			unzip "$archive" ||\
				die "Failed to unpack $archive"
		fi
	else
		if [ $make_extract_dir -ne 0 ]; then
			tar --one-top-level="$extract_dir" -xf "$archive" ||\
				die "Failed to unpack $archive"
		else
			tar -xf "$archive" ||\
				die "Failed to unpack $archive"
		fi
	fi
}

build_pythonpack()
{
	local python="$1"
	local name="$2"
	local archive="$3"
	local extract_dir="$4"
	local make_extract_dir="$5"

	info "Building $name for $python..."
	rm -rf "/tmp/$extract_dir"
	(
		cd /tmp || die "Failed to cd /tmp"
		extract_archive "$archive" "$extract_dir" "$make_extract_dir"
		cd "$extract_dir" ||\
			die "Failed to cd $extract_dir"
		"$python" ./setup.py install ||\
			die "Failed to install $name"
	) || die
	rm -r "/tmp/$extract_dir" ||\
		die "Failed to remove $name build files."
}

build_ppl()
{
	local archive="$PPL_FILE"
	for python in python3; do
		build_pythonpack "$python" "ppl-$PPL_VERSION" \
				 "$archive" "ppl-$PPL_VERSION" 1
	done
	rm "/tmp/$archive" ||\
		die "Failed to remove /tmp/$archive."
}

build_ppl2()
{
	local archive="$PPL2_FILE"
	for python in python3; do
		build_pythonpack "$python" "ppl2-$PPL2_VERSION" \
				 "$archive" "ppl2-$PPL2_VERSION" 1
	done
	rm "/tmp/$archive" ||\
		die "Failed to remove /tmp/$archive."
}

pilc_bootstrap_first_stage()
{
	echo "Running first stage..."

	[ "$(id -u)" = "0" ] || die "Permission denied. Must be root."

	# Check host tools (first/third stage).
	assert_program 7z
	assert_program chroot
	assert_program dd
	assert_program debootstrap
	assert_program git
	assert_program gpg
	assert_program install
	assert_program mkfs.ext4
	assert_program mkfs.vfat
	assert_program parted
	assert_program rsync
	assert_program setarch
	assert_program tar
	assert_program unzip
	assert_program wget
	[ -x "$opt_qemu" ] ||\
		die "The qemu binary '$opt_qemu' is not executable."

	info "Cleaning tmp..."
	rm -rf "$opt_target_dir"/tmp/*
	do_install -d -o root -g root -m 1777 "$opt_target_dir/tmp"

	info "Downloading and extracting keys..."
	do_install -o root -g root -m 644 \
		"$basedir_pilc/CF8A1AF502A2AA2D763BAE7E82B129927FA3303E.gpg" \
		"$opt_target_dir/tmp/"
	if [ $opt_bit -eq 32 ]; then
		download "$opt_target_dir/tmp/$KEYRING_TGZ_FILE" \
			 "$KEYRING_BASEURL/$KEYRING_TGZ_FILE" \
			 "$KEYRING_TGZ_SHA256"
		tar -C "$opt_target_dir/tmp" -x -f "$opt_target_dir/tmp/$KEYRING_TGZ_FILE" ||\
			die "Failed to extract keys."
		local raspbian_asc="$opt_target_dir/tmp/raspbian-archive-keyring-$KEYRING_VERSION/raspbian.public.key"
		local raspbian_gpg="$raspbian_asc.gpg"
		gpg --dearmor < "$raspbian_asc" > "$raspbian_gpg" ||\
			die "Failed to convert key."
	fi

	# debootstrap first stage.
	if [ $opt_skip_debootstrap1 -eq 0 ]; then
		info "Running debootstrap first stage..."
		if [ $opt_bit -eq 32 ]; then
			local arch="armhf"
			local keyopt="--keyring=$raspbian_gpg"
			local mirror="$MAIN_MIRROR_32"
		else
			local arch="arm64"
			local keyopt=
			local mirror="$MAIN_MIRROR_64"
		fi
		setarch "linux$opt_bit" \
			debootstrap --arch="$arch" --foreign \
			--components="main,contrib,non-free" \
			$keyopt \
			"$opt_suite" "$opt_target_dir" "$mirror" \
			|| die "debootstrap failed"
	fi
	[ -d "$opt_target_dir" ] ||\
		die "Target directory '$opt_target_dir' does not exist."

	# Avoid the start of daemons during second stage.
	do_install -o root -g root -m 755 \
		"$basedir_pilc/templates/policy-rc.d" \
		"$opt_target_dir/usr/sbin/"

	# Copy qemu.
	local qemu_bin="$opt_target_dir/$opt_qemu"
	if ! [ -x "$qemu_bin" ]; then
		info "Copying qemu binary from '$opt_qemu' to '$qemu_bin'..."
		do_install -d -o root -g root -m 755 \
			"$(dirname "$qemu_bin")"
		do_install -T -o root -g root -m 755 \
			"$opt_qemu" "$qemu_bin"
	fi

	info "Copying PiLC bootstrap script and templates..."
	do_install -o root -g root -m 755 \
		"$basedir_pilc/pilc-bootstrap.sh" \
		"$opt_target_dir/"
	cp -r "$basedir_pilc/templates" "$opt_target_dir/tmp/" ||\
		die "Failed to copy PiLC templates"
	cp -r "$basedir_pilc/deb" "$opt_target_dir/tmp/" ||\
		die "Failed to copy PiLC deb packages"

	info "Checking out awlsim..."
	local awlsim_dir="$opt_target_dir/tmp/awlsim"
	local checkout_dir="$awlsim_dir/src"
	rm -rf "$awlsim_dir"
	do_install -d -o root -g root -m 755 "$awlsim_dir"
	git clone --no-checkout "$basedir/.git" "$checkout_dir" ||\
		die "Failed to clone"
	(
		cd "$checkout_dir" ||\
			die "Failed to cd"
		git checkout "$opt_branch" ||\
			die "Failed to check out branch."
		git submodule update --init submodules/pyprofibus ||\
			die "Failed to pull pyprofibus submodule"
		rm -r .git submodules/pyprofibus/.git ||\
			die "Failed to remove .git directory."
		mv submodules/pyprofibus .. ||\
			die "Failed to move pyprofibus submodule."
	) || die

	# Fetch packages
	download "$opt_target_dir/tmp/$PPL_FILE" \
		 "$PPL_MIRROR" \
		 "$PPL_SHA256"
	download "$opt_target_dir/tmp/$PPL2_FILE" \
		 "$PPL2_MIRROR" \
		 "$PPL2_SHA256"

	# Second stage will mount a few filesystems.
	# Keep track to umount them in cleanup.
	mp_proc="$opt_target_dir/proc"
	mp_proc_binfmt_misc="$opt_target_dir/proc/sys/fs/binfmt_misc"
	mp_sys="$opt_target_dir/sys"
	mp_shm="$opt_target_dir/dev/shm"
}

pilc_bootstrap_second_stage()
{
	info "Running second stage..."

	[ -x /pilc-bootstrap.sh ] ||\
		die "Second stage does not contain the bootstrap script."

	# Set up environment.
	export LC_ALL=C
	export LANGUAGE=C
	export LANG=C
	if [ "$opt_rpiver" = "1" -o "$opt_rpiver" = "0" ]; then
		info "Optimizing for RPi 1, zero(w)"
		local march="-march=armv6kz"
		local mtune="-mtune=arm1176jzf-s"
	elif [ "$opt_rpiver" = "2" ]; then
		info "Optimizing for RPi 2"
		local march="-march=armv7-a"
		local mtune="-mtune=cortex-a7"
	elif [ "$opt_rpiver" = "3" ]; then
		info "Optimizing for RPi 3"
		local march="-march=armv8-a"
		local mtune="-mtune=cortex-a53"
	elif [ "$opt_rpiver" = "4" ]; then
		info "Optimizing for RPi 4"
		local march="-march=armv8-a"
		local mtune="-mtune=cortex-a72"
	else
		info "Optimizing for generic RPi"
		if [ $opt_bit -eq 32 ]; then
			local march="-march=armv6kz"
			local mtune=
		else
			local march="-march=armv8-a"
			local mtune=
		fi
	fi
	export CFLAGS="-O3 $march $mtune -pipe"
	[ $opt_bit -eq 32 ] && export CFLAGS="$CFLAGS -mfpu=vfp -mfloat-abi=hard"
	export CXXFLAGS="$CFLAGS"

	# debootstrap second stage.
	if [ $opt_skip_debootstrap2 -eq 0 ]; then
		info "Running debootstrap second stage..."
		/debootstrap/debootstrap --verbose --second-stage ||\
			die "Debootstrap second stage failed."
	fi

	if [ $opt_bit -eq 32 ]; then
		info "Disabling raspi-copies-and-fills..."
		rm -f /etc/ld.so.preload || die "Failed to disable raspi-copies-and-fills"
	fi

	info "Mounting /proc..."
	do_install -d -o root -g root -m 755 /proc
	mount -t proc proc /proc || die "Mounting /proc failed."

	info "Mounting /sys..."
	do_install -d -o root -g root -m 755 /sys
	mount -t sysfs sysfs /sys || die "Mounting /sys failed."

	info "Mounting /dev/shm..."
	do_install -d -o root -g root -m 755 /dev/shm
	mount -t tmpfs tmpfs /dev/shm || die "Mounting /dev/shm failed."

	info "Creating /etc/fstab"
	do_install -d -o root -g root -m 755 /config
	do_install -T -o root -g root -m 644 \
		/tmp/templates/fstab \
		/etc/fstab

	info "Writing misc /etc stuff..."
	echo "pilc" > /etc/hostname || die "Failed to set hostname"
	printf 'PiLC GNU/Linux (based on Raspberry Pi OS) \\n \\l\n\n' > /etc/issue ||\
		die "Failed to create /etc/issue"
	printf 'PiLC GNU/Linux (based on Raspberry Pi OS)\n' > /etc/issue.net ||\
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
	sed -i -e 's|ID_LIKE=.*|ID_LIKE=debian|' \
		/etc/os-release ||\
		die "Failed to set os-release ID_LIKE."
	sed -i -e 's|HOME_URL=.*|HOME_URL="https://bues.ch/a/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release HOME_URL."
	sed -i -e 's|SUPPORT_URL=.*|SUPPORT_URL="https://bues.ch/a/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release SUPPORT_URL."
	sed -i -e 's|BUG_REPORT_URL=.*|BUG_REPORT_URL="https://bues.ch/a/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release BUG_REPORT_URL."

	info "Writing apt configuration..."
	local apt_opts="-y -o Acquire::Retries=3"
	if [ $opt_bit -eq 32 ]; then
		cat > /etc/apt/sources.list <<EOF
deb $MAIN_MIRROR_32 $opt_suite main contrib non-free rpi firmware
#deb-src $MAIN_MIRROR_32 $opt_suite main contrib non-free rpi firmware
EOF
		[ $? -eq 0 ] || die "Failed to set sources.list"
	else
		cat > /etc/apt/sources.list <<EOF
deb $MAIN_MIRROR_64 $opt_suite main contrib non-free
#deb-src $MAIN_MIRROR_64 $opt_suite main contrib non-free
deb $MAIN_MIRROR_64_SECURITY $opt_suite/updates main contrib non-free
#deb-src $MAIN_MIRROR_64_SECURITY $opt_suite/updates main contrib non-free
deb $MAIN_MIRROR_64 $opt_suite-updates main contrib non-free
#deb-src $MAIN_MIRROR_64 $opt_suite-updates main contrib non-free
EOF
		[ $? -eq 0 ] || die "Failed to set sources.list"
		dpkg --add-architecture armhf ||\
			die "dpkg --add-architecture failed"
	fi
	echo 'Acquire { Languages "none"; };' > /etc/apt/apt.conf.d/99no-translations ||\
		die "Failed to set apt.conf.d"
	cat /tmp/templates/debconf-set-selections-preinstall.conf | debconf-set-selections ||\
		die "Failed to configure debconf settings"
	apt-get $apt_opts update ||\
		die "apt-get update failed"
	apt-get $apt_opts install apt-transport-https ||\
		die "apt-get install apt-transport-https failed"
	apt-get $apt_opts install \
		gnupg2 \
		debian-keyring \
		|| die "apt-get install keyrings failed"
	cat >> /etc/apt/sources.list <<EOF
deb $MAIN_MIRROR_ARCHIVE $opt_suite main ui
#deb-src $MAIN_MIRROR_ARCHIVE $opt_suite main ui
EOF
	[ $? -eq 0 ] || die "Failed to update sources.list"
	apt-key add /tmp/CF8A1AF502A2AA2D763BAE7E82B129927FA3303E.gpg ||\
		die "apt-key add failed"
	apt-get $apt_opts update ||\
		die "apt-get update failed"
	if [ $opt_bit -eq 32 ]; then
		apt-get $apt_opts install \
			raspberrypi-archive-keyring \
			raspbian-archive-keyring \
			|| die "apt-get install archive-keyrings failed"
	else
		apt-get $apt_opts install \
			raspberrypi-archive-keyring \
			|| die "apt-get install archive-keyrings failed"
	fi

	info "Upgrading system..."
	apt-get $apt_opts dist-upgrade ||\
		die "apt-get dist-upgrade failed"

	info "Installing packages..."
	apt-get $apt_opts install \
		aptitude \
		bash \
		build-essential \
		console-setup \
		cython3 \
		dbus \
		debconf-utils \
		debsums \
		devscripts \
		ethtool \
		fdisk \
		firmware-atheros \
		firmware-brcm80211 \
		firmware-libertas \
		firmware-linux \
		firmware-linux-free \
		firmware-linux-nonfree \
		firmware-misc-nonfree \
		firmware-realtek \
		git \
		htop \
		i2c-tools \
		irqbalance \
		iw \
		locales \
		nano \
		ntp \
		openssh-server \
		parted \
		python3 \
		python3-cffi \
		python3-dev \
		python3-serial \
		python3-setuptools \
		python3-spidev \
		rng-tools \
		schedtool \
		sudo \
		systemd \
		tmux \
		vim \
		wireless-tools \
		wpasupplicant \
		|| die "apt-get install failed"

	info "Configuring locales..."
	dpkg-reconfigure -u locales ||\
		die "Failed to reconfigure locales"

	info "Configuring console..."
	sed -i -e 's|CHARMAP=.*|CHARMAP="UTF-8"|' \
		-e 's|FONTFACE=.*|FONTFACE=""|' \
		-e 's|FONTSIZE=.*|FONTSIZE=""|' \
		/etc/default/console-setup ||\
		die "Failed to edit /etc/default/console-setup"

	info "Creating /etc/rc.local..."
	do_install -o root -g root -m 755 \
		/tmp/templates/rc.local \
		/etc/

	info "Creating users/groups..."
	userdel -f pi
	groupdel pi
	rm -rf /home/pi
	groupadd -g 1000 pi ||\
		die "Failed to create group pi."
	useradd -u 1000 -d /home/pi -m -g pi\
		-G pi,lp,dialout,cdrom,floppy,audio,dip,src,video,plugdev,netdev,i2c\
		-s /bin/bash\
		pi ||\
		die "Failed to create user pi."
	printf 'raspberry\nraspberry\n' | passwd pi ||\
		die "Failed to set 'pi' password."

	info "Initializing home directory..."
	do_install -d -o pi -g pi -m 755 /home/pi/.vim
	do_install -o pi -g pi -m 644 \
		/tmp/templates/vimrc \
		/home/pi/.vim/
	do_install -T -o pi -g pi -m 644 \
		/tmp/templates/tmux.conf \
		/home/pi/.tmux.conf

	info "Installing Raspberry Pi OS packages..."
	apt-get $apt_opts install \
		libraspberrypi-bin \
		libraspberrypi-dev \
		libraspberrypi-doc \
		python3-rpi.gpio \
		raspberrypi-bootloader \
		raspberrypi-kernel \
		raspberrypi-net-mods \
		raspberrypi-sys-mods \
		raspi-config \
		raspi-gpio \
		raspinfo \
		rpi-eeprom \
		rpi-eeprom-images \
		|| die "apt-get install failed"

	info "Removing unnecessary keys and repos..."
	for file in /etc/apt/trusted.gpg.d/microsoft.gpg \
		    /etc/apt/sources.list.d/vscode.list; do
		info "Replacing $file with dummy..."
		if [ -e "$file" ]; then
			rm "$file" || die "Failed to rm $file"
		fi
		touch "$file" || die "Failed to touch $file"
		chmod 444 "$file" || die "Failed to chmod 444 $file"
	done
	for file in /etc/apt/*.gpg~; do
		if [ -e "$file" ]; then
			info "Removing $file..."
			rm "$file" || die "Failed to rm $file"
		fi
	done
	apt-get $apt_opts update ||\
		die "apt-get update failed"

	info "Running debconf-set-selections..."
	cat /tmp/templates/debconf-set-selections-postinstall.conf | debconf-set-selections ||\
		die "Failed to configure debconf settings"

	info "Cleaning apt..."
	apt-get $apt_opts autoremove --purge ||\
		die "apt-get autoremove failed"
	apt-get $apt_opts clean ||\
		die "apt-get clean failed"

	info "Disabling some services..."
	do_systemctl mask apt-daily.service
	do_systemctl mask apt-daily.timer
	do_systemctl mask apt-daily-upgrade.timer
	do_systemctl mask rsync.service
	do_systemctl mask exim4.service
	do_systemctl mask triggerhappy.service
	do_systemctl mask triggerhappy.socket
	do_systemctl mask alsa-state.service
	do_systemctl mask alsa-restore.service
	do_systemctl mask alsa-utils.service

	info "Building and installing PiLC system package..."
	(
		cd /tmp/deb/pilc-system || die "Failed to cd to pilc-system"
		debuild -uc -us -b -d || die "debuild failed"
		dpkg -i ../pilc-system_*.deb || die "Failed to install pilc-system"
		# Copy debs
		rm -rf /home/pi/deb/pilc-system
		do_install -d -o pi -g pi -m 755 /home/pi/deb/pilc-system
		do_install -o pi -g pi -m 644 \
			../*pilc-system*.deb \
			/home/pi/deb/pilc-system/
	) || die

	info "Updating /etc/hosts..."
	if ! grep -qe pilc /etc/hosts; then
		printf '\n127.0.0.1\tpilc\n' >> /etc/hosts ||\
			die "Failed to update /etc/hosts"
	fi

	info "Building Python modules..."
	build_ppl
	build_ppl2

	info "Building awlsim..."
	(
		cd /tmp/awlsim/src || die "Failed to cd"
		if [ $opt_cython -eq 0 ]; then
			# Disable cython
			sed -i -e '/Package: cython/,/^$/ d' \
				debian/control ||\
				die "Failed to patch control file (cython)"
			sed -i -e 's/export AWLSIM_CYTHON_BUILD=1/export AWLSIM_CYTHON_BUILD=0/' \
				debian/rules ||\
				die "Failed to patch rules file (cython)"
		fi

		# Update the systemd service file.
		sed -i -e 's|AWLSIM_SCHED=|AWLSIM_SCHED=realtime-if-multicore|g' \
		       -e 's|AWLSIM_PRIO=|AWLSIM_PRIO=50|g' \
		       -e 's|AWLSIM_AFFINITY=|AWLSIM_AFFINITY=-1,-2,-3|g' \
		       -e 's|AWLSIM_MLOCK=|AWLSIM_MLOCK=1|g' \
		       awlsim-server.service ||\
		       die "Failed to patch awlsim-server.service"

		# Build the packages.
		debuild -uc -us -b -d || die "debuild failed"

		info "Installing awlsim..."
		# Core
		dpkg -i ../python3-awlsim_*.deb ||\
			die "Failed to install python3-awlsim"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython3-awlsim_*.deb ||\
				die "Failed to install cython3-awlsim"
		fi
		# hardware: dummy
		dpkg -i ../python3-awlsimhw-dummy_*.deb ||\
			die "Failed to install python3-awlsimhw-dummy"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython3-awlsimhw-dummy_*.deb ||\
				die "Failed to install cython3-awlsimhw-dummy"
		fi
		# hardware: linuxcnc
		dpkg -i ../python3-awlsimhw-linuxcnc_*.deb ||\
			die "Failed to install python3-awlsimhw-linuxcnc"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython3-awlsimhw-linuxcnc_*.deb ||\
				die "Failed to install cython3-awlsimhw-linuxcnc"
		fi
		# hardware: profibus
		dpkg -i ../python3-awlsimhw-profibus_*.deb ||\
			die "Failed to install python3-awlsimhw-profibus"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython3-awlsimhw-profibus_*.deb ||\
				die "Failed to install cython3-awlsimhw-profibus"
		fi
		# hardware: RPi GPIO
		dpkg -i ../python3-awlsimhw-rpigpio_*.deb ||\
			die "Failed to install python3-awlsimhw-rpigpio"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython3-awlsimhw-rpigpio_*.deb ||\
				die "Failed to install cython3-awlsimhw-rpigpio"
		fi
		# hardware: PiXtend
		dpkg -i ../python3-awlsimhw-pixtend_*.deb ||\
			die "Failed to install python3-awlsimhw-pixtend"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython3-awlsimhw-pixtend_*.deb ||\
				die "Failed to install cython3-awlsimhw-pixtend"
		fi
		# Executables
		dpkg -i ../awlsim-server_*.deb ||\
			die "Failed to install awlsim-server"
		dpkg -i ../awlsim-client_*.deb ||\
			die "Failed to install awlsim-client"
		dpkg -i ../awlsim-symtab_*.deb ||\
			die "Failed to install awlsim-symtab"
		dpkg -i ../awlsim-test_*.deb ||\
			die "Failed to install awlsim-test"
		dpkg -i ../awlsim-proupgrade_*.deb ||\
			die "Failed to install awlsim-proupgrade"
		# Copy debs
		rm -rf /home/pi/deb/awlsim
		do_install -d -o pi -g pi -m 755 /home/pi/deb/awlsim
		do_install -o pi -g pi -m 644 \
			../*awlsim*.deb \
			/home/pi/deb/awlsim/
		# Copy examples
		do_install -T -o pi -g pi -m 644 \
			examples/EXAMPLE.awlpro \
			/home/pi/generic-example.awlpro
		do_install -T -o pi -g pi -m 644 \
			examples/raspberrypi-gpio.awlpro \
			/home/pi/raspberrypi-gpio-example.awlpro
		do_install -T -o pi -g pi -m 644 \
			examples/raspberrypi-profibus.awlpro \
			/home/pi/raspberrypi-profibus-example.awlpro
		do_install -T -o pi -g pi -m 644 \
			examples/raspberrypi-pixtend.awlpro \
			/home/pi/raspberrypi-pixtend-example.awlpro
	) || die
	info "Building pyprofibus..."
	(
		cd /tmp/awlsim/pyprofibus ||\
			die "Failed to cd"
		if [ $opt_cython -eq 0 ]; then
			# Disable cython
			sed -i -e '/Package: cython/,/^$/ d' \
				debian/control ||\
				die "Failed to patch control file (cython)"
			sed -i -e 's/export PYPROFIBUS_CYTHON_BUILD=1/export PYPROFIBUS_CYTHON_BUILD=0/' \
				debian/rules ||\
				die "Failed to patch rules file (cython)"
		fi

		# Build the packages.
		debuild -uc -us -b -d || die "debuild failed"

		info "Installing pyprofibus..."
		dpkg -i ../python3-pyprofibus_*.deb ||\
			die "Failed to install python3-pyprofibus"
		dpkg -i ../profisniff_*.deb ||\
			die "Failed to install profisniff"
		dpkg -i ../gsdparser_*.deb ||\
			die "Failed to install gsdparser"

		# Copy debs
		rm -rf /home/pi/deb/pyprofibus
		do_install -d -o pi -g pi -m 755 /home/pi/deb/pyprofibus
		do_install -o pi -g pi -m 644 \
			../*pyprofibus*.deb \
			../profisniff_*.deb \
			../gsdparser_*.deb \
			/home/pi/deb/pyprofibus/
	) || die
	rm -r /tmp/awlsim ||\
		die "Failed to remove awlsim checkout."

	info "Updating home directory permissions..."
	chown -R pi:pi /home/pi || die "Failed to change /home/pi permissions."

	# Remove rc.d policy file
	if [ -e /usr/sbin/policy-rc.d ]; then
		rm /usr/sbin/policy-rc.d ||\
			die "Failed to remove policy-rc.d"
	fi

	if [ $opt_bit -eq 32 ]; then
		# Install this last. It won't work correctly in the qemu environment.
		info "Installing raspi-copies-and-fills..."
		apt-get $apt_opts install --reinstall raspi-copies-and-fills ||\
			die "apt-get install failed"
	fi

	info "Stopping processes..."
	for i in dbus ssh irqbalance; do
		/etc/init.d/$i stop
	done
}

pilc_bootstrap_third_stage()
{
	info "Running third stage..."

	info "Umounting /dev/shm..."
	umount -l "$mp_shm" || die "Failed to umount /dev/shm"
	info "Umounting /sys..."
	umount -l "$mp_sys" || die "Failed to umount /sys"
	info "Umounting /proc/sys/fs/binfmt_misc..."
	umount -l "$mp_proc_binfmt_misc"
	info "Umounting /proc..."
	umount -l "$mp_proc" || die "Failed to umount /proc"

	info "Removing PiLC bootstrap script..."
	rm "$opt_target_dir/pilc-bootstrap.sh" ||\
		die "Failed to remove bootstrap script."

	info "Cleaning tmp..."
	rm -rf "$opt_target_dir"/tmp/*

	info "Configuring boot..."
	do_install -T -o root -g root -m 644 \
		"$basedir_pilc/templates/boot_cmdline.txt" \
		"$opt_target_dir/boot/cmdline.txt"
	do_install -T -o root -g root -m 644 \
		"$basedir_pilc/templates/boot_config.txt" \
		"$opt_target_dir/boot/config.txt"
	if [ $opt_bit -eq 64 ]; then
		sed -i -e 's/arm_64bit=0/arm_64bit=1/g' \
			"$opt_target_dir/boot/config.txt" ||\
			die "Failed to set arm_64bit=1"
	fi

	# Prepare image paths.
	local imgfile="${opt_target_dir}${opt_imgsuffix}.img"
	local imgfile_zip="${imgfile}.7z"
	local bootimgfile="${imgfile}.boot"
	mp_bootimgfile="${bootimgfile}.mp"
	local rootimgfile="${imgfile}.root"
	mp_rootimgfile="${rootimgfile}.mp"
	rm -f "$imgfile" "$imgfile_zip" "$rootimgfile" "$bootimgfile"
	rmdir "$mp_bootimgfile" "$mp_rootimgfile" 2>/dev/null

	# Create images.
	if [ "$opt_img" -ne 0 ]; then
		# Calculate image size.
		local imgsize_b="$(expr "$opt_imgsize" \* 1000 \* 1000 \* 1000)"
		local imgsize_mib="$(expr "$imgsize_b" \/ 1024 \/ 1024)"
		# Reduce the size to make sure it fits every SD card.
		local imgsize_mib_red="$(expr \( "$imgsize_mib" \* 98 \) \/ 100)"
		[ -n "$imgsize_mib_red" ] || die "Failed to calculate image size"
		info "SD image size = $imgsize_mib_red MiB"

		info "Creating boot image..."
		mkfs.vfat -F 32 -i 7771B0BB -n boot -C "$bootimgfile" \
			$(expr \( 256 \* 1024 \) ) ||\
			die "Failed to create boot partition file system."
		mkdir "$mp_bootimgfile" ||\
			die "Failed to make boot partition mount point."
		mount -o loop "$bootimgfile" "$mp_bootimgfile" ||\
			die "Failed to mount boot partition."
		rsync -aHAX --inplace \
			"$opt_target_dir/boot/" "$mp_bootimgfile/" ||\
			die "Failed to copy boot files."
		umount "$mp_bootimgfile" ||\
			die "Failed to umount boot partition."
		rmdir "$mp_bootimgfile" ||\
			die "Failed to remove boot partition mount point."

		info "Creating root image..."
		mkfs.ext4 "$rootimgfile" $(expr \( "$imgsize_mib_red" - \( 256 + 4 + 4 \) \) \* 1024 ) ||\
			die "Failed to create root filesystem."
		mkdir "$mp_rootimgfile" ||\
			die "Failed to make root partition mount point."
		mount -o loop "$rootimgfile" "$mp_rootimgfile" ||\
			die "Failed to mount root partition."
		rsync -aHAX --inplace \
			--exclude='boot/*' \
			--exclude='dev/shm/*' \
			--exclude='proc/*' \
			--exclude='run/*' \
			--exclude='sys/*' \
			--exclude='tmp/*' \
			--exclude="$(basename "$opt_qemu")" \
			"$opt_target_dir/" "$mp_rootimgfile/" ||\
			die "Failed to copy root files."
		umount "$mp_rootimgfile" ||\
			die "Failed to umount root partition."
		rmdir "$mp_rootimgfile" ||\
			die "Failed to remove root partition mount point."

		info "Creating image '$imgfile'..."
		dd if=/dev/zero of="$imgfile" bs=1M count="$imgsize_mib_red" conv=sparse ||\
			die "Failed to create image file."
		parted "$imgfile" <<EOF
unit b
mklabel msdos
mkpart primary fat32 $(expr 4 \* 1024 \* 1024) $(expr \( 256 + 4 \) \* 1024 \* 1024)
mkpart primary ext4 $(expr \( 256 + 4 + 4 \) \* 1024 \* 1024) 100%
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
			seek="$(expr 256 + 4 + 4)" bs=1M conv=notrunc,sparse ||\
			die "Failed to integrate root partition."
		rm "$rootimgfile" ||\
			die "Failed to delete root partition image."

		# Create zipped image.
		if [ "$opt_zimg" -ne 0 ]; then
			info "Compressing image..."
			7z -mx=9 a "$imgfile_zip" "$imgfile" ||\
				die "Failed to compress partition image."
		fi

		# Write the image to the SD card.
		if [ -n "$opt_writedev" ]; then
			write_image "$imgfile" "$opt_writedev"
		fi
	fi
}

usage()
{
	echo "pilc-bootstrap.sh [OPTIONS] TARGET_DIR"
	echo
	echo "Options:"
	echo
	echo " --branch|-b BRANCH      Select the awlsim branch or tag."
	echo "                         Default: $default_branch"
	echo
	echo " --no-cython|-C          Do not build Cython modules."
	echo "                         Default: Build cython modules"
	echo
	echo " --suite|-s SUITE        Select the suite."
	echo "                         Default: $default_suite"
	echo
	echo " --bit|-B BIT            Build 32 bit or 64 bit image."
	echo "                         Default: $default_bit"
	echo
	echo " --qemu-bin|-Q PATH      Select qemu-user-static binary."
	echo "                         Default: $default_qemu"
	echo
	echo " --img-suffix|-X SUFFIX  Image file suffix."
	echo "                         Default: $default_imgsuffix"
	echo
	echo " --img-size|-S SIZEGB    Image file size, in Gigabytes (base 1000)."
	echo "                         Default: $default_imgsize"
	echo
	echo " --no-img|-I             Do not create an image."
	echo "                         Default: Create image."
	echo
	echo " --no-zimg|-Z            Do not create a 7zipped image."
	echo "                         Default: Create 7zipped image."
	echo
	echo " --write|-w DEV          Write image to an SD card after bootstrap."
	echo "                         DEV must be the /dev/mmcblkX path to the card."
	echo
	echo " --write-only|-W DEV     Write an existing image to an SD card"
	echo "                         without bootstrap and image generation."
	echo
	echo " --skip-debootstrap1|-1  Skip debootstrap first stage."
	echo " --skip-debootstrap2|-2  Skip debootstrap second stage."
	echo
	echo " --quick|-q              Quick build. This is a shortcut for:"
	echo "                         --no-cython --no-zimg"
	echo
	echo " --rpiver|-R VERSION     Raspberry Pi version to build for."
	echo "                         Can be either 0, 1, 2, 3, 4 or generic"
	echo "                         0 and 1 are equivalent."
	echo "                         generic runs on any Raspberry Pi 0-4."
	echo "                         Default: generic"
}

# canonicalize basedir
basedir="$(readlink -e "$basedir")"
[ -n "$basedir" ] || die "Failed to canonicalize base directory."

# Directory containing the PiLC bootstrapping files.
basedir_pilc="$basedir/pilc"

# Mountpoints. Will be umounted on cleanup.
mp_shm=
mp_proc=
mp_proc_binfmt_misc=
mp_sys=
mp_bootimgfile=
mp_rootimgfile=

trap term_signal TERM INT

if [ -z "$__PILC_BOOTSTRAP_SECOND_STAGE__" ]; then
	# First stage

	export _NPROCESSORS_ONLN="$(getconf _NPROCESSORS_ONLN)"
	[ -n "$_NPROCESSORS_ONLN" ] || die "Failed to get # of online CPUs"

	default_branch="master"
	default_suite="$DEFAULT_SUITE"
	default_bit=32
	default_qemu="/usr/bin/qemu-arm-static"
	default_imgsuffix="-$(date '+%Y%m%d')"
	default_imgsize=4
	default_img=1
	default_zimg=1
	default_writedev=
	default_writeonly=0
	default_rpiver="generic"

	opt_target_dir=
	opt_branch="$default_branch"
	opt_cython=1
	opt_suite="$default_suite"
	opt_bit="$default_bit"
	opt_qemu="$default_qemu"
	opt_skip_debootstrap1=0
	opt_skip_debootstrap2=0
	opt_imgsuffix="$default_imgsuffix"
	opt_imgsize="$default_imgsize"
	opt_img="$default_img"
	opt_zimg="$default_zimg"
	opt_writedev="$default_writedev"
	opt_writeonly="$default_writeonly"
	opt_rpiver="$default_rpiver"

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
		--suite|-s)
			shift
			opt_suite="$1"
			[ -n "$opt_suite" ] || die "No suite given"
			;;
		--bit|-B)
			shift
			opt_bit="$1"
			[ "$opt_bit" = "32" -o "$opt_bit" = "64" ] || die "Invalid --bit. Must be 32 or 64."
			;;
		--qemu-bin|-Q)
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
		--img-suffix|-X)
			shift
			opt_imgsuffix="$1"
			;;
		--img-size|-S)
			shift
			opt_imgsize="$(expr "$1" \* 1)"
			[ -n "$opt_imgsize" ] || die "--img-size|-S is invalid"
			;;
		--no-zimg|-Z)
			opt_zimg=0
			;;
		--no-img|-I)
			opt_img=0
			;;
		--quick|-q)
			opt_cython=0
			opt_zimg=0
			;;
		--write|-w|--write-only|-W)
			if [ "$1" = "--write" -o "$1" = "-w" ]; then
				opt_writeonly=0
			else
				opt_writeonly=1
			fi
			shift
			opt_writedev="$1"
			[ -b "$opt_writedev" ] || die "Invalid SD card block device"
			;;
		--rpiver|-R)
			shift
			opt_rpiver="$1"
			[ "$opt_rpiver" = "generic" -o\
			  "$opt_rpiver" = "0" -o\
			  "$opt_rpiver" = "1" -o\
			  "$opt_rpiver" = "2" -o\
			  "$opt_rpiver" = "3" -o\
			  "$opt_rpiver" = "4" ] || die "Invalid --rpiver|-R"
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
	opt_target_dir="$(readlink -m "${opt_target_dir}")"
	[ -n "$opt_target_dir" ] || die "Failed to resolve target dir."
	[ -d "$opt_target_dir" -o ! -e "$opt_target_dir" ] ||\
		die "$opt_target_dir is not a directory"
	if [ "$opt_rpiver" = "2" -o "$opt_rpiver" = "1" -o "$opt_rpiver" = "0" ]; then
		[ $opt_bit -eq 32 ] || die "Option --bit must be 32 for RPi zero, 1 or 2."
	fi

	trap cleanup EXIT

	if [ -n "$opt_writedev" -a $opt_writeonly -ne 0 ]; then
		# Just write the image to the SD card, then exit.
		write_image "${opt_target_dir}${opt_imgsuffix}.img" "$opt_writedev"
		exit 0
	fi

	# Run first stage.
	pilc_bootstrap_first_stage

	info "Starting second stage."
	# Export options for use by second stage.
	export opt_target_dir
	export opt_branch
	export opt_cython
	export opt_suite
	export opt_bit
	export opt_qemu
	export opt_skip_debootstrap1
	export opt_skip_debootstrap2
	export opt_imgsuffix
	export opt_zimg
	export opt_img
	export opt_writedev
	export opt_writeonly
	export opt_rpiver
	export __PILC_BOOTSTRAP_SECOND_STAGE__=1
	setarch "linux$opt_bit" \
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
