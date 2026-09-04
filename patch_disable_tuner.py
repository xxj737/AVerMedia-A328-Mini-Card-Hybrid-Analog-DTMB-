#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disable YUAN MT2063 tuner mount in saa7231_drv.c (I2C deadlock fix)"""

F = '/home/xxj/saa7231_debian/saa7231_drv.c'
t = open(F).read()

old = '''\t\t/* tuner @ i2c-1:0x60 - identity TBD (not tda18271/tda18218,
		 * suspected ADMTV series per MyGica D690 reference). Try the
		 * MT2063 driver as an interim probe; keep demod-only on fail. */
		{
			struct mt2063_config yuan_mt2063_cfg = {
				.tuner_address = 0x60,
			};
			struct dvb_frontend *tuner;

			tuner = dvb_attach(mt2063_attach, dvb->fe,
					   &yuan_mt2063_cfg,
					   &saa7231->i2c[1].i2c_adapter);
			if (tuner)
				dprintk(SAA7231_INFO, 1,
					"YUAN: MT2063 tuner attached @ i2c-1:0x60");
			else
				dprintk(SAA7231_INFO, 1,
					"YUAN: no tuner attached yet (demod only)");
		}
		break;'''

new = '''\t\t/* tuner @ i2c-1:0x60 - identity TBD. DISABLED for now: the
		 * MT2063 probe dead-locked the SAA7231 I2C controller while
		 * TVH enumerated the frontend (all 8 buses went dark). Keep
		 * the demod mounted only until the real tuner is identified
		 * (suspect ADMTV series per MyGica D690 reference). */
		dprintk(SAA7231_INFO, 1,
			"YUAN: tuner not mounted (I2C deadlock risk), demod only");
		break;'''

assert t.count(old) == 1, f'count={t.count(old)}'
open(F, 'w').write(t.replace(old, new))
print('TUNER_DISABLED_OK')
