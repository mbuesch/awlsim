/*
 * PiLC HAT firmware
 * 24Cxx EEPROM emulation
 *
 * Copyright (c) 2016 Michael Buesch <m@bues.ch>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include "eepemu_24cxx.h"
#include "i2c_slave.h"

#include <string.h>

#include <avr/eeprom.h>


/* Default to: emulated page size = 32 bytes. */
#ifndef EE24CXX_PAGE_MASK
# define EE24CXX_PAGE_MASK	((uint16_t)(32 - 1))
#endif


enum ee24cxx_state {
	EE24CXX_IDLE,
	EE24CXX_WRADDRLO,
	EE24CXX_ADDRCOMPLETE,
};

struct ee24cxx_context {
	enum ee24cxx_state state;
	uint16_t word_addr;
	bool write_en;
};


static struct ee24cxx_context ee24cxx;

#ifdef EEPEMU_24CXX_CONTENT_IN_FLASH
# define EEPEMU_DEF_ATTR	const __flash
# define EEPEMU_DECL_ATTR	const __flash
# define EEPEMU_IMG_SIZE
#else
# define EEPEMU_DEF_ATTR	EEMEM
# define EEPEMU_DECL_ATTR
# define EEPEMU_IMG_SIZE	(E2END + 1)
#endif

#include "eepemu_24cxx_content.c"


#define EE24CXX_ADDR_MASK	(EEPEMU_24CXX_SIZE - 1)


static void ee24cxx_busy_wait(void)
{
#ifndef EEPEMU_24CXX_CONTENT_IN_FLASH
	eeprom_busy_wait();
#endif
}

static uint8_t ee24cxx_read_byte(uint8_t EEPEMU_DECL_ATTR *mem)
{
#ifdef EEPEMU_24CXX_CONTENT_IN_FLASH
	return *mem;
#else
	return eeprom_read_byte(mem);
#endif
}

static void ee24cxx_write_byte(uint8_t EEPEMU_DECL_ATTR *mem, uint8_t data)
{
#ifndef EEPEMU_24CXX_CONTENT_IN_FLASH
	eeprom_write_byte(mem, data);
#endif
}

void ee24cxx_set_we(bool write_enable)
{
	struct ee24cxx_context *ee = &ee24cxx;

#ifdef EEPEMU_24CXX_CONTENT_IN_FLASH
	write_enable = false;
#endif
	ee->write_en = write_enable;
}

bool ee24cxx_get_we(void)
{
	struct ee24cxx_context *ee = &ee24cxx;

	return ee->write_en;
}

static uint8_t ee24cxx_transmit(bool start)
{
	struct ee24cxx_context *ee = &ee24cxx;
	uint8_t ret = 0;

	switch (ee->state) {
	case EE24CXX_IDLE:
		/* current-address-read. */
		ret = ee->word_addr & 0xFF;
		break;
	case EE24CXX_ADDRCOMPLETE:
		/* data read. */
		ee24cxx_busy_wait();
		if (ee->word_addr < sizeof(eepemu_24cxx_content))
			ret = ee24cxx_read_byte(&eepemu_24cxx_content[ee->word_addr]);
		else
			ret = 0xFF;
		ee->word_addr = (ee->word_addr + 1) & EE24CXX_ADDR_MASK;
		break;
	case EE24CXX_WRADDRLO:
		/* error: address not complete. */
		break;
	}

	return ret;
}

static bool ee24cxx_receive(bool start, uint8_t data)
{
	struct ee24cxx_context *ee = &ee24cxx;
	bool ret = false;

	if (start)
		ee->state = EE24CXX_IDLE;

	switch (ee->state) {
	case EE24CXX_IDLE:
		/* address high byte write. */
		ee->word_addr = (ee->word_addr & 0x00FF) |
				((uint16_t)data << 8);
		ee->word_addr &= EE24CXX_ADDR_MASK;
		ee->state = EE24CXX_WRADDRLO;
		ret = true;
		break;
	case EE24CXX_WRADDRLO:
		/* address low byte write. */
		ee->word_addr = (ee->word_addr & 0xFF00) |
				((uint16_t)data);
		ee->word_addr &= EE24CXX_ADDR_MASK;
		ee->state = EE24CXX_ADDRCOMPLETE;
		if (ee->write_en)
			ret = true;
		break;
	case EE24CXX_ADDRCOMPLETE:
		/* data write. */
		if (ee->write_en) {
			ee24cxx_busy_wait();
			ee24cxx_write_byte(&eepemu_24cxx_content[ee->word_addr],
					   data);
		}
		ee->word_addr = (ee->word_addr & ~EE24CXX_PAGE_MASK) |
				((ee->word_addr + 1) & EE24CXX_PAGE_MASK);
		ret = true;
		break;
	}

	return ret;
}

static const struct i2c_slave_ops __flash ee24cxx_i2c_slave_ops = {
	.transmit	= ee24cxx_transmit,
	.receive	= ee24cxx_receive,
};

void ee24cxx_init(void)
{
#ifndef EEPEMU_24CXX_CONTENT_IN_FLASH
	build_assert(sizeof(eepemu_24cxx_content) < E2END);
#endif

	memset(&ee24cxx, 0, sizeof(ee24cxx));
	ee24cxx.state = EE24CXX_IDLE;

	i2cs_add_slave(EEPEMU_24CXX_ADDR, &ee24cxx_i2c_slave_ops);
}
