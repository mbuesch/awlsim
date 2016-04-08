%.eep: %.txt
	$(MAKE) -C ../raspi-hat-tools/eepromutils all
	../raspi-hat-tools/eepromutils/eepmake $< $@
	$(MAKE) -C ../raspi-hat-tools/eepromutils clean

all: pilc_eeprom_settings.eep

clean:
	rm *.eep
