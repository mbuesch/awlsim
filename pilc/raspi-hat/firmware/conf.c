/*
 * PiLC HAT firmware
 * I2C configuration interface
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

#include "conf.h"
#include "i2c_slave.h"
#include "util.h"
#include "pb_txen.h"
#include "eepemu_24cxx.h"

#include <string.h>

#include <avr/io.h>


enum conf_items {
	CONF_NONE,
	CONF_XTALCAL,		/* Crystal calibration */
	CONF_EEMUWE,		/* EEPROM emulation write enable */
	CONF_PBTXENDBG,		/* TX-en debug mode */
	CONF_PBTXENTO,		/* TX-en timeout */
};

struct conf_context {
	enum conf_items item;
	uint8_t count;
	uint8_t buf[4];
};


static struct conf_context conf;


static void set_debug(uint8_t mode)
{
	enum pb_txen_debugmode m = (enum pb_txen_debugmode)mode;

	if (m == PBTXEN_DBG_OFF ||
	    m == PBTXEN_DBG_RETRIG ||
	    m == PBTXEN_DBG_NOTRIG)
		pb_txen_set_debug(m);
}

static uint8_t get_debug(void)
{
	return (uint8_t)pb_txen_get_debug();
}

static void set_osccal(uint8_t osccal)
{
	OSCCAL = osccal;
}

static uint8_t get_osccal(void)
{
	return OSCCAL;
}

static uint8_t handle_bool_read(bool (*getter)(void))
{
	struct conf_context *pc = &conf;
	uint8_t ret;

	ret = (uint8_t)getter();
	pc->item = CONF_NONE;

	return ret;
}

static uint8_t handle_u8_read(uint8_t (*getter)(void))
{
	struct conf_context *pc = &conf;
	uint8_t ret;

	ret = getter();
	pc->item = CONF_NONE;

	return ret;
}

static uint8_t handle_u16_read(uint16_t (*getter)(void))
{
	struct conf_context *pc = &conf;
	uint16_t value;
	uint8_t ret;

	build_assert(ARRAY_SIZE(pc->buf) >= 2);

	if (pc->count == 0) {
		value = getter();
		pc->buf[0] = (uint8_t)value;
		pc->buf[1] = (uint8_t)(value >> 8);
	}
	ret = pc->buf[pc->count++];
	if (pc->count >= ARRAY_SIZE(pc->buf))
		pc->item = CONF_NONE;

	return ret;
}

static uint8_t conf_transmit(bool start)
{
	struct conf_context *pc = &conf;
	uint8_t ret = 0;

	if (start)
		pc->count = 0;

	switch (pc->item) {
	case CONF_NONE:
		/* error */
		break;
	case CONF_XTALCAL:
		ret = handle_u8_read(get_osccal);
		break;
	case CONF_EEMUWE:
		ret = handle_bool_read(ee24cxx_get_we);
		break;
	case CONF_PBTXENDBG:
		ret = handle_u8_read(get_debug);
		break;
	case CONF_PBTXENTO:
		ret = handle_u16_read(pb_txen_get_timeout);
		break;
	}

	return ret;
}

static void handle_safe_bool_write(uint8_t data, void (*handler)(bool value))
{
	struct conf_context *pc = &conf;
	uint8_t a, b;

	build_assert(ARRAY_SIZE(pc->buf) >= 2);

	pc->buf[pc->count++] = data;
	if (pc->count >= 2) {
		a = pc->buf[0];
		b = (uint8_t)~(pc->buf[1]);
		if (a == b && (a == 0 || a == 1))
			handler(!!a);
		pc->item = CONF_NONE;
	}
}

static void handle_safe_u8_write(uint8_t data, void (*handler)(uint8_t value))
{
	struct conf_context *pc = &conf;
	uint8_t a, b;

	build_assert(ARRAY_SIZE(pc->buf) >= 2);

	pc->buf[pc->count++] = data;
	if (pc->count >= 2) {
		a = pc->buf[0];
		b = (uint8_t)~(pc->buf[1]);
		if (a == b)
			handler(a);
		pc->item = CONF_NONE;
	}
}

static void handle_safe_u16_write(uint8_t data, void (*handler)(uint16_t value))
{
	struct conf_context *pc = &conf;
	uint16_t a, b;

	build_assert(ARRAY_SIZE(pc->buf) >= 4);

	pc->buf[pc->count++] = data;
	if (pc->count >= 4) {
		a = (uint16_t)pc->buf[0];
		a |= (uint16_t)pc->buf[1] << 8;
		b = (uint16_t)pc->buf[2];
		b |= (uint16_t)pc->buf[3] << 8;
		b = ~b;
		if (a == b)
			handler(a);
		pc->item = CONF_NONE;
	}
}

static bool conf_receive(bool start, uint8_t data)
{
	struct conf_context *pc = &conf;

	if (start) {
		pc->item = CONF_NONE;
		pc->count = 0;
	}

	switch (pc->item) {
	case CONF_NONE:
		pc->item = (enum conf_items)data;
		pc->count = 0;
		break;
	case CONF_XTALCAL:
		handle_safe_u8_write(data, set_osccal);
		break;
	case CONF_EEMUWE:
		handle_safe_bool_write(data, ee24cxx_set_we);
		break;
	case CONF_PBTXENDBG:
		handle_safe_u8_write(data, set_debug);
		break;
	case CONF_PBTXENTO:
		handle_safe_u16_write(data, pb_txen_set_timeout);
		break;
	}

	return true;
}

static const struct i2c_slave_ops __flash conf_i2c_slave_ops = {
	.transmit	= conf_transmit,
	.receive	= conf_receive,
};

void conf_init(void)
{
	memset(&conf, 0, sizeof(conf));
	conf.item = CONF_NONE;

	i2cs_add_slave(CONF_ADDR, &conf_i2c_slave_ops);
}
