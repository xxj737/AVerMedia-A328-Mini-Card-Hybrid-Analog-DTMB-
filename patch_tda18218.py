#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Switch YUAN tuner attach from tda18271 (wrong chip, "Unknown device 0")
# to tda18218 (TDA18218HN @ 0x60, matches the DMB-TH era silicon tuner).
import io

f = "/home/xxj/saa7231_debian/saa7231_drv.c"
t = io.open(f, encoding="utf-8").read()

# 1) include
old = '#include "rtl2832.h"\n'
assert t.count(old) == 1
t = t.replace(old, old + '#include "tda18218.h"\n', 1)

# 2) config struct next to yuan_rtl2832_pdata
old = """static struct rtl2832_platform_data yuan_rtl2832_pdata = {
\t.clk\t\t= 27000000,\t/* RTL2836B: 27 MHz crystal (datasheet) */
\t.tuner\t\t= RTL2832_TUNER_R820T,\t/* placeholder; real tuner below */
};
"""
new = old + """
static struct tda18218_config yuan_tda18218_config = {
\t.i2c_address\t= 0x60,\t/* bus 13 */
\t.i2c_wr_max\t= 10,
\t.loop_through\t= 0,
};
"""
assert t.count(old) == 1, "cfg"
t = t.replace(old, new)

# 3) tuner attach: tda18271 -> tda18218
old = """\t\t\t/* tuner @ i2c-1:0x60 - reuse the A328 tda18271 config
\t\t\t * (same 4.57 MHz IF, DTMB set_params wrapper) */
\t\t\tif (!dvb_attach(tda18271_attach, dvb->fe, 0x60,
\t\t\t\t\t&saa7231->i2c[1].i2c_adapter,
\t\t\t\t\t&a328_tda18271_config)) {
\t\t\t\tdprintk(SAA7231_ERROR, 1,
\t\t\t\t\t"YUAN: tuner attach failed (i2c-1:0x60) - keeping demod only");
\t\t\t} else {
\t\t\t\tdprintk(SAA7231_INFO, 1, "YUAN: tuner attached @ i2c-1:0x60");
\t\t\t\tif (dvb->fe->ops.tuner_ops.set_params) {
\t\t\t\t\ta328_tuner_set_params_orig =
\t\t\t\t\t\tdvb->fe->ops.tuner_ops.set_params;
\t\t\t\t\tdvb->fe->ops.tuner_ops.set_params =
\t\t\t\t\t\ta328_tuner_set_params;
\t\t\t\t}
\t\t\t}
"""
new = """\t\t\t/* tuner @ i2c-1:0x60 - TDA18218HN silicon tuner
\t\t\t * (tda18271 probe returned "Unknown device 0", so it is not
\t\t\t * a TDA18271; TDA18218 sits at 0x60 in DMB-TH designs) */
\t\t\tif (!dvb_attach(tda18218_attach, dvb->fe,
\t\t\t\t\t&saa7231->i2c[1].i2c_adapter,
\t\t\t\t\t&yuan_tda18218_config)) {
\t\t\t\tdprintk(SAA7231_ERROR, 1,
\t\t\t\t\t"YUAN: tda18218 attach failed (i2c-1:0x60) - keeping demod only");
\t\t\t} else {
\t\t\t\tdprintk(SAA7231_INFO, 1, "YUAN: TDA18218 tuner attached @ i2c-1:0x60");
\t\t\t}
"""
assert t.count(old) == 1, "attach"
t = t.replace(old, new)

io.open(f, "w", encoding="utf-8", newline="\n").write(t)
print("TDA18218_OK")
