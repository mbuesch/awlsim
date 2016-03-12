######################################################
# AVR make library                                   #
# Copyright (c) 2015-2016 Michael Buesch <m@bues.ch> #
# Version 1.2                                        #
######################################################

ifeq ($(NAME),)
$(error NAME not defined)
endif
ifeq ($(SRCS),)
$(error SRCS not defined)
endif
ifeq ($(F_CPU),)
$(error F_CPU not defined)
endif
ifeq ($(GCC_ARCH),)
$(error GCC_ARCH not defined)
endif
ifeq ($(AVRDUDE_ARCH),)
$(error AVRDUDE_ARCH not defined)
endif

BINEXT			:=
NODEPS			:=

# The toolchain definitions
CC			= avr-gcc$(BINEXT)
OBJCOPY			= avr-objcopy$(BINEXT)
OBJDUMP			= avr-objdump$(BINEXT)
SIZE			= avr-size$(BINEXT)
MKDIR			= mkdir$(BINEXT)
MV			= mv$(BINEXT)
RM			= rm$(BINEXT)
CP			= cp$(BINEXT)
ECHO			= echo$(BINEXT)
GREP			= grep$(BINEXT)
TRUE			= true$(BINEXT)
TEST			= test$(BINEXT)
AVRDUDE			= avrdude$(BINEXT)
MYSMARTUSB		= mysmartusb.py
DOXYGEN			= doxygen$(BINEXT)
PYTHON3			= python3$(BINEXT)

V			:= @		# Verbose build:  make V=1
O			:= s		# Optimize flag
Q			:= $(V:1=)
QUIET_CC		= $(Q:@=@$(ECHO) '     CC       '$@;)$(CC)
QUIET_DEPEND		= $(Q:@=@$(ECHO) '     DEPEND   '$@;)$(CC)
QUIET_OBJCOPY		= $(Q:@=@$(ECHO) '     OBJCOPY  '$@;)$(OBJCOPY)
QUIET_SIZE		= $(Q:@=@$(ECHO) '     SIZE     '$@;)$(SIZE)
QUIET_PYTHON3		= $(Q:@=@$(ECHO) '     PY3-GEN  '$@;)$(PYTHON3)

FUNC_STACK_LIMIT	?= 128

WARN_CFLAGS		:= -Wall -Wextra -Wno-unused-parameter -Wswitch-enum \
			   -Wsuggest-attribute=noreturn \
			   -Wundef -Wpointer-arith -Winline \
			   $(if $(FUNC_STACK_LIMIT),-Wstack-usage=$(FUNC_STACK_LIMIT)) \
			   -Wcast-qual -Wlogical-op -Wshadow \
			   -Wconversion

CFLAGS			+= -mmcu=$(GCC_ARCH) -std=gnu11 -g -O$(O) $(WARN_CFLAGS) \
			  "-Dinline=inline __attribute__((__always_inline__))" \
			  -fshort-enums -DF_CPU=$(F_CPU) \
			  -mcall-prologues -mrelax -mstrict-X \
			  -flto

BIN			:= $(NAME).bin
HEX			:= $(NAME).hex
EEP			:= $(NAME).eep.hex

.SUFFIXES:
.DEFAULT_GOAL := all

# Programmer parameters
AVRDUDE_SPEED		?= 1
AVRDUDE_SLOW_SPEED	?= 200

ifeq ($(PROGRAMMER),mysmartusb)
AVRDUDE_PROGRAMMER	:= avr910
PROGPORT		:= /dev/ttyUSB0
endif
ifeq ($(PROGRAMMER),avrisp2)
AVRDUDE_PROGRAMMER	:= avrisp2
PROGPORT		:= usb
endif

ifeq ($(AVRDUDE_PROGRAMMER),)
$(error Invalid PROGRAMMER specified)
endif

PROGRAMMER_CMD_PWRCYCLE := \
	$(if $(filter mysmartusb,$(PROGRAMMER)), \
		$(MYSMARTUSB) -p0 $(PROGPORT) && \
		sleep 1 && \
		$(MYSMARTUSB) -p1 $(PROGPORT) \
	)

PROGRAMMER_CMD_PROG_ENTER := \
	$(if $(filter mysmartusb,$(PROGRAMMER)), \
		$(MYSMARTUSB) -mp $(PROGPORT) \
	)

PROGRAMMER_CMD_PROG_LEAVE := \
	$(if $(filter mysmartusb,$(PROGRAMMER)), \
		$(MYSMARTUSB) -md $(PROGPORT) \
	)

DEPS = $(sort $(patsubst %.c,dep/%.d,$(1)))
OBJS = $(sort $(patsubst %.c,obj/%.o,$(1)))

# Generate dependencies
$(call DEPS,$(SRCS)): dep/%.d: %.c 
	@$(MKDIR) -p $(dir $@)
	@$(MKDIR) -p obj
	$(QUIET_DEPEND) -o $@.tmp -MM -MG -MT "$@ $(patsubst dep/%.d,obj/%.o,$@)" $(CFLAGS) $<
	@$(MV) -f $@.tmp $@

ifeq ($(NODEPS),)
-include $(call DEPS,$(SRCS))
endif

# Generate object files
$(call OBJS,$(SRCS)): obj/%.o: %.c
	@$(MKDIR) -p $(dir $@)
	$(QUIET_CC) -o $@ -c $(CFLAGS) $<

all: $(HEX)

%.s: %.c
	$(QUIET_CC) $(CFLAGS) -fno-lto -S $*.c

$(BIN): $(call OBJS,$(SRCS))
	$(QUIET_CC) $(CFLAGS) -o $(BIN) -fwhole-program $(call OBJS,$(SRCS)) $(LDFLAGS)

$(HEX): $(BIN)
	$(QUIET_OBJCOPY) -R.eeprom -O ihex $(BIN) $(HEX)
	@$(if $(filter .exe,$(BINEXT)),$(TRUE), \
	$(OBJDUMP) -h $(BIN) | $(GREP) -qe .eeprom && \
	 $(OBJCOPY) -j.eeprom --set-section-flags=.eeprom="alloc,load" \
	 --change-section-lma .eeprom=0 -O ihex $(BIN) $(EEP) \
	 || $(TRUE))
	@$(ECHO)
	$(QUIET_SIZE) --format=SysV $(BIN)

define _avrdude_interactive
  $(AVRDUDE) -B $(AVRDUDE_SPEED) -p $(AVRDUDE_ARCH) \
    -c $(AVRDUDE_PROGRAMMER) -P $(PROGPORT) -t
endef

define _avrdude_reset
  $(AVRDUDE) -B $(AVRDUDE_SLOW_SPEED) -p $(AVRDUDE_ARCH) \
    -c $(AVRDUDE_PROGRAMMER) -P $(PROGPORT) \
    -U signature:r:/dev/null:i -q -q
endef

define _avrdude_write_flash
  $(AVRDUDE) -B $(AVRDUDE_SPEED) -p $(AVRDUDE_ARCH) \
    -c $(AVRDUDE_PROGRAMMER) -P $(PROGPORT) \
    -U flash:w:$(HEX)
endef

define _avrdude_write_eeprom
  $(TEST) -r $(EEP) && ( \
    $(AVRDUDE) -B $(AVRDUDE_SPEED) -p $(AVRDUDE_ARCH) \
    -c $(AVRDUDE_PROGRAMMER) -P $(PROGPORT) \
    -U eeprom:w:$(EEP) \
  ) || $(TRUE)
endef

define _avrdude_write_fuse
  $(AVRDUDE) -B $(AVRDUDE_SLOW_SPEED) -p $(AVRDUDE_ARCH) \
    -c $(AVRDUDE_PROGRAMMER) -P $(PROGPORT) -q -q \
    -U lfuse:w:$(LFUSE):m -U hfuse:w:$(HFUSE):m $(if $(EFUSE),-U efuse:w:$(EFUSE):m)
endef

write_flash: all
	$(call PROGRAMMER_CMD_PROG_ENTER)
	$(call _avrdude_write_flash)
	$(call PROGRAMMER_CMD_PWRCYCLE)
	$(call PROGRAMMER_CMD_PROG_LEAVE)

writeflash: write_flash

write_eeprom: all
	$(call PROGRAMMER_CMD_PROG_ENTER)
	$(call _avrdude_write_eeprom)
	$(call PROGRAMMER_CMD_PWRCYCLE)
	$(call PROGRAMMER_CMD_PROG_LEAVE)

writeeeprom: write_eeprom

write_mem: all
	$(call PROGRAMMER_CMD_PROG_ENTER)
	$(call _avrdude_write_flash)
	$(call _avrdude_write_eeprom)
	$(call PROGRAMMER_CMD_PWRCYCLE)
	$(call PROGRAMMER_CMD_PROG_LEAVE)

writemem: write_mem
install: write_mem

write_fuse:
	$(call PROGRAMMER_CMD_PROG_ENTER)
	$(call _avrdude_write_fuse)
	$(call PROGRAMMER_CMD_PWRCYCLE)
	$(call PROGRAMMER_CMD_PROG_LEAVE)

writefuse: write_fuse

reset:
	$(call PROGRAMMER_CMD_PROG_ENTER)
	$(call _avrdude_reset)
	$(call PROGRAMMER_CMD_PWRCYCLE)

avrdude:
	$(call PROGRAMMER_CMD_PROG_ENTER)
	$(call _avrdude_interactive)
	$(call PROGRAMMER_CMD_PWRCYCLE)
	$(call PROGRAMMER_CMD_PROG_LEAVE)

doxygen:
	$(DOXYGEN) Doxyfile

clean:
	-$(RM) -rf obj dep $(BIN) $(CLEAN_FILES)

distclean: clean
	-$(RM) -f $(HEX) $(EEP) $(DISTCLEAN_FILES)
	-$(RM) -f $(if $(filter .exe,$(BINEXT)),$(patsubst %.c,%.s,$(SRCS)),*.s)
