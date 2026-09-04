#!/usr/bin/env python3
# Patch saa7231_drv.c: keep tda18271 XTAL output (XTOUT, EB22 bit 5) enabled
# after every set_params call. tda18271's own init_regs writes back the
# default EB22=0x84 on every set_params, clearing XTOUT, so we must
# re-write it after each tune.
import sys

f = "/home/xxj/saa7231_debian/saa7231_drv.c"
t = open(f, encoding="utf-8").read()

def rep(old, new, tag):
    global t
    if t.count(old) != 1:
        print("FAIL", tag, t.count(old))
        sys.exit(1)
    t = t.replace(old, new)
    print("ok", tag)

# Add a one-time include guard for tda18271 headers if needed.
rep(
    'static int a328_tuner_set_params(struct dvb_frontend *fe)\n'
    '{\n'
    '\tstruct dtv_frontend_properties *c = &fe->dtv_property_cache;\n\n'
    '\tif (c->delivery_system == SYS_DTMB) {\n'
    '\t\tc->delivery_system = SYS_DVBT;\n'
    '\t\tc->bandwidth_hz = 8000000;\n'
    '\t}\n'
    '\treturn a328_tuner_set_params_orig(fe);\n'
    '}\n',
    'static int a328_tuner_set_params(struct dvb_frontend *fe)\n'
    '{\n'
    '\tstruct dtv_frontend_properties *c = &fe->dtv_property_cache;\n'
    '\tint ret;\n\n'
    '\tif (c->delivery_system == SYS_DTMB) {\n'
    '\t\tc->delivery_system = SYS_DVBT;\n'
    '\t\tc->bandwidth_hz = 8000000;\n'
    '\t}\n'
    '\tret = a328_tuner_set_params_orig(fe);\n\n'
    '\t/* A328: re-enable tda18271 XTAL output to XOUT pin after every tune,\n'
    '\t * because tda18271_init_regs() writes the default EB22=0x84 which\n'
    '\t * clears XTOUT. Without XTOUT the LGS8G75 demodulator has no clock\n'
    '\t * and never responds to writes. */\n'
    '\tif (ret == 0) {\n'
    '\t\tstruct tda18271_priv *p = fe->tuner_priv;\n'
    '\t\tif (p && tda18271_read_regs(fe) == 0 &&\n'
    '\t\t    !(p->tda18271_regs[R_EB22] & 0x20)) {\n'
    '\t\t\tp->tda18271_regs[R_EB22] |= 0x20;\n'
    '\t\t\ttda18271_write_regs(fe, R_EB22, 1);\n'
    '\t\t}\n'
    '\t}\n'
    '\treturn ret;\n'
    '}\n',
    "xto re-arm")

open(f, "w", encoding="utf-8").write(t)
print("DONE")
