#!/usr/bin/env python3
"""diag_read3.py - systematic read-direction attack on I2C3 (0x10C000).

Question: I2C3 ACKs on addr but RX always EMPTY.  Either (a) the read
dummy-clock mechanism is wrong (count/STOP/level), or (b) SCL is wedged
low on I2C3 so no real transfer completes (write "OK" = TX FIFO empty
is NOT proof of bus completion - FIFO drains into the shift register
even if SCL never clocks).

Every step dumps full I2C_STATUS so we can watch SCL(bit2)/SDA(bit3)/
BUS_ACTIVE(bit1) transition through the transaction.
"""
import os, struct, time

def rd32(fd, off): return struct.unpack("<I", os.pread(fd, 4, off))[0]
def wr32(fd, off, val): os.write(fd, struct.pack("<II", off, val & 0xFFFFFFFF))

DIAG = "/dev/saa_diag"
fd = os.open(DIAG, os.O_RDWR)
B = 0x10c000
TX = 0x00; STS = 0x08; CTL = 0x0C
CDH = 0x10; CDL = 0x14; SDAH = 0x28
RXL = 0x1C
START = 0x100; STOP = 0x200
TXE = 1 << 6; RXE = 1 << 4
SCL = 1 << 2; SDA = 1 << 3; ACT = 1 << 1

log = []
def st():
    s = rd32(fd, B + STS)
    flags = []
    if s & TXE: flags.append("TXE")
    if not (s & TXE): flags.append("tx!")
    if s & RXE: flags.append("RXE")
    if not (s & RXE): flags.append("rx!")
    if s & SCL: flags.append("SCL=1")
    else: flags.append("SCL=0")
    if s & SDA: flags.append("SDA=1")
    else: flags.append("SDA=0")
    if s & ACT: flags.append("ACT")
    if s & (1 << 8): flags.append("TXSE")
    return "0x%03X[%s]" % (s & 0xFFF, ",".join(flags))

def go():
    c = rd32(fd, B + CTL)
    wr32(fd, B + CTL, c | 0x01)
def push(v): wr32(fd, B + TX, v)
def wait_tx(tries=300, d=0.002):
    for _ in range(tries):
        if st_raw() & TXE: return True
        time.sleep(d)
    return False
def st_raw(): return rd32(fd, B + STS)
def wait_rx(tries=300, d=0.002):
    for _ in range(tries):
        if not (st_raw() & RXE): return True
        time.sleep(d)
    return False
def rx(): return rd32(fd, B + TX) & 0xFF

def full_hwinit():
    wr32(fd, B + CTL, 0x00cc); time.sleep(0.005)
    wr32(fd, B + CTL, 0x00c1); time.sleep(0.005)
    for _ in range(100):
        if rd32(fd, B + CTL) == 0xc0: break
        time.sleep(0.001)
    wr32(fd, B + CDH, 0x00d0)
    wr32(fd, B + CDL, 0x010e)
    wr32(fd, B + SDAH, 0x007c)
    wr32(fd, B + 0xfd8, 0x1fff)
    wr32(fd, B + 0xfe8, 0x1fff)

def t(stage):
    log.append("%-22s %s" % (stage, st()))
    return st()

print("== I2C3 (0x10C000) read-direction attack ==")
print("MODULE_CONF=0x%08X MODULE_ID=0x%08X" % (rd32(fd, B+0xfd4), rd32(fd, B+0xffc)))
print("CLKDIV_H=0x%08X CLKDIV_L=0x%08X SDAHOLD=0x%08X RXL=0x%08X" %
      (rd32(fd, B+CDH), rd32(fd, B+CDL), rd32(fd, B+SDAH), rd32(fd, B+RXL)))
full_hwinit()
print("hwinit done:", st())

DEV = 0x60   # TDA18271
REG = 0x00

def variant(name, fn):
    global log
    log = []
    full_hwinit()
    res = fn()
    print("\n--- %s ---" % name)
    for l in log: print("  " + l)
    print("  => %s" % res)
    return res

def vA_dummy_stop():
    """W regptr, Sr+R, dummy|STOP, wait_rx, read RX"""
    t("init")
    push((DEV << 1) | START); go(); t("addrW pushed")
    if not wait_tx(): return "TXstuck@addrW"
    t("addrW moved")
    push(REG); go(); t("reg pushed")
    if not wait_tx(): return "TXstuck@reg"
    t("reg moved")
    push((DEV << 1) | 1 | START); go(); t("addrR pushed")
    if not wait_tx(): return "TXstuck@addrR"
    t("addrR moved")
    push(0x00 | STOP); go(); t("dummy|STOP pushed")
    if not wait_tx(): return "TXstuck@dummy"
    t("dummy moved")
    if not wait_rx(tries=500): return "RXEMPTY"
    v = rx(); t("RX read")
    return "0x%02X" % v

def vB_stop_delay():
    """vA but delay 10ms after STOP before RX check"""
    t("init")
    push((DEV << 1) | START); go()
    if not wait_tx(): return "stuck@addrW"
    push(REG); go()
    if not wait_tx(): return "stuck@reg"
    push((DEV << 1) | 1 | START); go()
    if not wait_tx(): return "stuck@addrR"
    push(0x00 | STOP); go()
    if not wait_tx(): return "stuck@dummy"
    t("dummy moved")
    time.sleep(0.01)
    t("after 10ms")
    if not wait_rx(tries=500): return "RXEMPTY"
    v = rx(); t("RX read")
    return "0x%02X" % v

def vC_dummy_ff():
    """vA with dummy=0xFF"""
    t("init")
    push((DEV << 1) | START); go()
    if not wait_tx(): return "stuck@addrW"
    push(REG); go()
    if not wait_tx(): return "stuck@reg"
    push((DEV << 1) | 1 | START); go()
    if not wait_tx(): return "stuck@addrR"
    push(0xFF | STOP); go()
    if not wait_tx(): return "stuck@dummy"
    if not wait_rx(tries=500): return "RXEMPTY"
    return "0x%02X" % rx()

def vD_two_dummy():
    """2 dummy clocks: first no STOP, second with STOP, then read RX twice"""
    t("init")
    push((DEV << 1) | START); go()
    if not wait_tx(): return "stuck@addrW"
    push(REG); go()
    if not wait_tx(): return "stuck@reg"
    push((DEV << 1) | 1 | START); go()
    if not wait_tx(): return "stuck@addrR"
    push(0x00); go()                      # dummy 1, no STOP
    if not wait_tx(): return "stuck@dummy1"
    t("dummy1 moved")
    if not wait_rx(tries=200): t("no rx yet after dummy1")
    push(0x00 | STOP); go()               # dummy 2, STOP
    if not wait_tx(): return "stuck@dummy2"
    t("dummy2 moved")
    if not wait_rx(tries=500): return "RXEMPTY"
    v1 = rx(); t("RX1 read")
    v2 = rx(); t("RX2 read")
    return "0x%02X/0x%02X" % (v1, v2)

def vE_no_dummy():
    """addrR then NO dummy - wait RX directly (auto-clock?)"""
    t("init")
    push((DEV << 1) | START); go()
    if not wait_tx(): return "stuck@addrW"
    push(REG); go()
    if not wait_tx(): return "stuck@reg"
    push((DEV << 1) | 1 | START); go()
    if not wait_tx(): return "stuck@addrR"
    t("addrR moved, no dummy")
    if not wait_rx(tries=500): return "RXEMPTY"
    return "0x%02X" % rx()

def vF_single_msg():
    """1-msg read: addrR, dummy|STOP (no regptr prewrite)"""
    t("init")
    push((DEV << 1) | 1 | START); go()
    if not wait_tx(): return "stuck@addrR"
    t("addrR moved")
    push(0x00 | STOP); go()
    if not wait_tx(): return "stuck@dummy"
    if not wait_rx(tries=500): return "RXEMPTY"
    return "0x%02X" % rx()

def vG_rxl_3f():
    """vA but RX_LEVEL=0x3F first"""
    wr32(fd, B + RXL, 0x3F); t("RXL=0x3F")
    return vA_dummy_stop()

def vH_dummy_nostop_then_stop():
    """dummy no STOP, then separate STOP-only write"""
    t("init")
    push((DEV << 1) | START); go()
    if not wait_tx(): return "stuck@addrW"
    push(REG); go()
    if not wait_tx(): return "stuck@reg"
    push((DEV << 1) | 1 | START); go()
    if not wait_tx(): return "stuck@addrR"
    push(0x00); go()
    if not wait_tx(): return "stuck@dummy"
    t("dummy moved, no STOP")
    if not wait_rx(tries=200): t("no rx yet")
    push(STOP); go()                      # pure STOP
    if not wait_tx(): return "stuck@stop"
    t("STOP moved")
    if not wait_rx(tries=500): return "RXEMPTY"
    return "0x%02X" % rx()

def vI_txs():
    """vA but push dummy via TXS_FIFO (0x04) instead"""
    t("init")
    push((DEV << 1) | START); go()
    if not wait_tx(): return "stuck@addrW"
    push(REG); go()
    if not wait_tx(): return "stuck@reg"
    push((DEV << 1) | 1 | START); go()
    if not wait_tx(): return "stuck@addrR"
    wr32(fd, B + 0x04, 0x00 | STOP); t("dummy via TXS_FIFO")
    time.sleep(0.02)
    t("after 20ms")
    if not wait_rx(tries=500): return "RXEMPTY"
    return "0x%02X" % rx()

variant("A: dummy0x00|STOP + RX", vA_dummy_stop)
variant("B: +10ms delay", vB_stop_delay)
variant("C: dummy0xFF|STOP", vC_dummy_ff)
variant("D: 2 dummies", vD_two_dummy)
variant("E: no dummy, wait RX", vE_no_dummy)
variant("F: 1-msg read (no regptr)", vF_single_msg)
variant("G: RX_LEVEL=0x3F", vG_rxl_3f)
variant("H: dummy noSTOP + pure STOP", vH_dummy_nostop_then_stop)
variant("I: dummy via TXS_FIFO", vI_txs)

os.close(fd)
print("\nDone.")
