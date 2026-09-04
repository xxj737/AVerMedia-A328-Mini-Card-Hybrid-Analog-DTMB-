/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RTL2836_H
#define RTL2836_H

#include <linux/kconfig.h>
#include <media/dvb_frontend.h>

struct rtl2836_config {
	u8 i2c_addr;
	u8 ts_serial;   /* 0 = parallel TS, 1 = serial TS */
	u8 spec_inv;    /* 0 = normal spectrum, 1 = inverse */
};

#if IS_REACHABLE(CONFIG_DVB_RTL2836)
struct dvb_frontend *rtl2836_attach(const struct rtl2836_config *cfg,
				    struct i2c_adapter *i2c);
#else
static inline struct dvb_frontend *rtl2836_attach(
		const struct rtl2836_config *cfg, struct i2c_adapter *i2c)
{
	pr_warn("%s: driver disabled by Kconfig\n", __func__);
	return NULL;
}
#endif

#endif /* RTL2836_H */
