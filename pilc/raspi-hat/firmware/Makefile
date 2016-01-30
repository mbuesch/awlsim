# Project name
NAME			:= pilc-raspi-hat

# Project source files
SRCS			:= main.c \
			   util.c

# Project fuse bits
#TODO
LFUSE			:= 0xE2
HFUSE			:= 0xDD
EFUSE			:= 0x01

# CPU speed, in Hz
F_CPU			:= 8000000UL

# Architecture configuration
GCC_ARCH		:= attiny85
AVRDUDE_ARCH		:= m85
FUNC_STACK_LIMIT	:= 64

# Programmer selection.
# Values can be:  avrisp2, mysmartusb
PROGRAMMER		:= avrisp2

# Additional compiler flags
CFLAGS			:=
LDFLAGS			:=

# Additional "clean" and "distclean" target files
CLEAN_FILES		:=
DISTCLEAN_FILES		:=


include avrmakelib.mk
