#!/usr/bin/env python3
import subprocess, time

BUS = 1
ADDR = 0x21
FW = '/lib/firmware/lgs8g75.fw'

def w(reg, val):
    r = subprocess.run(['i2ctransfer','-y',str(BUS),f'w2@{ADDR:#x}',f'{reg:#x}',f'{val:#x}'], capture_output=True, text=True)
    if r.returncode != 0:
        print(f'  WRITE FAIL reg={reg:#x} val={val:#x}: {r.stderr.strip()}')
        return False
    return True

def rd(reg):
    r = subprocess.run(['i2cget','-y',str(BUS),f'{ADDR:#x}',f'{reg:#x}'], capture_output=True, text=True)
    try:
        return int(r.stdout.strip(), 16)
    except Exception:
        return None

fw = open(FW,'rb').read()
print(f'firmware: {len(fw)} bytes')

w(0xC6,0x40); w(0x3D,0x04); w(0x39,0x00)
w(0x3A,0x00); w(0x38,0x00); w(0x3B,0x00); w(0x38,0x00)
for i,b in enumerate(fw):
    w(0x38,0x00); w(0x3A,i&0xff); w(0x3B,i>>8); w(0x3C,b)
w(0x38,0x00)
print('firmware written')

w(0x02,0x00); time.sleep(0.01)
w(0x02,0x01); time.sleep(0.3)
print(f'after soft_reset: reg0 = {rd(0x00)} (expect 0xce)')
print(f'reg2 = {rd(0x02)}')

w(0x08,0xAA); time.sleep(0.1)
print(f'reg8 = {rd(0x08)} (expect 0xaa if RW alive)')
w(0x08,0x2D)
