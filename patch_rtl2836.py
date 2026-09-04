#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch saa7231_drv.c: mount YUAN RTL2836B via our rtl2836 driver."""

F = '/home/xxj/saa7231_debian/saa7231_drv.c'
t = open(F).read()


def rep(old, new, tag):
    n = t.count(old)
    assert n == 1, f"{tag}: count={n}"
    return t.replace(old, new)


# 1) includes: rtl2832/tda18218 -> rtl2836
t = rep('#include "rtl2832.h"\n#include "tda18218.h"\n',
        '#include "rtl2836.h"\n', 'includes')

# 2) replace pdata/config definitions with rtl2836 config
t = rep(
    '''static struct rtl2832_platform_data yuan_rtl2832_pdata = {
	.clk		= 27000000,	/* RTL2836B: 27 MHz crystal (datasheet) */
	.tuner		= RTL2832_TUNER_R820T,	/* placeholder; real tuner below */
};

static struct tda18218_config yuan_tda18218_config = {
	.i2c_address	= 0x60,	/* bus 13 */
	.i2c_wr_max	= 10,
	.loop_through	= 0,
};
''',
    '''static struct rtl2836_config yuan_rtl2836_cfg = {
	.i2c_addr	= 0x21,		/* bus 12: RTL2836B */
	.ts_serial	= 0,		/* parallel TS; module param to flip */
	.spec_inv	= 0,
};
''', 'pdata-defs')

# 3) replace the attach case body
t = rep(
    '''	case SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
		/* Yuan MC163ML: Realtek RTL2836B DTMB demod @ i2c-0:0x21 (bus 12)
		 * + tuner @ i2c-1:0x60 (bus 13, appears after GPIO power-up).
		 * Mount via the rtl2832 driver (i2c-client model, no chip-ID
		 * check) and attach the tuner with tda18271. NOTE: rtl2832 is a
		 * DVB-T demod driver - DTMB decoding itself still needs work,
		 * this mount only brings the front-end up in TVH. */
		if (frontend != 0)
			break;

		{
			struct i2c_client *rtl2832_client;
			struct i2c_board_info info;

			memset(&info, 0, sizeof(info));
			strscpy(info.type, "rtl2832", I2C_NAME_SIZE);
			info.addr = 0x21;
			info.platform_data = &yuan_rtl2832_pdata;

			rtl2832_client = i2c_new_client_device(
					&saa7231->i2c[0].i2c_adapter, &info);
			if (IS_ERR(rtl2832_client)) {
				dprintk(SAA7231_ERROR, 1,
					"YUAN: rtl2832 i2c client create failed");
				ret = -ENODEV;
				goto exit;
			}

			/* let the rtl2832 driver probe, then fetch the frontend */
			msleep(300);
			if (yuan_rtl2832_pdata.get_dvb_frontend)
				dvb->fe = yuan_rtl2832_pdata.get_dvb_frontend(rtl2832_client);
			if (!dvb->fe) {
				dprintk(SAA7231_ERROR, 1,
					"YUAN: rtl2832 probe failed - no frontend");
				ret = -ENODEV;
				goto exit;
			}
			dprintk(SAA7231_INFO, 1, "YUAN: RTL2836B (rtl2832) frontend attached");

			/* tuner @ i2c-1:0x60 - TDA18218HN silicon tuner
			 * (tda18271 probe returned "Unknown device 0", so it is not
			 * a TDA18271; TDA18218 sits at 0x60 in DMB-TH designs) */
			if (!dvb_attach(tda18218_attach, dvb->fe,
					&saa7231->i2c[1].i2c_adapter,
					&yuan_tda18218_config)) {
				dprintk(SAA7231_ERROR, 1,
					"YUAN: tda18218 attach failed (i2c-1:0x60) - keeping demod only");
			} else {
				dprintk(SAA7231_INFO, 1, "YUAN: TDA18218 tuner attached @ i2c-1:0x60");
			}
		}
		break;''',
    '''	case SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
		/* Yuan MC163ML: Realtek RTL2836B DTMB demod @ i2c-0:0x21 (bus 12)
		 * + tuner @ i2c-1:0x60 (bus 13, appears after GPIO power-up).
		 * Mounted via our rtl2836 driver (real DTMB demod, ported from
		 * the Realtek SDK). Tuner identification still pending. */
		if (frontend != 0)
			break;

		dvb->fe = dvb_attach(rtl2836_attach, &yuan_rtl2836_cfg,
				     &saa7231->i2c[0].i2c_adapter);
		if (!dvb->fe) {
			dprintk(SAA7231_ERROR, 1,
				"YUAN: rtl2836 attach failed (i2c-0:0x21)");
			ret = -ENODEV;
			goto exit;
		}
		dprintk(SAA7231_INFO, 1, "YUAN: RTL2836B (rtl2836) frontend attached");

		/* tuner @ i2c-1:0x60 - identity TBD (not tda18271/tda18218,
		 * suspected ADMTV series per MyGica D690 reference). Try the
		 * MT2063 driver as an interim probe; keep demod-only on fail. */
		{
			struct mt2063_config yuan_mt2063_cfg = {
				.tuner_address = 0x60,
			};
			struct dvb_frontend *tuner;

			tuner = dvb_attach(mt2063_attach, dvb->fe,
					   &saa7231->i2c[1].i2c_adapter,
					   &yuan_mt2063_cfg);
			if (tuner)
				dprintk(SAA7231_INFO, 1,
					"YUAN: MT2063 tuner attached @ i2c-1:0x60");
			else
				dprintk(SAA7231_INFO, 1,
					"YUAN: no tuner attached yet (demod only)");
		}
		break;''', 'attach-case')

open(F, 'w').write(t)
print('PATCH_OK')
