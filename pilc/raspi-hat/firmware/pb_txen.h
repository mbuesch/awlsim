#ifndef PB_TXEN_H_
#define PB_TXEN_H_

#include "util.h"


void pb_txen_set_timeout(uint16_t microseconds);
uint16_t pb_txen_get_timeout(void);

void pb_txen_set_debug(bool debug);
bool pb_txen_get_debug(void);

void pb_txen_init(void);
void pb_txen_work(void) noreturn;

#endif /* PB_TXEN_H_ */
