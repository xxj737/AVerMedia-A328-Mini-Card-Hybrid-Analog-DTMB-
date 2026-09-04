#!/usr/bin/env python3
"""调谐期间监控 LGS8G75 状态寄存器，判断 8051 是否真在运行"""
import os, struct, time, subprocess, signal, fcntl, sys

# --- i2c helpers (bus1 = card0 I2C0 = LGS) ---
I2C_SLAVE = 0x0703

def i2c_get(bus, addr, reg, retries=1):
    for attempt in range(retries):
        try:
            fd = os.open('/dev/i2c-%d' % bus, os.O_RDWR)
            fcntl.ioctl(fd, I2C_SLAVE, addr)
            os.write(fd, bytes([reg]))
            data = os.read(fd, 1)
            os.close(fd)
            return data[0] if data else None
        except Exception as e:
            try:
                os.close(fd)
            except Exception:
                pass
            if attempt == retries - 1:
                return None
    return None

def i2c_set(bus, addr, reg, val):
    try:
        fd = os.open('/dev/i2c-%d' % bus, os.O_RDWR)
        fcntl.ioctl(fd, I2C_SLAVE, addr)
        os.write(fd, bytes([reg, val]))
        os.close(fd)
        return True
    except Exception:
        return False

# --- LGS register map per driver:
# reg0x13 bit7 = lock (is_locked)
# reg0x1f bit7/6 = autodetect finished
# reg0x18 = GI/CPN control
# reg0x0C = mode control
# reg0x19 = detected params
# reg0x3F/3E = AGC levels

LGS_REGS = [0x00, 0x0C, 0x13, 0x18, 0x19, 0x1F, 0x3E, 0x3F]
REG_NAMES = {0x00:'reg0', 0x0C:'mode', 0x13:'lock', 0x18:'GI/CPN',
             0x19:'params', 0x1F:'autoD', 0x3E:'AGC1', 0x3F:'AGC0'}

def snapshot(bus, tag):
    vals = {}
    for r in LGS_REGS:
        v = i2c_get(bus, 0x21, r)
        vals[r] = v
    line = '%s  ' % tag
    for r in LGS_REGS:
        v = vals[r]
        s = '0x%02X' % v if v is not None else 'ERR'
        line += '%s=%s ' % (REG_NAMES[r], s)
    print(line, flush=True)
    return vals

bus = 1  # card0 I2C0

print('=== Phase 0: pre-tune snapshot ===')
snapshot(bus, 'pre-tune ')

# --- start dvbv5-zap in background (tune 674MHz) ---
print('=== starting dvbv5-zap tune (674MHz, background) ===')
zap = subprocess.Popen(['dvbv5-zap', '-c', '/tmp/dtmb_674.dvbv5', '-a', '0',
                        '-f', '0', '-t', '30', '-o', '/tmp/ts_mon.bin', 'DTMB'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    # monitor during first 12 seconds
    start = time.time()
    phase = 0
    while time.time() - start < 12:
        t = time.time() - start
        if t < 3:
            tag = 't=%.1fs init ' % t
        elif t < 7:
            tag = 't=%.1fs search' % t
        else:
            tag = 't=%.1fs locked?' % t
        snapshot(bus, tag)
        time.sleep(1.0)
finally:
    zap.send_signal(signal.SIGTERM)
    try:
        zap.wait(timeout=5)
    except Exception:
        zap.kill()

print('=== zap output (first 15 lines) ===')
out = zap.stdout.read() if zap.stdout else ''
for line in out.splitlines()[:15]:
    print('  ' + line)

print('=== TS bytes captured ===')
try:
    sz = os.path.getsize('/tmp/ts_mon.bin')
    print('  /tmp/ts_mon.bin = %d bytes' % sz)
    if sz > 0:
        with open('/tmp/ts_mon.bin', 'rb') as f:
            data = f.read(min(sz, 4096))
        syncs = sum(1 for i in range(len(data) - 1) if data[i] == 0x47)
        print('  0x47 sync bytes in first 4KB: %d' % syncs)
except Exception as e:
    print('  ERR: %s' % e)

print('=== Phase 1: post-tune snapshot ===')
snapshot(bus, 'post-tune')
print('Done.')
