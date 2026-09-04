#!/usr/bin/env python3
"""diag_drv_like.py - replicate the DRIVER's exact I2C read sequence
(which successfully detected TDA18271 after reboot):
  - full hwinit incl. INT_CLR_ENABLE/INT_CLR_STATUS (0xfd8/0xfe8 = 0x1fff)
  - xfer-start empty GO (like saa7231_i2c_xfer)
  - per-byte GO
  - RX poll loop like saa7231_i2c_recv
Read LGS reg0 on I2C0, TDA reg0 on I2C2.  Expect LGS 0xCE/0x04/0xE2,
TDA 0x84 - NOT 0xFF.
"""
import os, struct, time

def rd32(fd, off): return struct.unpack("<I", os.pread(fd, 4, off))[0]
def wr32(fd, off, val): os.write(fd, struct.pack("<II", off, val & 0xFFFFFFFF))

DIAG = "/dev/saa_diag"
fd = os.open(DIAG, os.O_RDWR)
TXE = 1 << 6; RXE = 1 << 4

def hwinit_full(b):
    """exact copy of saa7231_i2c_hwinit() 54MHz/100kHz path"""
    wr32(fd, b + 0x0C, 0x00cc); time.sleep(0.005)
    wr32(fd, b + 0x0C, 0x00c1); time.sleep(0.005)
    for _ in range(100):
        if rd32(fd, b + 0x0C) == 0xc0: break
        time.sleep(0.001)
    wr32(fd, b + 0x10, 0x00d0)   # CLKDIV_H
    wr32(fd, b + 0x14, 0x010e)   # CLKDIV_L
    wr32(fd, b + 0x28, 0x007c)   # SDA_HOLD
    wr32(fd, b + 0xfd8, 0x1fff)  # INT_CLR_ENABLE
    wr32(fd, b + 0xfe8, 0x1fff)  # INT_CLR_STATUS

def go(b):
    c = rd32(fd, b + 0x0C)
    wr32(fd, b + 0x0C, c | 0x01)

def send_byte(b, v):
    """send(): wait TXE, push, GO (per-byte), wait TXE"""
    for _ in range(10000):
        if rd32(fd, b + 0x08) & TXE: break
        time.sleep(0.00001)
    wr32(fd, b + 0x00, v)
    go(b)
    for _ in range(10000):
        if rd32(fd, b + 0x08) & TXE: break
        time.sleep(0.00001)
    return True

def recv_byte(b):
    """recv(): wait !(RX_BLOCK|RX_EMPTY), read RX_FIFO"""
    for _ in range(10000):
        s = rd32(fd, b + 0x08)
        if not (s & 0x500): break
        time.sleep(0.00001)
    if rd32(fd, b + 0x08) & 0x500:
        return None
    return rd32(fd, b + 0x00) & 0xFF

def read_reg(b, dev, reg):
    """2-msg read like xfer: addrW, regptr, Sr+R, dummy|STOP, then recv"""
    hwinit_full(b)
    # xfer-start empty GO (harmless, FIFO empty) - like saa7231_i2c_xfer
    go(b)
    send_byte(b, (dev << 1) | 0x100)          # addrW | START
    send_byte(b, reg)                          # reg pointer
    send_byte(b, (dev << 1) | 1 | 0x100)      # addrR | Sr
    send_byte(b, 0x00 | 0x200)                 # dummy | STOP
    return recv_byte(b)

def read_reg1(b, dev):
    """1-msg pure read: addrR|START, dummy|STOP, recv"""
    hwinit_full(b)
    go(b)
    send_byte(b, (dev << 1) | 1 | 0x100)
    send_byte(b, 0x00 | 0x200)
    return recv_byte(b)

def sts(b):
    s = rd32(fd, b + 0x08)
    return "0x%03X[%s%s%s%s]" % (s & 0xFFF,
        "TXE" if s & TXE else "tx!", "RXE" if s & RXE else "rx!",
        "SCL1" if s & 4 else "SCL0", "SDA1" if s & 8 else "SDA0")

print("== driver-like read on correct buses (post-reboot) ==")
for b, name in ((0x109000, "I2C0"), (0x10b000, "I2C2")):
    print("\n-- %s (%s)" % (name, hex(b)))
    print("   status before: %s" % sts(b))
    print("   LGS@0x21 reg0 2msg:", read_reg(b, 0x21, 0x00))
    print("   TDA@0x60 reg0 2msg:", read_reg(b, 0x60, 0x00))
    print("   LGS@0x21 reg0 1msg:", read_reg1(b, 0x21))
    print("   TDA@0x60 reg0 1msg:", read_reg1(b, 0x60))
    print("   status after : %s" % sts(b))

print("\n-- also I2C1/I2C3 for completeness --")
for b, name in ((0x10a000, "I2C1"), (0x10c000, "I2C3")):
    print("%s: LGS=%s TDA=%s" % (name,
        read_reg(b, 0x21, 0x00), read_reg(b, 0x60, 0x00)))

os.close(fd)
print("\nDone.")
