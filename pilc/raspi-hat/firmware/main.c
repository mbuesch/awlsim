/*
 * PiLC HAT firmware
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

#include "main.h"
#include "util.h"
#include "i2c_slave.h"
#include "eepemu_24cxx.h"
#include "pb_txen.h"
#include "conf.h"
#include "dbg_slave.h"

#include <avr/wdt.h>


void early_init(void) __attribute__((naked, section(".init3"), used));
void early_init(void)
{
	MCUSR = 0;
	wdt_enable(WDTO_250MS);
}

int main(void) _mainfunc;
int main(void)
{
	i2cs_init();
	ee24cxx_init();
	pb_txen_init();
	conf_init();
	dbgslave_init();

	wdt_enable(WDTO_60MS);
	pb_txen_work();
}
