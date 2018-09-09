#ifndef BYTESWAP_WIN_H_
#define BYTESWAP_WIN_H_

#include <stdint.h>

static inline uint16_t bswap_16(uint16_t v)
{
	return (v << 8) | (v >> 8);
}

static inline uint32_t bswap_32(uint32_t v)
{
	return ((v << 24) & 0xFF000000u) |
	       ((v << 8)  & 0x00FF0000u) |
	       ((v >> 8)  & 0x0000FF00u) |
	       ((v >> 24) & 0x000000FFu);
}

#endif /* BYTESWAP_WIN_H_ */
