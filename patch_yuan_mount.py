#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Mount YUAN MC163ML front-end: RTL2836B demod @ i2c-0:0x21 via rtl2832
# driver (i2c-client model) + tuner @ i2c-1:0x60 via tda18271.
# Also power the front-end through GPIO0-7 (tuner only appears after
# pulling them high - verified on the bench).
import io

f = "/home/xxj/saa7231_debian/saa7231_drv.c"
t = io.open(f, encoding="utf-8").read()

# ---- 1) include rtl2832.h ----
old = '#include "tda18271.h"\n'
assert t.count(old) >= 1, "include anchor"
t = t.replace(old, old + '#include "rtl2832.h"\n', 1)

# ---- 2) YUAN config structs (before avermedia_a328_dtmb board config) ----
old = """static struct saa7231_config avermedia_a328_dtmb = {
"""
new = """/* ------------------------------------------------------------------
 * YUAN MC163ML front-end: RTL2836B demod + tuner
 * ------------------------------------------------------------------ */
static struct rtl2832_platform_data yuan_rtl2832_pdata = {
\t.clk\t\t= 27000000,\t/* RTL2836B: 27 MHz crystal (datasheet) */
\t.tuner\t\t= RTL2832_TUNER_R820T,\t/* placeholder; real tuner below */
};

static struct saa7231_config avermedia_a328_dtmb = {
"""
assert t.count(old) == 1, "cfg anchor"
t = t.replace(old, new)

# ---- 3) YUAN frontend_enable: GPIO power-up ----
old = """\tcase SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
\t\t/* Same as A328: no GPIO sequencing required. */
\t\tbreak;
"""
new = """\tcase SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
\t\t/* GPIO0-7 power the front-end. Verified: the tuner on i2c-1:0x60
\t\t * only appears on the bus after pulling them high. */
\t\tGPIO_SET_OUT(0xFF);
\t\tif (saa7231_gpio_set(saa7231, 0xFF, 1) < 0)
\t\t\tret = -EIO;
\t\tmsleep(50);
\t\tbreak;
"""
assert t.count(old) == 1, "fe_enable anchor"
t = t.replace(old, new)

# ---- 4) YUAN frontend_attach: mount rtl2832 + tda18271 ----
old = """\tcase SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
\t\t/* Yuan MC163ML: the demod at i2c-0:0x21 (bus 12) is a Realtek
\t\t * RTL2836B (board silkscreen MC-963ML, Win10 HWID
\t\t * PCI\\VEN_1131&DEV_7231&SUBSYS_316212AB), NOT a Legend LGS8G75.
\t\t * The card has NO tuner (i2c-2 / bus 14 is empty), so it cannot
\t\t * tune any channel anyway. Attaching lgs8gxx here was wrong and
\t\t * made TVH enumerate two bogus "LGS8913/LGS8GXX" frontends.
\t\t * Leave the frontend unregistered. */
\t\tdprintk(SAA7231_INFO, 1,
\t\t\t"YUAN MC163ML: RTL2836B demod @ i2c-0:0x21, no tuner - frontend disabled");
\t\tbreak;
"""
new = """\tcase SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
\t\t/* Yuan MC163ML: Realtek RTL2836B DTMB demod @ i2c-0:0x21 (bus 12)
\t\t * + tuner @ i2c-1:0x60 (bus 13, appears after GPIO power-up).
\t\t * Mount via the rtl2832 driver (i2c-client model, no chip-ID
\t\t * check) and attach the tuner with tda18271. NOTE: rtl2832 is a
\t\t * DVB-T demod driver - DTMB decoding itself still needs work,
\t\t * this mount only brings the front-end up in TVH. */
\t\tif (frontend != 0)
\t\t\tbreak;

\t\t{
\t\t\tstruct i2c_client *rtl2832_client;
\t\t\tstruct i2c_board_info info;

\t\t\tmemset(&info, 0, sizeof(info));
\t\t\tstrscpy(info.type, "rtl2832", I2C_NAME_SIZE);
\t\t\tinfo.addr = 0x21;
\t\t\tinfo.platform_data = &yuan_rtl2832_pdata;

\t\t\trtl2832_client = i2c_new_client_device(
\t\t\t\t\t&saa7231->i2c[0].i2c_adapter, &info);
\t\t\tif (IS_ERR(rtl2832_client)) {
\t\t\t\tdprintk(SAA7231_ERROR, 1,
\t\t\t\t\t"YUAN: rtl2832 i2c client create failed");
\t\t\t\tret = -ENODEV;
\t\t\t\tgoto exit;
\t\t\t}

\t\t\t/* let the rtl2832 driver probe, then fetch the frontend */
\t\t\tmsleep(300);
\t\t\tif (yuan_rtl2832_pdata.get_dvb_frontend)
\t\t\t\tdvb->fe = yuan_rtl2832_pdata.get_dvb_frontend(rtl2832_client);
\t\t\tif (!dvb->fe) {
\t\t\t\tdprintk(SAA7231_ERROR, 1,
\t\t\t\t\t"YUAN: rtl2832 probe failed - no frontend");
\t\t\t\tret = -ENODEV;
\t\t\t\tgoto exit;
\t\t\t}
\t\t\tdprintk(SAA7231_INFO, 1, "YUAN: RTL2836B (rtl2832) frontend attached");

\t\t\t/* tuner @ i2c-1:0x60 - reuse the A328 tda18271 config
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
\t\t}
\t\tbreak;
"""
assert t.count(old) == 1, "fe_attach anchor"
t = t.replace(old, new)

io.open(f, "w", encoding="utf-8", newline="\n").write(t)
print("YUAN_MOUNT_OK")
