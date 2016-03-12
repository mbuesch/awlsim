#ifndef I2C_SLAVE_H_
#define I2C_SLAVE_H_

#include "util.h"


struct i2c_slave {
	uint8_t addr;
	void (*start_cond)(bool send);
	int16_t (*next_send_byte)(void);
	void (*receive_byte)(uint8_t byte);
};

void i2cs_add_slave(const struct i2c_slave __flash *slave);
void i2cs_init(void);

#endif /* I2C_SLAVE_H_ */
