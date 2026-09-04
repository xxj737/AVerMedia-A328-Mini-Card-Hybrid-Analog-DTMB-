#!/usr/bin/env python3
"""probe SAA7231 I2C engine registers via PCI BAR0 resource, read-only first"""
import os, struct, sys

BAR0 = "/sys/bus/pci/devices/0000:04:00.0/resource0"
fd = os.open(BAR0, os.O_RDWR)

def rd32_pre(off):
    try:
        d = os.pread(fd, 4, off)
        return struct.unpack("<I", d)[0]
    except Exception:
        return None

mm = None
def rd32(off):
    global mm
    if mm is not None:
        return struct.unpack("<I", mm[off:off+4])[0]
    v = rd32_pre(off)
    if v is not None and v != 0xFFFFFFFF:
        return v
    try:
        import mmap as _mmap
        mm = _mmap.mmap(fd, 0x400000, _mmap.MAP_SHARED, _mmap.PROT_READ)
        return struct.unpack("<I", mm[off:off+4])[0]
    except Exception:
        return v

print("=== SAA7231 I2C engine registers (BAR0) ===")
for name, base in (("I2C0(LGS)",0x109000), ("I2C1",0x10a000), ("I2C2(TDA)",0x10b000), ("I2C3",0x10c000)):
    tx = rd32(base+0x00); txs = rd32(base+0x04); sts = rd32(base+0x08); ctl = rd32(base+0x0C)
    if tx is None or tx == 0xFFFFFFFF:
        print("%s @0x%06x: <unreadable/FF>" % (name, base))
        continue
    s = (sts or 0) & 0xFFF
    bits = []
    for bit, label in ((0x100,"TXSE"),(0x80,"TXSF"),(0x40,"TXE"),(0x20,"RXF"),(0x10,"RXE"),(0x8,"SDA1"),(0x4,"SCL1"),(0x2,"ACT")):
        bits.append(label if s & bit else label.lower())
    print("%s @0x%06x: TX=0x%02x TXS=0x%08x STS=0x%03x[%s] CTL=0x%x" %
          (name, base, tx & 0xff, txs or 0, s, ",".join(bits), ctl or 0))
print("=== GPIO @0x105000 ===")
gpio = 0x105000
for reg, nm in ((0x10,"DATA"),(0x14,"MODE0_SET"),(0x18,"MODE0_RESET")):
    v = rd32(gpio+reg)
    if v is not None:
        print("  GPIO+0x%02x (%s) = 0x%08x" % (reg, nm, v))
    else:
        print("  GPIO+0x%02x unreadable" % reg)
print("=== SAA7231 CPU signature 0x4000 ===")
sig = rd32(0x4000)
if sig is not None:
    txt = "".join(chr((sig >> (8*i)) & 0xff) for i in range(4))
    print("  0x4000 = 0x%08x (%s)" % (sig, txt))
