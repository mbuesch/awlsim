/*
 * USI I2C bus slave
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

#include "i2c_slave.h"
#include "util.h"

#include <string.h>

#include <avr/io.h>
#include <avr/interrupt.h>


#define SDA_PORT		PORTB
#define SDA_PIN			PINB
#define SDA_DDR			DDRB
#define SDA_BIT			PB0

#define SCL_PORT		PORTB
#define SCL_PIN			PINB
#define SCL_DDR			DDRB
#define SCL_BIT			PB2


#ifndef I2CS_MAX_NR_SLAVES
# error "I2CS_MAX_NR_SLAVES is not defined"
#endif


enum i2cs_state {
	I2CS_STATE_ADDR,
	I2CS_STATE_SND,
	I2CS_STATE_REQ_DATA,
	I2CS_STATE_RCV_DATA,
	I2CS_STATE_REQ_REPLY,
	I2CS_STATE_CHK_REPLY,
};

struct i2cs_context {
	enum i2cs_state state;
	const struct i2c_slave __flash *slaves[I2CS_MAX_NR_SLAVES];
	const struct i2c_slave __flash *active_slave;
};

static struct i2cs_context i2cs;


#ifdef I2CS_CLKSTRETCH_WORKAROUND

/* Raspberry Pi I2C clock stretching bug workaround. */

#ifndef I2CS_EXPECTED_KHZ
# error "I2CS_EXPECTED_KHZ is not defined"
#endif

#include "clkstretch_table.c"

static void clkstretch_timer_init(void)
{
	TCCR0B = 0;

	TCNT0 = 0;
	OCR0A = 0;
	OCR0B = 0;

	TIMSK &= (uint8_t)~((1 << OCIE0A) | (1 << OCIE0B) | (1 << TOIE0));
	TIFR = (1 << OCF0A) | (1 << OCF0B) | (1 << TOV0);

	/* Normal mode, prescaler 8. */
	build_assert(F_CPU == 8000000UL);
	build_assert(I2CS_EXPECTED_KHZ == 100);
	GTCCR &= (uint8_t)~(1 << PSR0);
	GTCCR &= (uint8_t)~(1 << TSM);
	TCCR0A = (0 << COM0A1) | (0 << COM0A0) |
		 (0 << COM0B1) | (0 << COM0B0) |
		 (0 << WGM01) | (0 << WGM00);
	TCCR0B = (0 << FOC0A) | (0 << FOC0B) |
		 (0 << WGM02) |
		 (0 << CS02) | (1 << CS01) | (0 << CS00);
}

/* Prepare the clock stretching workaround timer. */
#define clkstretch_timer_prepare()			\
	__asm__ __volatile__(				\
"	push r18				\n"	\
"	ldi	r18, 1				\n"	\
"	out	%[_TCNT0], r18			\n"	\
"	pop r18					\n"	\
	: /* outputs */					\
	: /* inputs */					\
		[_TCNT0] "I" (_SFR_IO_ADDR(TCNT0))	\
	: /* clobbers */				\
		"memory"				\
	)

static inline void clkstretch_timer_wait(void)
{
	uint8_t timer_cnt;
	enum clkstretch_release_hint release_hint;

	build_assert(I2CS_EXPECTED_KHZ == 100);

	/* Check whether we are well into the SCL-low range
	 * before we release SCL.
	 * If we are in an SCL-high range or anywhere near
	 * SCL being high, we delay. */
	while (1) {
		memory_barrier();
		timer_cnt = TCNT0;
		release_hint = clkstretch_release_hint_table[timer_cnt];
		if (release_hint == CLKSTRETCH_RELEASE_SAFE)
			break;
	}
}

#else /* I2CS_CLKSTRETCH_WORKAROUND */

static void clkstretch_timer_init(void)
{
}

#define clkstretch_timer_prepare()	do { } while (0)

static inline void clkstretch_timer_wait(void)
{
}

#endif /* I2CS_CLKSTRETCH_WORKAROUND */

static const struct i2c_slave __flash * find_slave(uint8_t addr)
{
	const struct i2c_slave __flash *slave;
	uint8_t i;

	for (i = 0; i < ARRAY_SIZE(i2cs.slaves); i++) {
		slave = i2cs.slaves[i];
		if (slave && slave->addr == addr)
			return slave;
	}

	return NULL;
}

static inline void usi_set_control(bool enable_overflow_irq,
				   bool hold_scl_low)
{
	USICR = (uint8_t)((1 << USISIE) |
			  ((enable_overflow_irq ? 1 : 0) << USIOIE) |
			  (1 << USIWM1) |
			  ((hold_scl_low ? 1 : 0) << USIWM0) |
			  (1 << USICS1) |
			  (0 << USICS0) |
			  (0 << USICLK) |
			  (0 << USITC));
}

static inline void usi_set_counter(uint8_t nr_bits, bool clear_startcond)
{
	USISR = (uint8_t)(((clear_startcond ? 1 : 0) << USISIF) |
			  (1 << USIOIF) |
			  (1 << USIPF) |
			  ((16 - (nr_bits * 2)) << USICNT0));
}

ISR(USI_START_vect)
{
	memory_barrier();

	SDA_DDR &= (uint8_t)~(1 << SDA_BIT);

	/* Wait for SCL low (or stop condition). */
	while ((SCL_PIN & (1 << SCL_BIT)) &&
	       !((SDA_PIN & (1 << SDA_BIT)))) {
		/* Wait.
		 * We depend on the WDT to restart the MCU, if this loop never
		 * terminates due to external issues.
		 */
	}

	/* Check whether we do not have a stop condition. */
	if (!(SDA_PIN & (1 << SDA_BIT))) {
		/* Enable counter overflow interrupt. */
		usi_set_control(true, true);
	}
	usi_set_counter(8, true);

	i2cs.state = I2CS_STATE_ADDR;
	i2cs.active_slave = NULL;

	memory_barrier();
}

static void i2cs_set_wait_startcond(void)
{
	clkstretch_timer_wait();

	usi_set_control(false, false);
	usi_set_counter(0, false);
	i2cs.active_slave = NULL;
}

static void i2cs_set_send_ack(void)
{
	clkstretch_timer_wait();

	USIDR = 0;
	SDA_DDR |= (1 << SDA_BIT);
	usi_set_counter(1, false);
}

static void i2cs_set_read_ack(void)
{
	clkstretch_timer_wait();

	USIDR = 0;
	SDA_DDR &= (uint8_t)~(1 << SDA_BIT);
	usi_set_counter(1, false);
}

static void i2cs_set_send_data(void)
{
	clkstretch_timer_wait();

	SDA_DDR |= (1 << SDA_BIT);
	usi_set_counter(8, false);
}

static void i2cs_set_read_data(void)
{
	clkstretch_timer_wait();

	SDA_DDR &= (uint8_t)~(1 << SDA_BIT);
	usi_set_counter(8, false);
}

static void usi_handle_counter_overflow(void)
{
	const struct i2c_slave __flash *slave;
	uint8_t data, slave_addr;
	int16_t res;

	if (USISR & (1 << USIPF)) {
		/* Stop condition. */
		i2cs_set_wait_startcond();
		return;
	}
again:
	switch (i2cs.state) {
	case I2CS_STATE_ADDR:
		data = USIDR;
		slave_addr = data >> 1;
		//TODO also check for 0 addr?
		slave = find_slave(slave_addr);
		if (slave) {
			i2cs.active_slave = slave;
			if (data & 1) {
				slave->start_cond(true);
				i2cs.state = I2CS_STATE_SND;
			} else {
				slave->start_cond(false);
				i2cs.state = I2CS_STATE_REQ_DATA;
			}
			i2cs_set_send_ack();
		} else {
			i2cs_set_wait_startcond();
		}
		break;
	case I2CS_STATE_SND:
		slave = i2cs.active_slave;
//		res = slave->next_send_byte();
res = 0x55;
		if (res >= 0) {
			data = (uint8_t)res;
			USIDR = data;
			i2cs.state = I2CS_STATE_REQ_REPLY;
			i2cs_set_send_data();
		} else {
			i2cs_set_wait_startcond();
		}
		break;
	case I2CS_STATE_REQ_REPLY:
		i2cs.state = I2CS_STATE_CHK_REPLY;
		i2cs_set_read_ack();
		break;
	case I2CS_STATE_CHK_REPLY:
		data = USIDR;
		if (data) {
			/* NACK */
			i2cs_set_wait_startcond();
		} else {
			i2cs.state = I2CS_STATE_SND;
			goto again;
		}
		break;
	case I2CS_STATE_REQ_DATA:
		i2cs.state = I2CS_STATE_RCV_DATA;
		i2cs_set_read_data();
		break;
	case I2CS_STATE_RCV_DATA:
		slave = i2cs.active_slave;

		data = USIDR;
//		slave->receive_byte(data);

		i2cs.state = I2CS_STATE_REQ_DATA;
		i2cs_set_send_ack();
		break;
	}
}

ISR(USI_OVF_vect, ISR_NAKED)
{
	clkstretch_timer_prepare();

	__asm__ __volatile__(
"	push r18		\n"
"	in r18, %[_SREG]	\n"
"	push r18		\n"
	: /* outputs */
	: /* inputs */
		[_SREG] "I" (_SFR_IO_ADDR(SREG))
	: /* clobbers */
		"memory"
	);

	__asm__ __volatile__(
"	push r0			\n"
"	push r1			\n"
"	push r19		\n"
"	push r20		\n"
"	push r21		\n"
"	push r22		\n"
"	push r23		\n"
"	push r24		\n"
"	push r25		\n"
"	push r26		\n"
"	push r27		\n"
"	push r30		\n"
"	push r31		\n"
"	clr r1			\n"
	: /* outputs */
	: /* inputs */
	: /* clobbers */
		"memory"
	);

	memory_barrier();
	usi_handle_counter_overflow();
	memory_barrier();

	__asm__ __volatile__(
"	pop r31			\n"
"	pop r30			\n"
"	pop r27			\n"
"	pop r26			\n"
"	pop r25			\n"
"	pop r24			\n"
"	pop r23			\n"
"	pop r22			\n"
"	pop r21			\n"
"	pop r20			\n"
"	pop r19			\n"
"	pop r1			\n"
"	pop r0			\n"
	: /* outputs */
	: /* inputs */
	: /* clobbers */
		"memory"
	);

	__asm__ __volatile__(
"	pop r18			\n"
"	out %[_SREG], r18	\n"
"	pop r18			\n"
"	reti			\n"
	: /* outputs */
	: /* inputs */
		[_SREG] "I" (_SFR_IO_ADDR(SREG))
	: /* clobbers */
		"memory"
	);

	unreachable();
}

void i2cs_add_slave(const struct i2c_slave __flash *slave)
{
	uint8_t i;

	for (i = 0; i < ARRAY_SIZE(i2cs.slaves); i++) {
		if (!(i2cs.slaves[i])) {
			i2cs.slaves[i] = slave;
			break;
		}
	}
}

void i2cs_init(void)
{
	memset(&i2cs, 0, sizeof(i2cs));

	clkstretch_timer_init();

	/* SDA */
	SDA_PORT |= (1 << SDA_BIT);
	SDA_DDR &= (uint8_t)~(1 << SDA_BIT);

	/* SCL */
	SCL_PORT |= (1 << SCL_BIT);
	SCL_DDR |= (1 << SCL_BIT);

	/* Initialize USI in TWI slave mode. */
	usi_set_control(false, false);
	usi_set_counter(0, true);
}
