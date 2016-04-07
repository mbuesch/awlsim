#ifndef I2C_SLAVE_H_
#define I2C_SLAVE_H_

#include "util.h"


struct i2c_slave_ops {
	uint8_t (*transmit)(bool start);
	bool (*receive)(bool start, uint8_t byte);
};

void i2cs_add_slave(uint8_t addr, const struct i2c_slave_ops __flash *ops);
void i2cs_init(void);

#endif /* I2C_SLAVE_H_ */
