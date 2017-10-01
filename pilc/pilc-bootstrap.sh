#!/bin/sh
#
# PiLC bootstrap
#
# Copyright 2016-2017 Michael Buesch <m@bues.ch>
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


MAIN_MIRROR="http://mirrordirector.raspbian.org/raspbian/"
DEFAULT_SUITE=stretch

RPIGPIO_VERSION="0.6.3"
RPIGPIO_MIRROR="https://netcologne.dl.sourceforge.net/project/raspberry-gpio-python/RPi.GPIO-$RPIGPIO_VERSION.tar.gz"
RPIGPIO_SHA256="9366ff36104a39368759929e71f0d8ad6a88553497b3064cbc40f4248806cc19"


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
			umount "$mp" >/dev/null 2>&1
	done
	for mp in "$mp_bootimgfile" "$mp_rootimgfile"; do
		[ -n "$mp" -a -d "$mp" ] &&\
			rmdir "$mp" >/dev/null 2>&1
	done
}

write_image()
{
	local image="$1"
	local dev="$2"

	info "Writing $image to $dev ..."

	[ -b "$dev" ] || die "$dev is not a block device"
	mount | grep -q "$dev" && die "$dev is mounted. Refusing to write to it!"

	dd if="$image" of="$dev" bs=32M status=progress ||\
		die "Failed to write image."
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

# GPU memory
gpu_mem=16

#uncomment to overclock the arm. 700 MHz is the default.
#arm_freq=800

# Uncomment some or all of these to enable the optional hardware interfaces
dtparam=i2c_arm=on
dtparam=i2c_vc=on
#dtparam=i2s=on
#dtparam=spi=on

# Uncomment this to enable the lirc-rpi module
#dtoverlay=lirc-rpi

# Additional overlays and parameters are documented /boot/overlays/README

# Enable audio (loads snd_bcm2835)
dtparam=audio=on
EOF
}

policy_rcd_file()
{
	cat <<EOF
#!/bin/sh
exit 101
EOF
}

download()
{
	local target="$1"
	local mirror="$2"
	local sha256="$3"

	info "Downloading $mirror..."
	rm -f "$target"
	wget -O "$target" "$mirror" || die "Failed to fetch $mirror"
	[ "$(sha256sum -b "$target" | cut -f1 -d' ')" = "$sha256" ] ||\
		die "SHA256 verification of $target failed"
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
	assert_program install
	[ -x "$opt_qemu" ] ||\
		die "The qemu binary '$opt_qemu' is not executable."

	# debootstrap first stage.
	if [ $opt_skip_debootstrap1 -eq 0 ]; then
		info "Running debootstrap first stage..."
		debootstrap --arch="$opt_arch" --foreign --verbose \
			--keyring="$basedir/pilc/raspbian.public.key.gpg" \
			"$opt_suite" "$opt_target_dir" "$MAIN_MIRROR" \
			|| die "debootstrap failed"
		mkdir -p "$opt_target_dir/usr/share/keyrings" ||\
			die "Failed to create keyrings dir."
		cp "$basedir/pilc/raspbian.archive.public.key.gpg" \
		   "$opt_target_dir/usr/share/keyrings/" ||\
			die "Failed to copy raspbian.archive.public.key.gpg."
		cp /usr/share/keyrings/debian-archive-keyring.gpg \
		   "$opt_target_dir/usr/share/keyrings/debian-archive-keyring.gpg" ||\
			die "Failed to copy debian-archive-keyring.gpg."
	fi
	[ -d "$opt_target_dir" ] ||\
		die "Target directory '$opt_target_dir' does not exist."

	# Avoid the start of daemons during second stage.
	policy_rcd_file > "$opt_target_dir/usr/sbin/policy-rc.d" ||\
		die "Failed to create policy-rc.d"
	chmod 755 "$opt_target_dir/usr/sbin/policy-rc.d" ||\
		die "Failed to chmod policy-rc.d"

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
	cp "$basedir/pilc/pilc-bootstrap.sh" "$opt_target_dir/" ||\
		die "Failed to copy bootstrap script."

	info "Checking out awlsim..."
	local awlsim_dir="$opt_target_dir/tmp/awlsim"
	local checkout_dir="$awlsim_dir/src"
	rm -rf "$awlsim_dir"
	mkdir -p "$awlsim_dir" || die "mkdir failed"
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

	# Fetch RPi.GPIO
	download "$opt_target_dir/tmp/RPi.GPIO-$RPIGPIO_VERSION.tar.gz" \
		"$RPIGPIO_MIRROR" "$RPIGPIO_SHA256"

	# Copy kernel tree
	if [ "$opt_kernel" = "pilc" ]; then
		info "Copying PiLC kernel tree..."
		rsync -rlt --inplace --exclude='.git*' \
			"$basedir/pilc/kernel/" "$opt_target_dir/tmp/kernel/" ||\
			die "Failed to copy PiLC kernel."
		cp "$basedir/pilc/kernel.config" "$opt_target_dir/tmp/kernel/.config" ||\
			die "Failed to copy PiLC kernel config."
	fi

	# Second stage will mount a few filesystems.
	# Keep track to umount them in cleanup.
	mp_proc="$opt_target_dir/proc"
	mp_proc_binfmt_misc="$opt_target_dir/proc/sys/fs/binfmt_misc"
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
	export CFLAGS="-O3 -march=armv6j -mfpu=vfp -mfloat-abi=hard -pipe"
	export CXXFLAGS="$CFLAGS"
#	export CC=clang LINKCC=clang LDSHARED="clang -shared" CXX=clang++

	# debootstrap second stage.
	if [ $opt_skip_debootstrap2 -eq 0 ]; then
		info "Running debootstrap second stage..."
		/debootstrap/debootstrap --verbose --second-stage ||\
			die "Debootstrap second stage failed."
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

	info "Writing apt configuration..."
cat > /etc/apt/sources.list <<EOF
deb $MAIN_MIRROR $opt_suite main firmware rpi
deb http://archive.raspberrypi.org/debian/ $opt_suite main ui
EOF
	[ $? -eq 0 ] || die "Failed to set sources.list"
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
	sed -i -e 's|HOME_URL=.*|HOME_URL="https://bues.ch/a/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release HOME_URL."
	sed -i -e 's|SUPPORT_URL=.*|SUPPORT_URL="https://bues.ch/a/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release SUPPORT_URL."
	sed -i -e 's|BUG_REPORT_URL=.*|BUG_REPORT_URL="https://bues.ch/a/pilc"|' \
		/etc/os-release ||\
		die "Failed to set os-release BUG_REPORT_URL."

	info "Updating packages..."
cat <<EOF | debconf-set-selections
debconf	debconf/priority	select	high
debconf	debconf/frontend	select	Noninteractive
locales	locales/locales_to_be_generated	multiselect	en_US.UTF-8 UTF-8
locales	locales/default_environment_locale	select	None
EOF
	[ $? -eq 0 ] || die "Failed to configure debconf settings"
	apt-key add /usr/share/keyrings/raspbian.archive.public.key.gpg ||\
		die "apt-key add failed"
	apt-get -y update ||\
		die "apt-get update failed"
	apt-get -y dist-upgrade ||\
		die "apt-get dist-upgrade failed"

	info "Installing packages..."
	if [ "$opt_kernel" = "raspi" ]; then
		local bootloader=raspberrypi-bootloader
		apt-get -y purge raspberrypi-bootloader-nokernel ||\
			die "Failed to remove bootloader"
	elif [ "$opt_kernel" = "pilc" ]; then
		local bootloader=raspberrypi-bootloader-nokernel
		apt-get -y purge raspberrypi-bootloader ||\
			die "Failed to remove bootloader"
	else
		die "Invalid opt_kernel"
	fi
	apt-get -y install \
		"$bootloader" \
		aptitude \
		autoconf \
		automake \
		bc \
		build-essential \
		bwidget \
		clang \
		console-setup \
		cython \
		cython3 \
		dbus \
		debconf-utils \
		devscripts \
		git \
		gnu-fdisk \
		htop \
		i2c-tools \
		irqbalance \
		libboost-python-dev \
		libgl1-mesa-dev \
		libglu1-mesa-dev \
		libglib2.0-dev \
		libgtk2.0-dev \
		libncurses5-dev \
		libmodbus-dev \
		libreadline-gplv2-dev \
		libtk-img \
		libudev-dev \
		libusb-1.0-0-dev \
		libxmu-dev \
		locales \
		nano \
		openssh-server \
		openssh-blacklist \
		openssh-blacklist-extra \
		parted \
		pkg-config \
		pypy \
		pypy-dev \
		python \
		python-all-dev \
		python-cairo \
		python-dev \
		python-gtk2 \
		python-rpi.gpio \
		python-serial \
		python-setuptools \
		python-smbus \
		python-tk \
		python3 \
		python3-all-dev \
		python3-cairo \
		python3-dev \
		python3-rpi.gpio \
		python3-serial \
		python3-setuptools \
		python3-smbus \
		python3-tk \
		schedtool \
		screen \
		sudo \
		systemd \
		tcl-dev \
		tclx \
		tk-dev \
		tmux \
		vim ||\
		die "apt-get install failed"
	apt-get install --reinstall libc6-dev ||\
		die "Failed to reinstall"
cat <<EOF | debconf-set-selections
debconf	debconf/frontend	select	Dialog
locales	locales/default_environment_locale	select	en_US.UTF-8
EOF
	[ $? -eq 0 ] || die "Failed to configure debconf settings"
	dpkg-reconfigure -u locales ||\
		die "Failed to reconfigure locales"
	apt-get -y clean ||\
		die "apt-get clean failed"

	# Build RPi.GPIO
	info "Building RPi.GPIO $RPIGPIO_VERSION for PyPy..."
	(
		cd /tmp || die "Failed to cd /tmp"
		tar xf "RPi.GPIO-$RPIGPIO_VERSION.tar.gz" ||\
			die "Failed to unpack RPi.GPIO-$RPIGPIO_VERSION.tar.gz"
		cd "RPi.GPIO-$RPIGPIO_VERSION" ||\
			die "Failed to cd RPi.GPIO-$RPIGPIO_VERSION"
		pypy ./setup.py install ||\
			die "Failed to install RPi.GPIO-$RPIGPIO_VERSION"
	) || die
	rm -r /tmp/RPi.GPIO* ||\
		die "Failed to remove RPi.GPIO."

	# Build and install kernel
	if [ "$opt_kernel" = "pilc" ]; then
		info "Building PiLC kernel..."
		(
			cd "/tmp/kernel" ||\
				die "Failed to cd to /tmp/kernel"
			make oldconfig ||\
				die "Kernel oldconfig failed"
			make -j "$_NPROCESSORS_ONLN" ||\
				die "Kernel build failed"
			#TODO
		) || die
		die "TODO: PiLC kernel"
	fi

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

# Re-generate ssh keys, if requested.
if [ -e /etc/ssh/ssh_create_keys ]; then
	/bin/rm -f /etc/ssh/ssh_host_*_key*
	LC_ALL=C LANGUAGE=C LANG=C /usr/sbin/dpkg-reconfigure openssh-server
	/bin/rm /etc/ssh/sshd_not_to_be_run
	/bin/rm /etc/ssh/ssh_create_keys
	/etc/init.d/ssh start
fi

# Workaround firmware issue leaving i2c0 in an non-ALT0 state.
for i in 28 29; do
	/bin/echo \$i > /sys/class/gpio/export
	/bin/echo in > /sys/class/gpio/gpio\${i}/direction
done

# Add HAT eeprom device.
if ! [ -d "/sys/class/i2c-adapter/i2c-0/0-0050" ]; then
	/bin/echo "24c32 0x50" > /sys/class/i2c-adapter/i2c-0/new_device
fi

# Add /dev/ttyS0 link for convenience.
if ! [ -e /dev/ttyS0 ]; then
	/bin/ln -s /dev/ttyAMA0 /dev/ttyS0
fi

exit 0
EOF
	[ $? -eq 0 ] || die "Failed to create /etc/rc.local"
	chmod 755 /etc/rc.local || die "Failed to chmod /etc/rc.local"

	info "Creating /etc/modules-load.d/i2c.conf..."
	cat > /etc/modules-load.d/i2c.conf <<EOF
i2c-dev
i2c-bcm2708
at24
rtc-rv3029c2
EOF
	[ $? -eq 0 ] || die "Failed to create /etc/modules-load.d/i2c.conf"

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
	echo 'pi ALL=(ALL:ALL) ALL' > "/etc/sudoers.d/00-pi" ||\
		die "Failed to create /etc/sudoers.d/00-pi"

	info "Initializing home directory..."
	mkdir -p /home/pi/.vim || die "Failed to mkdir /home/pi/.vim"
	cat > /home/pi/.vim/vimrc <<EOF
set nocompatible
set autoindent
syntax enable
set backspace=indent,start
set number
EOF
	[ $? -eq 0 ] || die "Failed to create /home/pi/.vim/vimrc"
	cat > /home/pi/.tmux.conf <<EOF
# Default new panes and windows to be opened in the current panes path
bind-key c new-window -c "#{pane_current_path}"
bind-key % split-window -h -c "#{pane_current_path}"
bind-key "\"" split-window -c "#{pane_current_path}"
EOF
	[ $? -eq 0 ] || die "Failed to create /home/pi/.tmux.conf"

	info "Building awlsim..."
	(
		cd /tmp/awlsim/src ||\
			die "Failed to cd"
		if [ $opt_cython -eq 0 ]; then
			# Disable cython
			sed -i -e '/Package: cython/,/^$/ d' \
				debian/control ||\
				die "Failed to patch control file"
			sed -i -e 's/export AWLSIM_CYTHON=1/export AWLSIM_CYTHON=0/' \
				debian/rules ||\
				die "Failed to patch rules file"
		fi
		debuild -uc -us -b -d || die "debuild failed"
		info "Built awlsim files:"
		ls .. || die "Failed to list results"

		info "Installing awlsim..."
		# Core
		dpkg -i ../python-awlsim_*.deb ||\
			die "Failed to install python-awlsim"
		dpkg -i ../python3-awlsim_*.deb ||\
			die "Failed to install python3-awlsim"
		dpkg -i ../pypy-awlsim_*.deb ||\
			die "Failed to install pypy-awlsim"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython-awlsim_*.deb ||\
				die "Failed to install cython-awlsim"
			dpkg -i ../cython3-awlsim_*.deb ||\
				die "Failed to install cython3-awlsim"
		fi
		# hardware: dummy
		dpkg -i ../python-awlsimhw-dummy_*.deb ||\
			die "Failed to install python-awlsimhw-dummy"
		dpkg -i ../python3-awlsimhw-dummy_*.deb ||\
			die "Failed to install python3-awlsimhw-dummy"
		dpkg -i ../pypy-awlsimhw-dummy_*.deb ||\
			die "Failed to install pypy-awlsimhw-dummy"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython-awlsimhw-dummy_*.deb ||\
				die "Failed to install cython-awlsimhw-dummy"
			dpkg -i ../cython3-awlsimhw-dummy_*.deb ||\
				die "Failed to install cython3-awlsimhw-dummy"
		fi
		# hardware: linuxcnc
		dpkg -i ../python-awlsimhw-linuxcnc_*.deb ||\
			die "Failed to install python-awlsimhw-linuxcnc"
		dpkg -i ../python3-awlsimhw-linuxcnc_*.deb ||\
			die "Failed to install python3-awlsimhw-linuxcnc"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython-awlsimhw-linuxcnc_*.deb ||\
				die "Failed to install cython-awlsimhw-linuxcnc"
			dpkg -i ../cython3-awlsimhw-linuxcnc_*.deb ||\
				die "Failed to install cython3-awlsimhw-linuxcnc"
		fi
		# hardware: profibus
		dpkg -i ../python-awlsimhw-profibus_*.deb ||\
			die "Failed to install python-awlsimhw-profibus"
		dpkg -i ../python3-awlsimhw-profibus_*.deb ||\
			die "Failed to install python3-awlsimhw-profibus"
		dpkg -i ../pypy-awlsimhw-profibus_*.deb ||\
			die "Failed to install pypy-awlsimhw-profibus"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython-awlsimhw-profibus_*.deb ||\
				die "Failed to install cython-awlsimhw-profibus"
			dpkg -i ../cython3-awlsimhw-profibus_*.deb ||\
				die "Failed to install cython3-awlsimhw-profibus"
		fi
		# hardware: RPi GPIO
		dpkg -i ../python-awlsimhw-rpigpio_*.deb ||\
			die "Failed to install python-awlsimhw-rpigpio"
		dpkg -i ../python3-awlsimhw-rpigpio_*.deb ||\
			die "Failed to install python3-awlsimhw-rpigpio"
		dpkg -i ../pypy-awlsimhw-rpigpio_*.deb ||\
			die "Failed to install pypy-awlsimhw-rpigpio"
		if [ $opt_cython -ne 0 ]; then
			dpkg -i ../cython-awlsimhw-rpigpio_*.deb ||\
				die "Failed to install cython-awlsimhw-rpigpio"
			dpkg -i ../cython3-awlsimhw-rpigpio_*.deb ||\
				die "Failed to install cython3-awlsimhw-rpigpio"
		fi
		# PiLC libraries
		dpkg -i ../python-libpilc_*.deb ||\
			die "Failed to install python-libpilc"
		dpkg -i ../python3-libpilc_*.deb ||\
			die "Failed to install python3-libpilc"
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
		dpkg -i ../awlsim-linuxcnc-hal_*.deb ||\
			die "Failed to install awlsim-linuxcnc-hal"
		dpkg -i ../pilc-hat-conf_*.deb ||\
			die "Failed to install pilc-hat-conf"
		# GUI and misc
		mkdir -p /home/pi/awlsim-gui ||\
			die "mkdir /home/pi/awlsim-gui failed"
		cp ../python*-awlsim-gui_*.deb ../awlsim-gui_*.deb \
			/home/pi/awlsim-gui/ ||\
			die "Failed to copy awlsim-gui"
		cp examples/EXAMPLE.awlpro /home/pi/generic-example.awlpro ||\
			die "Failed to copy EXAMPLE.awlpro."
		cp examples/raspberrypi-gpio.awlpro /home/pi/raspberrypi-gpio-example.awlpro ||\
			die "Failed to copy raspberrypi-gpio.awlpro."
		cp examples/raspberrypi-profibus.awlpro /home/pi/raspberrypi-profibus-example.awlpro ||\
			die "Failed to copy raspberrypi-profibus.awlpro."

		#TODO run the testsuite

		#TODO install unit via package
		info "Installing awlsim service unit..."
		local awlsim_prefix=/usr
		local site="$awlsim_prefix/lib/python2.7/dist-packages"
		cat awlsim-server.service.in |\
		sed -e 's|@USER@|root|g' \
		    -e 's|@GROUP@|root|g' \
		    -e "s|@PREFIX@|$awlsim_prefix|g" \
		    -e 's|@PROJECT@|/etc/awlsim-server.awlpro|g' \
		    -e 's|@PYTHON@|/usr/bin/python2.7|g' \
		    -e "s|@PYTHON_SITE@|$site|g" >\
		    /etc/systemd/system/awlsim-server.service ||\
		    die "Failed to create awlsim-server.service"
		systemctl enable awlsim-server.service ||\
			die "Failed to enable awlsim-server-service"
	) || die
	info "Building pyprofibus..."
	(
		cd /tmp/awlsim/pyprofibus ||\
			die "Failed to cd"
		debuild -uc -us -b -d || die "debuild failed"
		info "Built pyprofibus files:"
		ls .. || die "Failed to list results"

		info "Installing pyprofibus..."
		dpkg -i ../python-pyprofibus_*.deb ||\
			die "Failed to install python-pyprofibus"
		dpkg -i ../python3-pyprofibus_*.deb ||\
			die "Failed to install python3-pyprofibus"
		dpkg -i ../pypy-pyprofibus_*.deb ||\
			die "Failed to install pypy-pyprofibus"
		dpkg -i ../profisniff_*.deb ||\
			die "Failed to install profisniff"
		dpkg -i ../gsdparser_*.deb ||\
			die "Failed to install gsdparser"
		dpkg -i ../pyprofibus-linuxcnc-hal_*.deb ||\
			die "Failed to install pyprofibus-linuxcnc-hal"
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

	info "Configuring network..."
	cat > /etc/network/interfaces.d/lo <<EOF
auto lo
iface lo inet loopback
EOF
	[ $? -eq 0 ] || die "Failed to create /etc/network/interfaces.d/lo"
	cat > /etc/network/interfaces.d/enx <<EOF
allow-hotplug /enx*=enx
iface enx inet dhcp
iface enx inet6 auto
EOF
	[ $? -eq 0 ] || die "Failed to create /etc/network/interfaces.d/enx"
	cat > /etc/network/interfaces.d/eth <<EOF
allow-hotplug /eth*=eth
iface eth inet dhcp
iface eth inet6 auto
EOF
	[ $? -eq 0 ] || die "Failed to create /etc/network/interfaces.d/eth"
	for i in $(seq 0 9); do
		cat > /etc/network/interfaces.d/eth$i <<EOF
allow-hotplug eth$i
iface eth$i inet dhcp
iface eth$i inet6 auto
EOF
		[ $? -eq 0 ] || die "Failed to create /etc/network/interfaces.d/eth$i"
	done

	info "Updating home directory permissions..."
	chown -R pi:pi /home/pi || die "Failed to change /home/pi permissions."

	# Remove rc.d policy file
	if [ -e /usr/sbin/policy-rc.d ]; then
		rm /usr/sbin/policy-rc.d ||\
			die "Failed to remove policy-rc.d"
	fi

	info "Stopping processes..."
	for i in dbus ssh atd irqbalance; do
		/etc/init.d/$i stop
	done
}

pilc_bootstrap_third_stage()
{
	info "Running third stage..."

	info "Umounting /dev/shm..."
	umount "$mp_shm" || die "Failed to umount /dev/shm"
	info "Umounting /sys..."
	umount "$mp_sys" || die "Failed to umount /sys"
	info "Umounting /proc/sys/fs/binfmt_misc..."
	umount "$mp_proc_binfmt_misc"
	info "Umounting /proc..."
	umount "$mp_proc" || die "Failed to umount /proc"

	info "Removing PiLC bootstrap script..."
	rm "$opt_target_dir/pilc-bootstrap.sh" ||\
		die "Failed to remove bootstrap script."

	info "Configuring boot..."
	cat > "$opt_target_dir/boot/cmdline.txt" <<EOF
dwc_otg.lpm_enable=0 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline isolcpus=2,3 rcu_nocbs=2,3 nohz_full=2,3 fsck.repair=yes net.ifnames=0 rootwait quiet
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
		info "Creating boot image..."
		mkfs.vfat -F 32 -i 7771B0BB -n boot -C "$bootimgfile" \
			$(expr \( 64 \* 1024 \) - \( 4 \* 1024 \) ) ||\
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
		mkfs.ext4 "$rootimgfile" $(expr \( 4000 - 64 \) \* 1024 ) ||\
			die "Failed to create root filesystem."
		mkdir "$mp_rootimgfile" ||\
			die "Failed to make root partition mount point."
		mount -o loop "$rootimgfile" "$mp_rootimgfile" ||\
			die "Failed to mount root partition."
		rsync -aHAX --inplace \
			--exclude='boot/*' \
			--exclude='proc/*' \
			--exclude='sys/*' \
			--exclude='dev/shm/*' \
			--exclude='tmp/*' \
			--exclude="$(basename "$opt_qemu")" \
			"$opt_target_dir/" "$mp_rootimgfile/" ||\
			die "Failed to copy root files."
		umount "$mp_rootimgfile" ||\
			die "Failed to umount root partition."
		rmdir "$mp_rootimgfile" ||\
			die "Failed to remove root partition mount point."

		info "Creating image '$imgfile'..."
		dd if=/dev/zero of="$imgfile" bs=1M count=4000 conv=sparse ||\
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
	echo " --arch|-a ARCH          Select the default arch."
	echo "                         Default: $default_arch"
	echo
	echo " --kernel|-k KERNEL      Kernel selection. Any of:"
	echo "                         raspi  -> raspberrypi-bootloader package (default)"
	echo "                         pilc   -> PiLC kernel"
	echo
	echo " --qemu-bin|-Q PATH      Select qemu-user-static binary."
	echo "                         Default: $default_qemu"
	echo
	echo " --img-suffix|-s SUFFIX  Image file suffix."
	echo "                         Default: $default_imgsuffix"
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
}

# canonicalize basedir
basedir="$(readlink -e "$basedir")"
[ -n "$basedir" ] || die "Failed to canonicalize base directory."

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
	default_arch="armhf"
	default_kernel="raspi"
	default_qemu="/usr/bin/qemu-arm-static"
	default_imgsuffix="-$(date '+%Y%m%d')"
	default_img=1
	default_zimg=1
	default_writedev=
	default_writeonly=0

	opt_target_dir=
	opt_branch="$default_branch"
	opt_cython=1
	opt_suite="$default_suite"
	opt_arch="$default_arch"
	opt_kernel="$default_kernel"
	opt_qemu="$default_qemu"
	opt_skip_debootstrap1=0
	opt_skip_debootstrap2=0
	opt_imgsuffix="$default_imgsuffix"
	opt_img="$default_img"
	opt_zimg="$default_zimg"
	opt_writedev="$default_writedev"
	opt_writeonly="$default_writeonly"

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
		--arch|-a)
			shift
			opt_arch="$1"
			[ -n "$opt_arch" ] || die "No arch given"
			;;
		--kernel|-k)
			shift
			opt_kernel="$1"
			[ "$opt_kernel" = "raspi" -o \
			  "$opt_kernel" = "pilc" ] || die "Invalid kernel"
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
		--img-suffix|-s)
			shift
			opt_imgsuffix="$1"
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
	export opt_arch
	export opt_kernel
	export opt_qemu
	export opt_skip_debootstrap1
	export opt_skip_debootstrap2
	export opt_imgsuffix
	export opt_zimg
	export opt_img
	export opt_writedev
	export opt_writeonly
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
