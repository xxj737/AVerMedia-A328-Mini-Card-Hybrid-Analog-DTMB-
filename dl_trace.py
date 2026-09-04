#!/usr/bin/env python3
"""dl_trace.py - 逐步跟踪 Windows 下载序列中 reg0 的状态变化
回答关键矛盾：0x39=0x00 到底踢不踢出下载模式？
Windows 序列 (AVer7231_x64.sys):
  soft_reset -> reg18 RW -> C6=0x40 -> 3D=0x04 x2 -> 39=0x00
  -> 3A/38/3B/38/38 设地址 -> payload loop -> 38=0x00 -> sleep -> verify
"""
import fcntl, os, time, sys

I2C_SLAVE = 0x0703
BUS = int(sys.argv[1]) if len(sys.argv) > 1 else 1
ADDR = 0x21
FW = "/lib/firmware/lgs8g75.fw"

fd = os.open("/dev/i2c-%d" % BUS, os.O_RDWR)
fcntl.ioctl(fd, I2C_SLAVE, ADDR)

def wr(reg, val, delay=0.0003):
    os.write(fd, bytes([reg, val & 0xFF]))
    time.sleep(delay)

def rd(reg):
    try:
        os.write(fd, bytes([reg]))
        time.sleep(0.0005)
        d = os.read(fd, 1)
        return d[0] if d else None
    except Exception as e:
        return 'ERR'

def state(tag):
    r0 = rd(0x00); r1 = rd(0x01); r2 = rd(0x02)
    r13 = rd(0x13); r18 = rd(0x18)
    def h(v): return '0x%02X' % v if isinstance(v, int) else v
    print('%-28s reg0=%s reg1=%s reg2=%s reg13=%s reg18=%s' % (
        tag, h(r0), h(r1), h(r2), h(r13), h(r18)), flush=True)

print('BUS %d ADDR 0x%02X FW %s' % (BUS, ADDR, FW))
state('initial')

# --- Windows download sequence, step by step ---

# 1. soft reset first
wr(0x02, 0x00, 0.001)   # soft_reset low?
wr(0x02, 0x01, 0.005)   # soft_reset high?
state('after soft_reset')

# 2. reg 0x18 read-back-rewrite
t18 = rd(0x18)
print('  reg18 read = %s' % ('0x%02X' % t18 if isinstance(t18, int) else t18))
if isinstance(t18, int):
    wr(0x18, t18, 0.001)
state('after reg18 RW')

# 3. enter download mode
wr(0xC6, 0x40, 0.005)
state('after C6=0x40')

# 4. 0x3D=0x04 twice
wr(0x3D, 0x04, 0.001)
state('after 3D=0x04 #1')
wr(0x3D, 0x04, 0.001)
state('after 3D=0x04 #2')

# 5. 0x39=0x00  <-- KEY QUESTION
wr(0x39, 0x00, 0.001)
state('after 39=0x00')

# 6. set start address 0
wr(0x3A, 0x00, 0.0005); wr(0x38, 0x00, 0.0005)
wr(0x3B, 0x00, 0.0005); wr(0x38, 0x00, 0.0005)
wr(0x38, 0x00, 0.0005)
state('addr setup done')

# 7. payload loop
fw = open(FW, "rb").read()
print('fw size: %d bytes' % len(fw))
t0 = time.time()
for i, b in enumerate(fw):
    wr(0x38, 0x00, 0)
    wr(0x3A, i & 0xFF, 0)
    wr(0x3B, i >> 8, 0)
    wr(0x3C, b, 0)
wr(0x38, 0x00, 0.001)
print('payload done in %.2fs' % (time.time() - t0))
state('after payload')

# 8. let firmware boot
time.sleep(0.1)
state('after 100ms boot')

# verify: read a few more times
for t in range(5):
    time.sleep(0.2)
    state('verify t+%d' % (t + 1))

os.close(fd)
print('Done.')
