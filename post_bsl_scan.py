#!/usr/bin/env python3
import subprocess, time
BUS=1; A=0x21
def w(r,v): subprocess.run(['i2cset','-y',str(BUS),f'{A:#x}',f'{r:#x}',f'{v:#x}'],capture_output=True)
def rd(r):
    x=subprocess.run(['i2cget','-y',str(BUS),f'{A:#x}',f'{r:#x}'],capture_output=True,text=True)
    try: return int(x.stdout.strip(),16)
    except: return None
# get to 0x04 state
w(0x02,0x00); time.sleep(0.05); w(0x02,0x01); time.sleep(0.4)
print('state reg0 =', hex(rd(0x00)))
# full scan
nz = []
for reg in range(0, 256):
    v = rd(reg)
    if v is not None and v != 0xFF:
        nz.append((reg, v))
print(f'non-0xFF regs ({len(nz)}):', ['%02X=%02X' % (r,v) for r,v in nz])
# alternate read protocols
print('--- alt protocol tests (state reg0=%s) ---' % hex(rd(0x00)))
# proto A: write addr into reg0 then read reg0
for target in [0x13, 0x34]:
    w(0x00, target); time.sleep(0.1)
    v = rd(0x00)
    print(f'  protoA: wrote reg0={target:#x}, read reg0={hex(v) if v is not None else None}')
# proto B: enable gate (0x01=0xE0) then read 0x13
w(0x01, 0xE0); time.sleep(0.1)
print('  after gate on, reg0 =', hex(rd(0x00)) if rd(0x00) is not None else None)
print('  gate on reg13 =', hex(rd(0x13)) if rd(0x13) is not None else None)
w(0x01, 0x60); time.sleep(0.1)
print('  after gate off, reg0 =', hex(rd(0x00)) if rd(0x00) is not None else None)
