%.dtb: %.dts
	false

%.eep: %.txt %.dtb
	$(MAKE) -C ../raspi-hat-tools/eepromutils all
	../raspi-hat-tools/eepromutils/eepmake $< $@ $*.dtb
	$(MAKE) -C ../raspi-hat-tools/eepromutils clean

all: pilc_eeprom_settings.eep

clean:
	rm -f *.eep
