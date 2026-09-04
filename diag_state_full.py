#!/usr/bin/env python3
"""综合状态检查：LGS/TDA 寄存器 + DVB 前端 + 尝试调谐"""
import os, struct, time, sys

def rd8(fd, off):
    return struct.unpack('<I', os.pread(fd, 4, off))[0]

def rd(fd, off):
    return struct.unpack('<I', os.pread(fd, 4, off))[0]

def wr(fd, off, val):
    os.write(fd, struct.pack('<II', off, val & 0xFFFFFFFF))

print('=' * 60)
print('PART 1: LGS/TDA registers via i2c-dev')
print('=' * 60)
# card0: i2c-1..4 = I2C0..3 ; card1: i2c-5..8 = I2C0..3
for (bus, name) in [(1, 'card0 I2C0'), (2, 'card0 I2C1'), (3, 'card0 I2C2'), (4, 'card0 I2C3'),
                    (5, 'card1 I2C0'), (6, 'card1 I2C1'), (7, 'card1 I2C2'), (8, 'card1 I2C3')]:
    try:
        with open('/sys/class/i2c-dev/i2c-%d/device/name' % bus) as f:
            pass
    except Exception:
        pass

# Use i2cget equivalent via python (ioctl)
import fcntl
I2C_SLAVE = 0x0703

def i2c_get(bus, addr, reg, nretry=2):
    """I2C read: write reg pointer, then read 1 byte"""
    import io
    for attempt in range(nretry):
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
            if attempt == nretry - 1:
                return 'ERR:%s' % str(e)[:30]
    return None

def i2c_set(bus, addr, reg, val):
    try:
        fd = os.open('/dev/i2c-%d' % bus, os.O_RDWR)
        fcntl.ioctl(fd, I2C_SLAVE, addr)
        os.write(fd, bytes([reg, val]))
        os.close(fd)
        return 'OK'
    except Exception as e:
        return 'ERR:%s' % str(e)[:30]

print('\n--- LGS8G75 @ 0x21 probe on all buses ---')
for bus in [1, 2, 3, 4, 5, 6, 7, 8]:
    r = i2c_get(bus, 0x21, 0x00)
    print('  bus%d: reg0 = %s' % (bus, '0x%02X' % r if isinstance(r, int) else r))

print('\n--- TDA18271 @ 0x60 probe on all buses ---')
for bus in [1, 2, 3, 4, 5, 6, 7, 8]:
    r = i2c_get(bus, 0x60, 0x00)
    print('  bus%d: reg0 = %s' % (bus, '0x%02X' % r if isinstance(r, int) else r))

print('\n--- LGS status regs on known-good bus (card0 I2C0=bus1, card1 I2C0=bus5) ---')
for bus in [1, 5]:
    print('  bus%d:' % bus)
    for r in [0x00, 0x01, 0x02, 0x0c, 0x13, 0x18, 0x1f]:
        v = i2c_get(bus, 0x21, r)
        print('    reg0x%02X = %s' % (r, '0x%02X' % v if isinstance(v, int) else v))

print('\n--- TDA status regs (bus3=card0 I2C2, bus7=card1 I2C2) ---')
for bus in [3, 7]:
    print('  bus%d:' % bus)
    for r in [0x00, 0x01, 0x02]:
        v = i2c_get(bus, 0x60, r)
        print('    reg0x%02X = %s' % (r, '0x%02X' % v if isinstance(v, int) else v))

print('\n' + '=' * 60)
print('PART 2: DVB frontends')
print('=' * 60)
try:
    for d in sorted(os.listdir('/dev/dvb')):
        path = '/dev/dvb/' + d
        print('  %s: %s' % (d, os.listdir(path)))
except Exception as e:
    print('  ERR: %s' % e)

# DVB frontend ioctl: FE_GET_INFO etc.
import subprocess

print('\n--- try dvbv5 tools if available ---')
for tool in ['dvbv5-zap', 'dvbv5-scan', 'dvb-fe-tool']:
    r = subprocess.run(['which', tool], capture_output=True, text=True)
    if r.returncode == 0:
        print('  %s: %s' % (tool, r.stdout.strip()))

print('\n--- frontend status via sysfs ---')
try:
    for fe in sorted(os.listdir('/sys/class/dvb')):
        if 'frontend' not in fe:
            continue
        fe_path = '/sys/class/dvb/' + fe
        try:
            status = open(fe_path + '/status').read().strip()
            print('  %s: status=%s' % (fe, status))
        except Exception as e:
            print('  %s: no status (%s)' % (fe, e))
except Exception as e:
    print('  ERR: %s' % e)

print('\nDone.')
