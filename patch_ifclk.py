#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Make A328 LGS8G75 ADC clock (if_clk_freq) a runtime module parameter
# so we can sweep crystal frequencies without recompiling.
import io

f = "/home/xxj/A328_D_Driver/saa7231_drv.c"
t = io.open(f, encoding="utf-8").read()

# ---- 1) module param before the config struct ----
old = """/* ------------------------------------------------------------------
 * AVerMedia A328 Pure DTMB frontend configuration
 * ------------------------------------------------------------------ */
static struct lgs8gxx_config a328_lgs8g75_config = {
"""
new = """/* ------------------------------------------------------------------
 * AVerMedia A328 Pure DTMB frontend configuration
 * ------------------------------------------------------------------ */

/* LGS8G75 ADC clock (kHz). Default 30400 is the Legend Silicon
 * reference value; the A328 board crystal may differ, so this is
 * exposed as a module parameter for on-the-fly sweeping:
 *   echo 28800 > /sys/module/saa7231_drv/parameters/a328_if_clk
 * then reload saa7231_drv. */
static int a328_if_clk = 30400;
module_param(a328_if_clk, int, 0644);
MODULE_PARM_DESC(a328_if_clk, "LGS8G75 ADC clock in kHz (A328, default 30400)");

static struct lgs8gxx_config a328_lgs8g75_config = {
"""
assert t.count(old) == 1, "param anchor"
t = t.replace(old, new)

# ---- 2) apply param right before lgs8gxx attach ----
old = """\t\tif (frontend != 0)
\t\t\tbreak;

\t\tdvb->fe = dvb_attach(lgs8gxx_attach, &a328_lgs8g75_config,
\t\t\t\t     &saa7231->i2c[0].i2c_adapter);
"""
new = """\t\tif (frontend != 0)
\t\t\tbreak;

\t\ta328_lgs8g75_config.if_clk_freq = a328_if_clk;
\t\tdprintk(SAA7231_INFO, 1, "A328: LGS8G75 if_clk=%d kHz", a328_if_clk);
\t\tdvb->fe = dvb_attach(lgs8gxx_attach, &a328_lgs8g75_config,
\t\t\t\t     &saa7231->i2c[0].i2c_adapter);
"""
assert t.count(old) == 1, "attach anchor"
t = t.replace(old, new)

io.open(f, "w", encoding="utf-8", newline="\n").write(t)
print("IFCLK_PARAM_OK")
