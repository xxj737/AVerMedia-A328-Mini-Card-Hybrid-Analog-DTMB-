#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Parameterize LGS8G75 ADC config (if_neg_center/if_neg_edge/adc_signed/adc_vpp)
# as module parameters so we can sweep combinations at runtime.
import io

f = "/home/xxj/A328_D_Driver/saa7231_drv.c"
t = io.open(f, encoding="utf-8").read()

# ---- 1) extend module params ----
old = """static int a328_if_clk = 30400;
module_param(a328_if_clk, int, 0644);
MODULE_PARM_DESC(a328_if_clk, "LGS8G75 ADC clock in kHz (A328, default 30400)");
"""
new = """static int a328_if_clk = 30400;
module_param(a328_if_clk, int, 0644);
MODULE_PARM_DESC(a328_if_clk, "LGS8G75 ADC clock in kHz (A328, default 30400)");

static int a328_if_neg_center = 0;
module_param(a328_if_neg_center, int, 0644);
MODULE_PARM_DESC(a328_if_neg_center, "LGS8G75 IF negative center (default 0)");

static int a328_if_neg_edge = 1;
module_param(a328_if_neg_edge, int, 0644);
MODULE_PARM_DESC(a328_if_neg_edge, "LGS8G75 IF negative edge (default 1)");

static int a328_adc_signed = 1;
module_param(a328_adc_signed, int, 0644);
MODULE_PARM_DESC(a328_adc_signed, "LGS8G75 ADC signed (default 1)");

static int a328_adc_vpp = 3;
module_param(a328_adc_vpp, int, 0644);
MODULE_PARM_DESC(a328_adc_vpp, "LGS8G75 ADC Vpp select 0-3 (default 3)");
"""
assert t.count(old) == 1, "params"
t = t.replace(old, new)

# ---- 2) apply params before attach ----
old = """\t\ta328_lgs8g75_config.if_clk_freq = a328_if_clk;
\t\tdprintk(SAA7231_INFO, 1, "A328: LGS8G75 if_clk=%d kHz", a328_if_clk);
"""
new = """\t\ta328_lgs8g75_config.if_clk_freq = a328_if_clk;
\t\ta328_lgs8g75_config.if_neg_center = a328_if_neg_center;
\t\ta328_lgs8g75_config.if_neg_edge = a328_if_neg_edge;
\t\ta328_lgs8g75_config.adc_signed = a328_adc_signed;
\t\ta328_lgs8g75_config.adc_vpp = a328_adc_vpp;
\t\tdprintk(SAA7231_INFO, 1,
\t\t\t"A328: LGS8G75 if_clk=%d ifnegc=%d ifnege=%d adcsgn=%d vpp=%d",
\t\t\ta328_if_clk, a328_if_neg_center, a328_if_neg_edge,
\t\t\ta328_adc_signed, a328_adc_vpp);
"""
assert t.count(old) == 1, "apply"
t = t.replace(old, new)

io.open(f, "w", encoding="utf-8", newline="\n").write(t)
print("ADC_PARAM_OK")
