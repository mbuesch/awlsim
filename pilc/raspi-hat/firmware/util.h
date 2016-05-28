#ifndef MY_UTIL_H_
#define MY_UTIL_H_

#ifndef F_CPU
# warning "F_CPU not defined"
#endif
#include <util/delay.h>

#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <avr/cpufunc.h>
#include <avr/eeprom.h>


/* Return the smaller value of 'a' and 'b'. */
#define min(a, b)	({						\
		__typeof__(a) __amin = (a);				\
		__typeof__(b) __bmin = (b);				\
		(__typeof__(a))(__amin < __bmin ? __amin : __bmin);	\
	})

/* Return the bigger value of 'a' and 'b'. */
#define max(a, b)	({						\
		__typeof__(a) __amax = (a);				\
		__typeof__(b) __bmax = (b);				\
		(__typeof__(a))(__amax > __bmax ? __amax : __bmax);	\
	})

/* Return 'value' clamped inbetween 'min_val' and 'max_val'. */
#define clamp(value, min_val, max_val)		\
	max(min(value, max_val), min_val)

/* Return the absolute value of 'val' */
#undef abs
#define abs(val)	({			\
		__typeof__(val) __val = (val);	\
		__val >= 0 ? __val : -__val;	\
	})

/* Round an unsigned integer 'n' up to a multiple of 's'. */
#define round_up(n, s)          ((((n) + (s) - 1) / (s)) * (s))

/* Perform a signed ceiling division of 'x' / 'd'. */
#define sdiv_round_up(x, d)		({		\
		__typeof__(x) __r, __x = (x);		\
		__typeof__(d) __d = (d);		\
		if ((__x < 0) ^ (__d < 0))		\
			__r = __x / __d;		\
		else if ((__x < 0) && (__d < 0))	\
			__r = (__x + __d + 1) / __d;	\
		else					\
			__r = (__x + __d - 1) / __d;	\
		__r;					\
	})

/* Perform an unsigned ceiling division of 'x' / 'd'. */
#define udiv_round_up(x, d)		({	\
		__typeof__(x) __x = (x);	\
		__typeof__(d) __d = (d);	\
		(__x + __d - 1) / __d;		\
	})

/* Divide signed integer x by signed integer d and
 * round to the closest result. */
#define sdiv_round(x, d)	({			\
		__typeof__(x) __r, __x = (x);		\
		__typeof__(d) __d = (d);		\
		if ((__x < 0) ^ (__d < 0))		\
			__r = (__x - (__d / 2)) / __d;	\
		else					\
			__r = (__x + (__d / 2)) / __d;	\
		__r;					\
	})

/* Divide unsigned integer x by unsigned integer d and
 * round to the closest result. */
#define udiv_round(x, d)	({		\
		__typeof__(x) __x = (x);	\
		__typeof__(d) __d = (d);	\
		(__x + (__d / 2)) / __d;	\
	})

/* Swap values 'a' and 'b' in place.
 * Also checks whether 'a' and 'b' are of the same type. */
#define swap_values(a, b)	do {		\
		__typeof__(a) __a = (a);	\
		__typeof__(b) __b = (b);	\
		__typeof__(a) __tmp = __a;	\
		(void)((&__a) == (&__b));	\
		(a) = __b;			\
		(b) = __tmp;			\
	} while (0)

/* Return the number of elements in a C array. */
#define ARRAY_SIZE(x)		(sizeof(x) / sizeof((x)[0]))

/* Full memory barrier. */
#define memory_barrier()	__asm__ __volatile__("" : : : "memory")

/* Do-not-inline function attribute. */
#define noinline		__attribute__((__noinline__))

/* Pure-function attribute. */
#define pure_fn			__attribute__((__pure__))

/* Const-function attribute. */
#define const_fn		__attribute__((__const__))

/* Data structure packing attribute. */
#define _packed			__attribute__((__packed__))

/* Naked functions. */
#define _naked			__attribute__((__naked__))

/* Suppress 'unused' warnings. */
#define _used			__attribute__((__used__))

/* Build-time assertion.
 * 'cond' must be a compile-time constant.
 * Build will fail, if 'cond' is false.
 */
#define build_assert(cond)	((void)sizeof(char[1 - 2 * !(cond)]))

/* Code flow attributes */
#define noreturn		__attribute__((__noreturn__))
#define _mainfunc		__attribute__((__OS_main__))
#if defined(__GNUC__) && __GNUC__ >= 4 && __GNUC_MINOR__ >= 5
# define unreachable()		__builtin_unreachable()
#else
# define unreachable()		do {} while (1)
#endif

/* Mark branches as likely/unlikely. */
#ifdef __GNUC__
# define likely(cond)		__builtin_expect(!!(cond), 1)
# define unlikely(cond)		__builtin_expect(!!(cond), 0)
#else
# define likely(cond)		(!!(cond))
# define unlikely(cond)		(!!(cond))
#endif

/* Convert something to a string. */
#define _tostr(x)		#x
#define tostr(x)		_tostr(x)

/* Non-standard integer types. */
typedef __int24		int24_t;
typedef __uint24	uint24_t;


/* Disable interrupts globally. */
static inline void irq_disable(void)
{
	cli();
	memory_barrier();
}

/* Enable interrupts globally. */
static inline void irq_enable(void)
{
	memory_barrier();
	sei();
}

/* Save flags and disable interrupts globally. */
static inline uint8_t irq_disable_save(void)
{
	uint8_t sreg = SREG;
	cli();
	memory_barrier();
	return sreg;
}

/* Restore interrupt flags. */
static inline void irq_restore(uint8_t sreg_flags)
{
	memory_barrier();
	SREG = sreg_flags;
}

/* Check whether the interrupt-enable flag is set in 'sreg_flags' */
static inline bool __irqs_enabled(uint8_t sreg_flags)
{
	return !!(sreg_flags & (1 << SREG_I));
}

/* Check whether interrupts are enabled globally. */
static inline bool irqs_enabled(void)
{
	return __irqs_enabled(SREG);
}

/* Indirect special function register access. */
typedef uint16_t sfr_addr_t;
#define SFR_ADDR(sfr)		_SFR_ADDR(sfr)
#define SFR_BYTE(sfr_addr)	_MMIO_BYTE(sfr_addr)

#endif /* MY_UTIL_H_ */
