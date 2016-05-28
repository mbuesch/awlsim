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

#ifndef I2CS_EXPECTED_KHZ
# error "I2CS_EXPECTED_KHZ is not defined"
#endif


enum i2cs_state {
	I2CS_STATE_ADDR,	/* Handle received address */
	I2CS_STATE_PREP_SND,	/* Prepare sending of data */
	I2CS_STATE_PREP_RCV,	/* Prepare receiving of data */
	I2CS_STATE_SND,		/* Data was sent */
	I2CS_STATE_RCV,		/* Handle received data */
	I2CS_STATE_RCVPROC,	/* Process received data */
	I2CS_STATE_RCV_ACK,	/* Handle received ack after sent data */
};

#define I2CS_NO_ADDR		0xFF
#define I2CS_NO_SLAVE		0xFF

static enum i2cs_state _used i2cs_state;
static uint8_t _used i2cs_addrs[I2CS_MAX_NR_SLAVES];
static uint8_t _used i2cs_active_slave;
static uint8_t _used i2cs_rx_byte;
static bool i2cs_had_start;
static const struct i2c_slave_ops __flash _used *i2cs_ops[I2CS_MAX_NR_SLAVES];


#ifdef I2CS_CLKSTRETCH_WORKAROUND

/* Raspberry Pi I2C clock stretching bug workaround. */

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
	GTCCR &= (uint8_t)~(1 << PSR0);
	GTCCR &= (uint8_t)~(1 << TSM);
	TCCR0A = (0 << COM0A1) | (0 << COM0A0) |
		 (0 << COM0B1) | (0 << COM0B0) |
		 (0 << WGM01) | (0 << WGM00);
	TCCR0B = (0 << FOC0A) | (0 << FOC0B) |
		 (0 << WGM02) |
		 (0 << CS02) | (1 << CS01) | (0 << CS00);
#define TCNT0_KHZ 1000
}

/* Prepare the clock stretching workaround timer.
 * r31 is the only register allowed to be clobbered.
 * Everything else (including SREG) must be left untouched!
 */
#define CLKSTRETCH_TIMER_PREPARE() \
"	ldi	r31, %[_STRETCH_TIMER_PRELOAD]	\n" \
"	out	%[_TCNT0], r31			\n" \
"	ldi	r31, (1 << %[_TOV0])		\n" \
"	out	%[_TIFR], r31			\n"

/* Wait until we are in the safe range. */
#define CLKSTRETCH_TIMER_WAIT() \
"1:	in r31, %[_TIFR]			\n" \
"	sbrs r31, %[_TOV0]			\n" \
"	rjmp 1b					\n"

#else /* I2CS_CLKSTRETCH_WORKAROUND */

static void clkstretch_timer_init(void) { }
#define CLKSTRETCH_TIMER_PREPARE()	""
#define CLKSTRETCH_TIMER_WAIT()		""
#define TCNT0_KHZ			1000

#endif /* I2CS_CLKSTRETCH_WORKAROUND */

#define USICR_BASE	(		\
		(1 << USISIE) |		\
		(0 << USIOIE) |		\
		(1 << USIWM1) |		\
		(0 << USIWM0) |		\
		(1 << USICS1) |		\
		(0 << USICS0) |		\
		(0 << USICLK) |		\
		(0 << USITC)		\
	)

#define USISR_BASE	(		\
		(0 << USISIF) |		\
		(1 << USIOIF) |		\
		(1 << USIPF) |		\
		(0 << USICNT2) |	\
		(0 << USICNT1) |	\
		(0 << USICNT0)		\
	)

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
		USICR = USICR_BASE | (1 << USIOIE) | (0 << USIWM0);
	}
	USISR = USISR_BASE | (1 << USISIF) | (1 << USICNT0);

	i2cs_state = I2CS_STATE_ADDR;
	i2cs_active_slave = I2CS_NO_SLAVE;
	i2cs_had_start = true;

	memory_barrier();
}

static uint8_t _used slaveop_transmit(void)
{
	const struct i2c_slave_ops __flash *ops;
	uint8_t data;

	ops = i2cs_ops[i2cs_active_slave];
	data = ops->transmit(i2cs_had_start);
	i2cs_had_start = false;

	return data;
}

static uint8_t _used slaveop_receive(uint8_t data)
{
	const struct i2c_slave_ops __flash *ops;
	bool continue_rx;

	ops = i2cs_ops[i2cs_active_slave];
	continue_rx = ops->receive(i2cs_had_start, data);
	i2cs_had_start = false;

	return continue_rx ? 1u : 0u;
}

/* Save all caller-saved regs, except r0 and SREG. */
#define SAVE_CALLER_REGS()		\
	"	push r18	\n"	\
	"	push r19	\n"	\
	"	push r20	\n"	\
	"	push r21	\n"	\
	"	push r22	\n"	\
	"	push r23	\n"	\
	"	push r24	\n"	\
	"	push r25	\n"	\
	"	push r26	\n"	\
	"	push r27	\n"	\
	"	push r30	\n"	\
	"	push r31	\n"

/* Restore all caller-saved regs, except r0 and SREG. */
#define RESTORE_CALLER_REGS()		\
	"	pop r31		\n"	\
	"	pop r30		\n"	\
	"	pop r27		\n"	\
	"	pop r26		\n"	\
	"	pop r25		\n"	\
	"	pop r24		\n"	\
	"	pop r23		\n"	\
	"	pop r22		\n"	\
	"	pop r21		\n"	\
	"	pop r20		\n"	\
	"	pop r19		\n"	\
	"	pop r18		\n"

#define IN_CONSTR_BASE							\
	[_SREG]				"I" (_SFR_IO_ADDR(SREG)),	\
	[_TCNT0]			"I" (_SFR_IO_ADDR(TCNT0)),	\
	[_TIFR]				"I" (_SFR_IO_ADDR(TIFR)),	\
	[_TOV0]				"M" (TOV0),			\
	[_STRETCH_TIMER_PRELOAD]	"M" (256 - ((TCNT0_KHZ / I2CS_EXPECTED_KHZ) + 1)), \
	[_USIDR]			"I" (_SFR_IO_ADDR(USIDR)),	\
	[_USICR]			"I" (_SFR_IO_ADDR(USICR)),	\
	[_USISR]			"I" (_SFR_IO_ADDR(USISR)),	\
	[_SDA_DDR]			"I" (_SFR_IO_ADDR(SDA_DDR)),	\
	[_SDA_BIT]			"M" (SDA_BIT),			\
	[_SCL_PIN]			"I" (_SFR_IO_ADDR(SCL_PIN)),	\
	[_SCL_BIT]			"M" (SCL_BIT),			\
	[_STATE_ADDR]			"M" (I2CS_STATE_ADDR),		\
	[_STATE_PREP_SND]		"M" (I2CS_STATE_PREP_SND),	\
	[_STATE_PREP_RCV]		"M" (I2CS_STATE_PREP_RCV),	\
	[_STATE_SND]			"M" (I2CS_STATE_SND),		\
	[_STATE_RCV]			"M" (I2CS_STATE_RCV),		\
	[_STATE_RCVPROC]		"M" (I2CS_STATE_RCVPROC),	\
	[_STATE_RCV_ACK]		"M" (I2CS_STATE_RCV_ACK),	\
	[_I2CS_NO_SLAVE]		"M" (I2CS_NO_SLAVE)

static void _naked _used switch_to_start_condition_state(void)
{
	__asm__ __volatile__(
"	; Set USI to wait for start condition.		\n"
"	ldi r31, %[_cr_scond]				\n"
"	out %[_USICR], r31				\n"
"	ldi r31, %[_sr_scond]				\n"
"	out %[_USISR], r31				\n"
"							\n"
"	; Reset active slave index.			\n"
"	ldi r31, %[_I2CS_NO_SLAVE]			\n"
"	sts i2cs_active_slave, r31			\n"
"							\n"
"	rjmp isr_ovf_ret				\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE,
		[_cr_scond]	"M" (USICR_BASE | (0 << USIOIE) | (0 << USIWM0)),
		[_sr_scond]	"M" (USISR_BASE | (0 << USISIF) | (0 << USICNT0))
	: /* clobbers */
		"memory"
	);
	unreachable();
}

#define CHECK_ONE_ADDR(index) \
"	lds r31, i2cs_addrs + " tostr(index) "		\n" \
"	cp r31, __tmp_reg__				\n" \
"	ldi r31, " tostr(index) "			\n" \
"	breq handle_addr				\n" \

static void _naked _used handle_state_addr(void)
{
	__asm__ __volatile__(
"	; Read the received address.			\n"
"	in r30, %[_USIDR]				\n"
"							\n"
"	; Check if the address is ours.			\n"
"	mov __tmp_reg__, r30				\n"
"	lsr __tmp_reg__					\n"
#if I2CS_MAX_NR_SLAVES >= 1
	CHECK_ONE_ADDR(0)
#endif
#if I2CS_MAX_NR_SLAVES >= 2
	CHECK_ONE_ADDR(1)
#endif
#if I2CS_MAX_NR_SLAVES >= 3
	CHECK_ONE_ADDR(2)
#endif
#if I2CS_MAX_NR_SLAVES >= 4
# error "I2CS_MAX_NR_SLAVES is too big"
#endif
"							\n"
"	; Unknown address.				\n"
"	rjmp switch_to_start_condition_state		\n"
"							\n"
"handle_addr:						\n"
"	; Save the slave index.				\n"
"	sts i2cs_active_slave, r31			\n"
"							\n"
"	; Wait for SCK low				\n"
"1:	sbic %[_SCL_PIN], %[_SCL_BIT]			\n"
"	rjmp 1b						\n"
"							\n"
"	; Set SDA low for ACK.				\n"
"	out %[_USIDR], __zero_reg__			\n"
"	sbi %[_SDA_DDR], %[_SDA_BIT]			\n"
"							\n"
"	; Set USI to send ACK.				\n"
"	ldi r31, %[_cr_ack]				\n"
"	out %[_USICR], r31				\n"
"	ldi r31, %[_sr_ack]				\n"
"	out %[_USISR], r31				\n"
"							\n"
"	; Set the next state.				\n"
"	ldi r31, %[_STATE_PREP_SND]			\n"
"	sbrs r30, 0		; Check R/W bit		\n"
"	ldi r31, %[_STATE_PREP_RCV]			\n"
"	sts i2cs_state, r31				\n"
"							\n"
"	rjmp isr_ovf_ret				\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE,
		[_cr_ack]	"M" (USICR_BASE | (1 << USIOIE) | (1 << USIWM0)),
		[_sr_ack]	"M" (USISR_BASE | (0 << USISIF) | (14 << USICNT0))
	: /* clobbers */
		"memory"
	);
	unreachable();
}

static void _naked _used handle_state_prep_snd(void)
{
	__asm__ __volatile__(
	SAVE_CALLER_REGS()
"							\n"
"	; Call the slave op to get the next TX byte.	\n"
"	rcall slaveop_transmit				\n"
"							\n"
"	; Write the TX byte to USI.			\n"
"	out %[_USIDR], r24				\n"
"							\n"
"	; Enable SDA driver.				\n"
"	sbi %[_SDA_DDR], %[_SDA_BIT]			\n"
"							\n"
	RESTORE_CALLER_REGS()
"							\n"
	CLKSTRETCH_TIMER_WAIT()
"							\n"
"	; Set USI to send data				\n"
"	ldi r31, %[_cr_send]				\n"
"	out %[_USICR], r31				\n"
"	ldi r31, %[_sr_send]				\n"
"	out %[_USISR], r31				\n"
"	; Write counter again to make sure it's		\n"
"	; written after the pos. SCL edge.		\n"
"	out %[_USISR], r31				\n"
"							\n"
"	; Set the next state				\n"
"	ldi r31, %[_STATE_SND]				\n"
"	sts i2cs_state, r31				\n"
"							\n"
"	rjmp isr_ovf_ret				\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE,
		[_cr_send]	"M" (USICR_BASE | (1 << USIOIE) | (0 << USIWM0)),
		[_sr_send]	"M" (USISR_BASE | (0 << USISIF) | (2 << USICNT0))
	: /* clobbers */
		"memory"
	);
	unreachable();
}

static void _naked _used handle_state_prep_rcv(void)
{
	__asm__ __volatile__(
"	; Stop pulling SDA.				\n"
"	cbi %[_SDA_DDR], %[_SDA_BIT]			\n"
"							\n"
	CLKSTRETCH_TIMER_WAIT()
"							\n"
"	; Set USI to read data				\n"
"	ldi r31, %[_cr_rddata]				\n"
"	out %[_USICR], r31				\n"
"	ldi r31, %[_sr_rddata]				\n"
"	out %[_USISR], r31				\n"
"	; Write counter again to make sure it's		\n"
"	; written after the pos. SCL edge.		\n"
"	out %[_USISR], r31				\n"
"							\n"
"	; Set the next state				\n"
"	ldi r31, %[_STATE_RCV]				\n"
"	sts i2cs_state, r31				\n"
"							\n"
"	rjmp isr_ovf_ret				\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE,
		[_cr_rddata]	"M" (USICR_BASE | (1 << USIOIE) | (0 << USIWM0)),
		[_sr_rddata]	"M" (USISR_BASE | (0 << USISIF) | (2 << USICNT0))
	: /* clobbers */
		"memory"
	);
	unreachable();
}

static void _naked _used handle_state_rcv(void)
{
	__asm__ __volatile__(
"	; Get the received data				\n"
"	in r30, %[_USIDR]				\n"
"							\n"
"	; Wait for SCK low				\n"
"1:	sbic %[_SCL_PIN], %[_SCL_BIT]			\n"
"	rjmp 1b						\n"
"							\n"
"	; Store the received byte for later processing.	\n"
"	; Can't process it now due to possible		\n"
"	; Raspi SCL stretch bug.			\n"
"	sts i2cs_rx_byte, r30				\n"
"							\n"
"	; Set SDA low for ACK.				\n"
"	out %[_USIDR], __zero_reg__			\n"
"	sbi %[_SDA_DDR], %[_SDA_BIT]			\n"
"							\n"
"	; Set USI to send ack.				\n"
"	ldi r31, %[_cr_ack]				\n"
"	out %[_USICR], r31				\n"
"	ldi r31, %[_sr_ack]				\n"
"	out %[_USISR], r31				\n"
"							\n"
"	; Set the next state				\n"
"	ldi r31, %[_STATE_RCVPROC]			\n"
"	sts i2cs_state, r31				\n"
"							\n"
"	rjmp isr_ovf_ret				\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE,
		[_cr_ack]	"M" (USICR_BASE | (1 << USIOIE) | (1 << USIWM0)),
		[_sr_ack]	"M" (USISR_BASE | (0 << USISIF) | (14 << USICNT0))
	: /* clobbers */
		"memory"
	);
	unreachable();
}

static void _naked _used handle_state_rcvproc(void)
{
	__asm__ __volatile__(
	SAVE_CALLER_REGS()
"							\n"
"	; Call the slave op to receive the byte.	\n"
"	lds r24, i2cs_rx_byte				\n"
"	rcall slaveop_receive				\n"
"	mov __tmp_reg__, r24				\n"
"							\n"
	RESTORE_CALLER_REGS()
"							\n"
"	; If 'continue-rx' is set, prepare next RX	\n"
"	sbrc __tmp_reg__, 0				\n"
"	rjmp handle_state_prep_rcv			\n"
"							\n"
"	; We expect a new address transmission.		\n"
"							\n"
"	; Stop pulling SDA.				\n"
"	cbi %[_SDA_DDR], %[_SDA_BIT]			\n"
"							\n"
	CLKSTRETCH_TIMER_WAIT()
"							\n"
"	; Set USI to read addr				\n"
"	ldi r31, %[_cr_addrread]			\n"
"	out %[_USICR], r31				\n"
"	ldi r31, %[_sr_addrread]			\n"
"	out %[_USISR], r31				\n"
#if 0
"	; Write counter again to make sure it's		\n"
"	; written after the pos. SCL edge.		\n"
"	out %[_USISR], r31				\n"
#endif
"							\n"
"	; Set the next state				\n"
"	ldi r31, %[_STATE_ADDR]				\n"
"	sts i2cs_state, r31				\n"
"							\n"
"	rjmp isr_ovf_ret				\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE,
		[_cr_addrread]	"M" (USICR_BASE | (1 << USIOIE) | (0 << USIWM0)),
#if 0
		[_sr_addrread]	"M" (USISR_BASE | (0 << USISIF) | (2 << USICNT0))
#else
		[_sr_addrread]	"M" (USISR_BASE | (0 << USISIF) | (1 << USICNT0))
#endif
	: /* clobbers */
		"memory"
	);
	unreachable();
}

static void _naked _used handle_state_snd(void)
{
	__asm__ __volatile__(
"	; Release SDA.					\n"
"	cbi %[_SDA_DDR], %[_SDA_BIT]			\n"
"							\n"
"	; Wait for SCK low				\n"
"1:	sbic %[_SCL_PIN], %[_SCL_BIT]			\n"
"	rjmp 1b						\n"
"							\n"
"	; Set USI to read ack				\n"
"	ldi r31, %[_cr_rdack]				\n"
"	out %[_USICR], r31				\n"
"	ldi r31, %[_sr_rdack]				\n"
"	out %[_USISR], r31				\n"
"							\n"
"	; Set the next state				\n"
"	ldi r31, %[_STATE_RCV_ACK]			\n"
"	sts i2cs_state, r31				\n"
"							\n"
"	rjmp isr_ovf_ret				\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE,
		[_cr_rdack]	"M" (USICR_BASE | (1 << USIOIE) | (1 << USIWM0)),
		[_sr_rdack]	"M" (USISR_BASE | (0 << USISIF) | (14 << USICNT0))
	: /* clobbers */
		"memory"
	);
	unreachable();
}

static void _naked _used handle_state_rcv_ack(void)
{
	__asm__ __volatile__(
"	; Read the state of SDA to get ACK/NACK		\n"
"	in r30, %[_USIDR]				\n"
"							\n"
"	; Check whether we have ACK or NACK		\n"
"	andi r30, 0x01					\n"
"	brne chk_reply_got_nack				\n"
"							\n"
"	; We got an ACK.				\n"
"	; Just directly go to send.			\n"
"	rjmp handle_state_prep_snd			\n"
"							\n"
"chk_reply_got_nack:					\n"
"	rjmp switch_to_start_condition_state		\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE
	: /* clobbers */
		"memory"
	);
	unreachable();
}

static uint16_t _used state_handlers[] = {
	[I2CS_STATE_ADDR]	= (uint16_t)&handle_state_addr,
	[I2CS_STATE_PREP_SND]	= (uint16_t)&handle_state_prep_snd,
	[I2CS_STATE_PREP_RCV]	= (uint16_t)&handle_state_prep_rcv,
	[I2CS_STATE_SND]	= (uint16_t)&handle_state_snd,
	[I2CS_STATE_RCV]	= (uint16_t)&handle_state_rcv,
	[I2CS_STATE_RCVPROC]	= (uint16_t)&handle_state_rcvproc,
	[I2CS_STATE_RCV_ACK]	= (uint16_t)&handle_state_rcv_ack,
};

ISR(USI_OVF_vect, ISR_NAKED)
{
	__asm__ __volatile__(
"	push r31					\n"
CLKSTRETCH_TIMER_PREPARE()
"	in r31, %[_SREG]				\n"
"	push r31					\n"
"	push __tmp_reg__				\n"
"	push __zero_reg__				\n"
"	push r30					\n"
"	clr __zero_reg__				\n"
"							\n"
"	; Branch to the current state handler.		\n"
"	ldi r30, lo8(state_handlers)			\n"
"	ldi r31, hi8(state_handlers)			\n"
"	lds __tmp_reg__, i2cs_state			\n"
"	lsl __tmp_reg__					\n"
"	add r30, __tmp_reg__				\n"
"	adc r31, __zero_reg__				\n"
"	ld __tmp_reg__, Z+				\n"
"	ld r31, Z					\n"
"	mov r30, __tmp_reg__				\n"
"	ijmp						\n"
"							\n"
"isr_ovf_ret:						\n"
"	pop r30						\n"
"	pop __zero_reg__				\n"
"	pop __tmp_reg__					\n"
"	pop r31						\n"
"	out %[_SREG], r31				\n"
"	pop r31						\n"
"	reti						\n"
	: /* outputs */
	: /* inputs */
		IN_CONSTR_BASE
	: /* clobbers */
		"memory"
	);
	unreachable();
}

void i2cs_add_slave(uint8_t addr, const struct i2c_slave_ops __flash *ops)
{
	uint8_t i;

	for (i = 0; i < ARRAY_SIZE(i2cs_addrs); i++) {
		if (i2cs_addrs[i] == I2CS_NO_ADDR) {
			i2cs_addrs[i] = addr;
			i2cs_ops[i] = ops;
			break;
		}
	}
}

void i2cs_init(void)
{
	i2cs_state = I2CS_STATE_ADDR;
	i2cs_active_slave = I2CS_NO_SLAVE;
	i2cs_had_start = false;
	memset(i2cs_addrs, I2CS_NO_ADDR, sizeof(i2cs_addrs));

	clkstretch_timer_init();

	/* SDA */
	SDA_PORT |= (1 << SDA_BIT);
	SDA_DDR &= (uint8_t)~(1 << SDA_BIT);

	/* SCL */
	SCL_PORT |= (1 << SCL_BIT);
	SCL_DDR |= (1 << SCL_BIT);

	/* Initialize USI in TWI slave mode. */
	USICR = USICR_BASE | (0 << USIOIE) | (0 << USIWM0);
	USISR = USISR_BASE | (1 << USISIF) | (0 << USICNT0);
}
