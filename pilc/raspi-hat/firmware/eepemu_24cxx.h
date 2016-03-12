#ifndef EEPEMU_24CXX_H_
#define EEPEMU_24CXX_H_

#include "util.h"


void ee24cxx_set_we(bool write_enable);
bool ee24cxx_get_we(void);

void ee24cxx_init(void);

#endif /* EEPEMU_24CXX_H_ */
