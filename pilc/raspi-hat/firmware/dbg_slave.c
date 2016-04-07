/*
 * PiLC HAT firmware
 * I2C debugging slave
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

#include "dbg_slave.h"
#include "i2c_slave.h"
#include "util.h"


#define DBGSLAVE_MAX_DELAY	42

static uint8_t dbgslave_data;
static uint8_t dbgslave_tx_delay;
static uint8_t dbgslave_rx_delay;


static void dbgslave_delay(uint8_t delay)
{
	while (delay--)
		__asm__ __volatile__ ("nop\n");
}

static uint8_t dbgslave_transmit(bool start)
{
	dbgslave_delay(dbgslave_tx_delay);
	if (++dbgslave_tx_delay >= DBGSLAVE_MAX_DELAY)
		dbgslave_tx_delay = 0;

	return (uint8_t)(dbgslave_data | (start ? 0x02 : 0x00));
}

static bool dbgslave_receive(bool start, uint8_t data)
{
	dbgslave_delay(dbgslave_rx_delay);
	if (++dbgslave_rx_delay >= DBGSLAVE_MAX_DELAY)
		dbgslave_rx_delay = 0;

	dbgslave_data = (uint8_t)((data & ~0x03) | (start ? 0x01 : 0x00));

	return true;
}

static const struct i2c_slave_ops __flash dbgslave_i2c_slave_ops = {
	.transmit	= dbgslave_transmit,
	.receive	= dbgslave_receive,
};

void dbgslave_init(void)
{
	i2cs_add_slave(DBGSLAVE_ADDR, &dbgslave_i2c_slave_ops);
}
