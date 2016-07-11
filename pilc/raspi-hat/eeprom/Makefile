EEPROMUTILS_DIR	:= ../../../submodules/raspi-hat-tools/eepromutils
EEPMAKE		:= $(EEPROMUTILS_DIR)/eepmake

%.dtb: %.dts
	false

%.eep: %.txt %.dtb
	$(MAKE) -C $(EEPROMUTILS_DIR) all
	$(EEPMAKE) $< $@ $*.dtb
	$(MAKE) -C $(EEPROMUTILS_DIR) clean

all: pilc_eeprom_settings.eep

clean:
	rm -f *.eep
