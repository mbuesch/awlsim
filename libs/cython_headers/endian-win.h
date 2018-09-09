#ifndef ENDIAN_WIN_H_
#define ENDIAN_WIN_H_

#include "byteswap-win.h"

#define LITTLE_ENDIAN	1
#define BIG_ENDIAN	2
#define BYTE_ORDER	LITTLE_ENDIAN

static inline uint16_t htobe16(uint16_t v)
{
	if (BYTE_ORDER == LITTLE_ENDIAN)
		return bswap_16(v);
	return v;
}

static inline uint16_t htole16(uint16_t v)
{
	if (BYTE_ORDER == BIG_ENDIAN)
		return bswap_16(v);
	return v;
}

static inline uint16_t be16toh(uint16_t v)
{
	if (BYTE_ORDER == LITTLE_ENDIAN)
		return bswap_16(v);
	return v;
}

static inline uint16_t le16toh(uint16_t v)
{
	if (BYTE_ORDER == BIG_ENDIAN)
		return bswap_16(v);
	return v;
}

static inline uint32_t htobe32(uint32_t v)
{
	if (BYTE_ORDER == LITTLE_ENDIAN)
		return bswap_32(v);
	return v;
}

static inline uint32_t htole32(uint32_t v)
{
	if (BYTE_ORDER == BIG_ENDIAN)
		return bswap_32(v);
	return v;
}

static inline uint32_t be32toh(uint32_t v)
{
	if (BYTE_ORDER == LITTLE_ENDIAN)
		return bswap_32(v);
	return v;
}

static inline uint32_t le32toh(uint32_t v)
{
	if (BYTE_ORDER == BIG_ENDIAN)
		return bswap_32(v);
	return v;
}

#endif /* ENDIAN_WIN_H_ */
