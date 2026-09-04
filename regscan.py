#!/usr/bin/env python3
import subprocess

BUS = 1
ADDR = 0x21

def rd(reg):
    r = subprocess.run(['i2cget','-y',str(BUS),f'{ADDR:#x}',f'{reg:#x}'], capture_output=True, text=True)
    try:
        return int(r.stdout.strip(), 16)
    except Exception:
        return None

# activate first
subprocess.run(['i2cset','-y',str(BUS),f'{ADDR:#x}','0x02','0x00'])
subprocess.run(['i2cset','-y',str(BUS),f'{ADDR:#x}','0x02','0x01'])
import time; time.sleep(0.4)

nonzero = []
for reg in range(0, 256):
    v = rd(reg)
    if v is not None and v != 0xFF:
        nonzero.append((reg, v))
print(f'non-0xFF registers ({len(nonzero)}):')
for reg, v in nonzero:
    print(f'  0x{reg:02X} = 0x{v:02X}')
