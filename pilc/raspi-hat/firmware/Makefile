# Project name
NAME			:= pilc-raspi-hat

# Project source files
SRCS			:= conf.c \
			   dbg_slave.c \
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
CFLAGS			:= -DI2CS_MAX_NR_SLAVES=3 \
			   -DI2CS_CLKSTRETCH_WORKAROUND \
			   -DI2CS_EXPECTED_KHZ=$(I2CS_EXPECTED_KHZ) \
			   -DEEPEMU_24CXX_ADDR=0x50 \
			   -DEEPEMU_24CXX_CONTENT_IN_FLASH \
			   -DEEPEMU_24CXX_SIZE=0x8000 \
			   -DCONF_ADDR=0x2F \
			   -DDBGSLAVE_ADDR=0x77
LDFLAGS			:=

# Additional "clean" and "distclean" target files
CLEAN_FILES		:= eepemu_24cxx_content.c
DISTCLEAN_FILES		:=


../eeprom/pilc_eeprom_settings.eep: ../eeprom/pilc_eeprom_settings.txt
	CFLAGS= CPPFLAGS= $(MAKE) -C ../eeprom all

eepemu_24cxx_content.c: ../eeprom/pilc_eeprom_settings.eep
	@echo 'uint8_t EEPEMU_DEF_ATTR eepemu_24cxx_content[EEPEMU_IMG_SIZE] = {' > $@
	hexdump -v -e '/1 "0x%02X, "' $< >> $@
	@echo '};' >> $@


include avrmakelib.mk
