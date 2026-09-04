#!/usr/bin/env python3
"""diag_gpio_power.py - does GPIO0-7 power control decide which bus ACKs?

saa7231_drv.c frontend_enable comment: "pulling them low kills the TDA18271
on i2c-2 (0x60 no longer ACKs), restoring them high revives it."

So chips may be dark (no power) -> NACK everywhere.  Probe I2C0/I2C2/I2C3
before and after forcing GPIO0-7 HIGH via 0x105014(MODE0_SET)=0xFF.

Also read TXS_FIFO (+0x04) after an addr byte: TXS is likely a per-byte
ACK/status FIFO - I2C3 shows TXS not-empty (STATUS bit8=0) while others
are empty, and its INT_STATUS has bit12 pending.
"""
import os, struct, time

def rd32(fd, off): return struct.unpack("<I", os.pread(fd, 4, off))[0]
def wr32(fd, off, val): os.write(fd, struct.pack("<II", off, val & 0xFFFFFFFF))

DIAG = "/dev/saa_diag"
fd = os.open(DIAG, os.O_RDWR)
GPIO = 0x105000
TX = 0x00; TXS = 0x04; STS = 0x08; CTL = 0x0C
TXE = 1 << 6; RXE = 1 << 4; TXSE = 1 << 8

def st_raw(b): return rd32(fd, b + STS)
def go(b):
    c = rd32(fd, b + CTL)
    wr32(fd, b + CTL, c | 0x01)
def push(b, v): wr32(fd, b + TX, v)
def hwinit(b):
    wr32(fd, b + CTL, 0x00cc); time.sleep(0.005)
    wr32(fd, b + CTL, 0x00c1); time.sleep(0.005)
    for _ in range(100):
        if rd32(fd, b + CTL) == 0xc0: break
        time.sleep(0.001)

def fmt(b):
    s = rd32(fd, b + STS)
    return "STS=0x%03X %s%s%s%s%s%s%s%s TXS=0x%08X" % (
        s & 0xFFF,
        "TXE" if s & TXE else "tx!", "RXE" if s & RXE else "rx!",
        "TXSE" if s & TXSE else "txs!",
        "SCL1" if s & 4 else "SCL0", "SDA1" if s & 8 else "SDA0",
        "ACT" if s & 2 else "", "MST" if s & 1 else "",
        "INT" if rd32(fd, b + 0xfe0) else "",
        rd32(fd, b + TXS))

def ack_probe(b, dev):
    """push addr|START, GO, tight SDA sample + TXS_FIFO read"""
    hwinit(b)
    push(b, (dev << 1) | 0x100)   # addr | START
    go(b)
    lows = highs = 0
    t0 = time.time()
    while time.time() - t0 < 0.004:
        s = rd32(fd, b + STS)
        if s & 0x8: highs += 1
        else: lows += 1
    # after sampling, read TXS FIFO (ACK status?) and INT_STATUS
    txs = rd32(fd, b + TXS)
    ints = rd32(fd, b + 0xfe0)
    verdict = "ACK?" if lows > 50 else ("NACK" if highs > lows else "??")
    return verdict, lows, highs, txs, ints

def gpio_state():
    return (rd32(fd, GPIO + 0x00), rd32(fd, GPIO + 0x10),
            rd32(fd, GPIO + 0x14), rd32(fd, GPIO + 0x18),
            rd32(fd, GPIO + 0x20), rd32(fd, GPIO + 0x24),
            rd32(fd, GPIO + 0x28))

print("GPIO regs PINS/M0/M0SET/M0RST/M1/M1SET/M1RST =", 
      " ".join("0x%08X" % v for v in gpio_state()))
print()

for phase, pre in (("BEFORE GPIO HIGH", True), ("AFTER  GPIO HIGH", False)):
    if pre:
        print("--- %s ---" % phase)
        for b, name in ((0x109000, "I2C0"), (0x10a000, "I2C1"),
                        (0x10b000, "I2C2"), (0x10c000, "I2C3")):
            print("  %-5s %s" % (name, fmt(b)))
        print()
    else:
        wr32(fd, GPIO + 0x14, 0xFF)   # MODE0_SET 0xFF -> GPIO0-7 HIGH
        time.sleep(0.2)
        print("--- %s (MODE0_SET=0xFF written) ---" % phase)
        print("GPIO regs now:", " ".join("0x%08X" % v for v in gpio_state()))
        print()
        for b, name in ((0x109000, "I2C0"), (0x10a000, "I2C1"),
                        (0x10b000, "I2C2"), (0x10c000, "I2C3")):
            print("  %-5s %s" % (name, fmt(b)))
        print()

print("== ACK probe with GPIO HIGH (0xFF) ==")
for b, name in ((0x109000, "I2C0"), (0x10a000, "I2C1"),
                (0x10b000, "I2C2"), (0x10c000, "I2C3")):
    for dev, dname in ((0x21, "LGS"), (0x60, "TDA")):
        v, lo, hi, txs, ints = ack_probe(b, dev)
        print("  %-5s %-4s -> %-5s (lows=%d highs=%d TXS=0x%08X INT=0x%X) %s" %
              (name, dname, v, lo, hi, txs, ints, fmt(b)))
        time.sleep(0.02)

os.close(fd)
print("\nDone.")
