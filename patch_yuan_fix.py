#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Fix YUAN MC163ML: it is a Realtek RTL2836B (NOT LGS8G75) with NO tuner.
# Do not attach lgs8gxx -> stop the wrong "LGS8913/LGS8GXX" identification.
import io

f = "/home/xxj/saa7231_debian/saa7231_drv.c"
t = io.open(f, encoding="utf-8").read()

old = """\tcase SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
\t\t/* Yuan MC163ML: only a DTMB demod at i2c-0:0x21 (bus 12);
\t\t * no tuner on i2c-2 (bus 14). Try LGS8G75 first - the chip
\t\t * ACKs but reads 0xFF until its firmware is loaded, exactly
\t\t * like the A328 did before attach. */
\t\tif (frontend != 0)
\t\t\tbreak;

\t\tdvb->fe = dvb_attach(lgs8gxx_attach, &a328_lgs8g75_config,
\t\t\t\t     &saa7231->i2c[0].i2c_adapter);
\t\tif (!dvb->fe) {
\t\t\tdprintk(SAA7231_ERROR, 1, "YUAN: LGS8G75 attach failed (i2c-0:0x21)");
\t\t\tret = -ENODEV;
\t\t\tgoto exit;
\t\t}
\t\tdprintk(SAA7231_INFO, 1, "YUAN: LGS8G75 frontend attached");
\t\tbreak;
"""
new = """\tcase SUBSYS_INFO(YUAN_TECHNOLOGY, YUAN_MC163ML):
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
assert t.count(old) == 1, "yuan case"
t = t.replace(old, new)

io.open(f, "w", encoding="utf-8", newline="\n").write(t)
print("YUAN_FIX_OK")
