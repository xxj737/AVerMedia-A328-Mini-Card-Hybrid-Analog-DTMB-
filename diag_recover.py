#!/usr/bin/env python3
"""diag_recover.py - after days of hammering, restore LGS/TDA and probe ACK
via TXS_FIFO (+0x04), which may hold per-byte ACK status.

Steps:
  1. GPIO5 pulse (LGS reset) to recover the demod
  2. On I2C0 (LGS 0x21) and I2C2 (TDA 0x60): full write/read transaction
     with TXS_FIFO + INT_STATUS read after EVERY byte
  3. Watch SCL/SDA/BUS_ACTIVE per step
"""
import os, struct, time

def rd32(fd, off): return struct.unpack("<I", os.pread(fd, 4, off))[0]
def wr32(fd, off, val): os.write(fd, struct.pack("<II", off, val & 0xFFFFFFFF))

DIAG = "/dev/saa_diag"
fd = os.open(DIAG, os.O_RDWR)
GPIO = 0x105000
TXS = 0x04; STS = 0x08; CTL = 0x0C
TXE = 1 << 6; RXE = 1 << 4; TXSE = 1 << 8

def st(b):
    s = rd32(fd, b + STS)
    return "0x%03X[%s%s%s%s%s%s%s]" % (s & 0xFFF,
        "TXE" if s & TXE else "tx!", "RXE" if s & RXE else "rx!",
        "TXSE" if s & TXSE else "txs!", "SCL1" if s & 4 else "SCL0",
        "SDA1" if s & 8 else "SDA0", "ACT" if s & 2 else "",
        "INT!" if rd32(fd, b + 0xfe0) else "")

def go(b):
    c = rd32(fd, b + CTL)
    wr32(fd, b + CTL, c | 0x01)
def push(b, v): wr32(fd, b, v)
def wait_tx(b, tries=200, d=0.003):
    for _ in range(tries):
        if rd32(fd, b + STS) & TXE: return True
        time.sleep(d)
    return False

def hwinit(b):
    wr32(fd, b + CTL, 0x00cc); time.sleep(0.005)
    wr32(fd, b + CTL, 0x00c1); time.sleep(0.005)
    for _ in range(100):
        if rd32(fd, b + CTL) == 0xc0: break
        time.sleep(0.001)

def step(b, tag, v):
    push(b, v); go(b)
    ok = wait_tx(b)
    txs = rd32(fd, b + TXS)
    ints = rd32(fd, b + 0xfe0)
    print("    %-16s txmoved=%s TXS=0x%08X INT=0x%X %s" %
          (tag, ok, txs, ints, st(b)))
    return ok

def full_tx(b, dev):
    """write reg0x00=0x40 to dev, TXS after each byte"""
    print("  -- write 0x00=0x40 to dev 0x%02X on module 0x%06X" % (dev, b))
    step(b, "addrW", (dev << 1) | 0x100)
    step(b, "reg 0x00", 0x00)
    step(b, "val 0x40|STOP", 0x40 | 0x200)

def full_read(b, dev):
    """2-msg read reg0: W ptr, Sr+R, dummy|STOP; TXS after each byte"""
    print("  -- read reg0 of dev 0x%02X on module 0x%06X" % (dev, b))
    step(b, "addrW", (dev << 1) | 0x100)
    step(b, "reg 0x00", 0x00)
    step(b, "addrR|Sr", (dev << 1) | 1 | 0x100)
    step(b, "dummy|STOP", 0x00 | 0x200)
    time.sleep(0.01)
    s = rd32(fd, b + STS)
    print("    after STOP: RXE=%d -> %s" % (1 if s & RXE else 0, st(b)))
    if not (s & RXE):
        v = rd32(fd, b) & 0xFF
        print("    RX data = 0x%02X" % v)
        return v
    else:
        print("    RXEMPTY (no data)")
        return None

print("== recover + TXS-FIFO ACK probe ==")
print("GPIO MODE0_SET/MODE0_RESET = 0x%08X/0x%08X" %
      (rd32(fd, GPIO + 0x14), rd32(fd, GPIO + 0x18)))

# 1) GPIO5 pulse: reset LGS8G75
print("\n[1] GPIO5 pulse (LGS reset assert/release)")
wr32(fd, GPIO + 0x18, 0x20)   # MODE0_RESET bit5 -> GPIO5 low
time.sleep(0.3)
wr32(fd, GPIO + 0x14, 0x20)   # MODE0_SET bit5 -> GPIO5 high
time.sleep(0.5)
print("    done. GPIO now: SET=0x%08X RST=0x%08X" %
      (rd32(fd, GPIO + 0x14), rd32(fd, GPIO + 0x18)))

# also reset TDA via GPIO4 if wired
wr32(fd, GPIO + 0x18, 0x10)   # GPIO4 low
time.sleep(0.2)
wr32(fd, GPIO + 0x14, 0x10)   # GPIO4 high
time.sleep(0.3)
print("    GPIO4 pulse done")

# 2) probe I2C0 (LGS) and I2C2 (TDA) with full transactions
print("\n[2] I2C0 (0x109000) - LGS 0x21")
hwinit(0x109000)
print("    hwinit:", st(0x109000))
full_tx(0x109000, 0x21)
hwinit(0x109000)
full_read(0x109000, 0x21)

print("\n[3] I2C2 (0x10b000) - TDA 0x60")
hwinit(0x10b000)
print("    hwinit:", st(0x10b000))
full_tx(0x10b000, 0x60)
hwinit(0x10b000)
full_read(0x10b000, 0x60)

print("\n[4] I2C3 (0x10c000) status after resets")
hwinit(0x10c000)
print("    hwinit:", st(0x10c000))
for dev, dname in ((0x21, "LGS"), (0x60, "TDA")):
    print("  -- probe %s on I2C3" % dname)
    step(0x10c000, "addrW", (dev << 1) | 0x100)
    step(0x10c000, "STOP release", 0x200)
    hwinit(0x10c000)

os.close(fd)
print("\nDone.")
