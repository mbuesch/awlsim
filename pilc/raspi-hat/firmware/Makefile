# Project name
NAME			:= pilc-raspi-hat

# Project source files
SRCS			:= conf.c \
			   eepemu_24cxx.c \
			   main.c \
			   i2c_slave.c \
			   pb_txen.c \
			   util.c

# Project fuse bits
# 8Mhz internal, WDTon, BOD 2.7
LFUSE			:= 0xE2
HFUSE			:= 0xCD
EFUSE			:= 0xFF

# CPU speed, in Hz
F_CPU			:= 8000000UL

# Architecture configuration
GCC_ARCH		:= attiny85
AVRDUDE_ARCH		:= t85
FUNC_STACK_LIMIT	:=

# Programmer selection.
# Values can be:  avrisp2, mysmartusb
PROGRAMMER		:= avrisp2

# Additional compiler flags
I2CS_EXPECTED_KHZ	:= 100
CFLAGS			:= -DI2CS_MAX_NR_SLAVES=2 \
			   -DI2CS_CLKSTRETCH_WORKAROUND \
			   -DI2CS_EXPECTED_KHZ=$(I2CS_EXPECTED_KHZ) \
			   -DEEPEMU_24CXX_ADDR=0x50 \
			   -DCONF_ADDR=0x2F
LDFLAGS			:=

# Additional "clean" and "distclean" target files
CLEAN_FILES		:= clkstretch_table.c
DISTCLEAN_FILES		:=


clkstretch_table.c: clkstretch_table.py
	$(QUIET_PYTHON3) $< $(I2CS_EXPECTED_KHZ) > $@

include avrmakelib.mk
