#ifndef PB_TXEN_H_
#define PB_TXEN_H_

#include "util.h"


enum pb_txen_debugmode {
	PBTXEN_DBG_OFF,		/* Debug mode off. */
	PBTXEN_DBG_RETRIG,	/* Continuous retrigger. */
	PBTXEN_DBG_NOTRIG,	/* No trigger. */
};

void pb_txen_set_timeout(uint16_t microseconds);
uint16_t pb_txen_get_timeout(void);

void pb_txen_set_debug(enum pb_txen_debugmode mode);
enum pb_txen_debugmode pb_txen_get_debug(void);

void pb_txen_init(void);
void pb_txen_work(void) noreturn;

#endif /* PB_TXEN_H_ */
