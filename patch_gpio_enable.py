#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A328: force GPIO0-7 high in frontend_enable (they power/control the
# front-end chips; verified: pulling them low kills TDA18271 on i2c-2).
import io

f = "/home/xxj/saa7231_debian/saa7231_drv.c"
t = io.open(f, encoding="utf-8").read()

old = """\tcase SUBSYS_INFO(AVERMEDIA_TECHNOLOGY, AVERMEDIA_A328_DTMB):
\t\t/* Chips on the A328 ACK on the on-chip I2C buses without any
\t\t * GPIO power/reset sequencing (verified with i2cdetect on
\t\t * bus i2c-0: demod 0x21, i2c-2: tuner 0x60). */
\t\tbreak;
"""
new = """\tcase SUBSYS_INFO(AVERMEDIA_TECHNOLOGY, AVERMEDIA_A328_DTMB):
\t\t/* GPIO0-7 power/control the front-end chips. Verified on the
\t\t * bench: pulling them low kills the TDA18271 on i2c-2 (0x60 no
\t\t * longer ACKs), restoring them high revives it. Force all high
\t\t * at probe so demod 0x21 + tuner 0x60 stay powered. */
\t\tGPIO_SET_OUT(0xFF);
\t\tif (saa7231_gpio_set(saa7231, 0xFF, 1) < 0)
\t\t\tret = -EIO;
\t\tbreak;
"""
assert t.count(old) == 1, "a328 fe_enable"
t = t.replace(old, new)

io.open(f, "w", encoding="utf-8", newline="\n").write(t)
print("A328_GPIO_ENABLE_OK")
