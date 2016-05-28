/*
 * PiLC HAT firmware
 * PROFIBUS-DP PHY - TxEnable handler
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

#include "pb_txen.h"

#include <string.h>

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>


/* Tx pin definitions (input) */
#define PB_TXPORT	PORTB
#define PB_TXPIN	PINB
#define PB_TXDDR	DDRB
#define PB_TXBIT	PB3
#define PB_TXPOL	-1

/* Tx-enable pin definitions (output) */
#define PB_TXENPORT	PORTB
#define PB_TXENDDR	DDRB
#define PB_TXENBIT	PB4
#define PB_TXENPOL	1

/* Run time compensation subtracted from timeout value. */
#define PBTXEN_RTCOMP_US	6


struct pb_txen_state {
	bool txen;			/* Current TxEn state. */
	enum pb_txen_debugmode debug;	/* Debug mode. */
	uint16_t timeout_us;		/* TxEn timeout in microseconds. */
};

static struct pb_txen_state pb_txen;


static inline bool pb_tx_get(void)
{
	bool tx_state;

	tx_state = !!(PB_TXPIN & (1 << PB_TXBIT));
	if (PB_TXPOL < 0)
		tx_state = !tx_state;

	return tx_state;
}

static inline void pb_txen_set(bool enable)
{
	if (enable) {
		/* Set to high. */
		PB_TXENDDR |= (1 << PB_TXENBIT);
		if (PB_TXENPOL < 0)
			PB_TXENPORT &= (uint8_t)~(1 << PB_TXENBIT);
		else
			PB_TXENPORT |= (1 << PB_TXENBIT);
	} else {
		/* Set to floating. */
		PB_TXENDDR &= (uint8_t)~(1 << PB_TXENBIT);
		PB_TXENPORT &= (uint8_t)~(1 << PB_TXENBIT);
	}
}

static inline void pb_txen_timer_start(void)
{
	TCNT1 = 0;
	TIFR = (1 << OCF1A);
	TIMSK |= (1 << OCIE1A);
}

static inline void pb_txen_timer_stop(void)
{
	TIMSK &= (uint8_t)~(1 << OCIE1A);
}

ISR(TIMER1_COMPA_vect)
{
	pb_txen_set(false);
	pb_txen_timer_stop();
	pb_txen.txen = false;
	memory_barrier();
}

static void pb_txen_timer_init(void)
{
	pb_txen_timer_stop();

	PLLCSR = 0;
	GTCCR &= (uint8_t)~((1 << PWM1B) | (1 << COM1B1) | (1 << COM1B0));

	TCNT1 = 0;
	OCR1A = 0;
	OCR1B = 0;
	OCR1C = 0;

	TIFR = (1 << OCF1A);
	TIMSK |= (1 << OCIE1A);
}

void pb_txen_set_timeout(uint16_t microseconds)
{
	uint32_t mul, div, ocr;
	uint8_t ps_idx, ps;

	static const uint16_t clkdivs[] = {
		1, 2, 4, 8, 16, 32, 64, 128, 256,
		512, 1024, 2048, 4096, 8192, 16384,
	};
	static const uint8_t ps_tab[] = {
		((0 << CS13) | (0 << CS12) | (0 << CS11) | (1 << CS10)),
		((0 << CS13) | (0 << CS12) | (1 << CS11) | (0 << CS10)),
		((0 << CS13) | (0 << CS12) | (1 << CS11) | (1 << CS10)),
		((0 << CS13) | (1 << CS12) | (0 << CS11) | (0 << CS10)),
		((0 << CS13) | (1 << CS12) | (0 << CS11) | (1 << CS10)),
		((0 << CS13) | (1 << CS12) | (1 << CS11) | (0 << CS10)),
		((0 << CS13) | (1 << CS12) | (1 << CS11) | (1 << CS10)),
		((1 << CS13) | (0 << CS12) | (0 << CS11) | (0 << CS10)),
		((1 << CS13) | (0 << CS12) | (0 << CS11) | (1 << CS10)),
		((1 << CS13) | (0 << CS12) | (1 << CS11) | (0 << CS10)),
		((1 << CS13) | (0 << CS12) | (1 << CS11) | (1 << CS10)),
		((1 << CS13) | (1 << CS12) | (0 << CS11) | (0 << CS10)),
		((1 << CS13) | (1 << CS12) | (0 << CS11) | (1 << CS10)),
		((1 << CS13) | (1 << CS12) | (1 << CS11) | (0 << CS10)),
		((1 << CS13) | (1 << CS12) | (1 << CS11) | (1 << CS10)),
	};

	build_assert(ARRAY_SIZE(clkdivs) == ARRAY_SIZE(ps_tab));

	pb_txen.timeout_us = microseconds;
	if (microseconds > PBTXEN_RTCOMP_US)
		microseconds -= PBTXEN_RTCOMP_US;
	else
		microseconds = 0;

	mul = F_CPU;
	div = 1000000UL;
	while ((mul % 10 == 0) && (div % 10 == 0)) {
		mul /= 10;
		div /= 10;
	}

	for (ps_idx = 0; ps_idx < ARRAY_SIZE(clkdivs); ps_idx++) {
		ocr = udiv_round_up(mul * (uint32_t)microseconds,
				    div * (uint32_t)clkdivs[ps_idx]);
		ps = ps_tab[ps_idx];
		if (ocr <= 0xFF)
			break;
	}

	pb_txen_set(false);
	pb_txen_timer_stop();
	pb_txen.txen = false;
	OCR1A = (uint8_t)ocr;
	TCCR1 = (0 << CTC1) | (0 << PWM1A) |
		(0 << COM1A1) | (0 << COM1A0) |
		ps;

	memory_barrier();
}

uint16_t pb_txen_get_timeout(void)
{
	return pb_txen.timeout_us;
}

void pb_txen_set_debug(enum pb_txen_debugmode mode)
{
	pb_txen.debug = mode;
}

enum pb_txen_debugmode pb_txen_get_debug(void)
{
	return pb_txen.debug;
}

void pb_txen_init(void)
{
	memset(&pb_txen, 0, sizeof(pb_txen));

	/* Initialize input */
	PB_TXPORT &= (uint8_t)~(1 << PB_TXBIT);
	PB_TXDDR &= (uint8_t)~(1 << PB_TXBIT);

	/* Initialize output */
	pb_txen_set(false);

	/* Wait for pin capacities */
	_delay_ms(20);

	pb_txen_timer_init();
	pb_txen_set_timeout(573);
}

static inline void pb_txen_trigger(void)
{
	pb_txen_set(true);
	pb_txen_timer_start();
	pb_txen.txen = true;
}

static void pb_txen_run_debug_mode(void)
{
	while (1) {
		wdt_reset();
		memory_barrier();

		switch (pb_txen.debug) {
		case PBTXEN_DBG_OFF:
			return;
		case PBTXEN_DBG_RETRIG:
			if (!pb_txen.txen)
				pb_txen_trigger();
			break;
		case PBTXEN_DBG_NOTRIG:
			break;
		}
	}
}

void pb_txen_work(void)
{
	irq_enable();
	while (1) {
		wdt_reset();

		if (unlikely(pb_txen.debug != PBTXEN_DBG_OFF))
			pb_txen_run_debug_mode();

		memory_barrier();
		if (!pb_txen.txen && pb_tx_get()) {
			/* We are transmitting. Set TxEn. */
			pb_txen_trigger();
		}
	}
}
