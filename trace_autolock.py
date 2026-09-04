#!/usr/bin/env python3
import subprocess, time
BUS=1; A=0x21
def w(r,v): subprocess.run(['i2cset','-y',str(BUS),f'{A:#x}',f'{r:#x}',f'{v:#x}'],capture_output=True)
def rd(r):
    x=subprocess.run(['i2cget','-y',str(BUS),f'{A:#x}',f'{r:#x}'],capture_output=True,text=True)
    try: return int(x.stdout.strip(),16)
    except: return None
def srst():
    w(0x02,0x00); time.sleep(0.02); w(0x02,0x01); time.sleep(0.4)
def state(tag):
    v = rd(0x00)
    print(f'  {tag}: reg0={hex(v) if v is not None else "ERR"}')
    return v

print('=== baseline ===')
srst(); state('after soft_reset (0x04 expected)')

print('=== simulate init: set_mpeg_mode/set_if_freq/set_ad_mode (already done in driver, skip) ===')

print('=== auto_detect: autolock_gi (read 0x0C/0x18, write GI) ===')
t1 = rd(0x0C) or 0xFF; t2 = rd(0x18) or 0xFF
print(f'  read 0x0C={t1:#x} 0x18={t2:#x}')
w(0x0C, (t1 & ~0x60) | 0x02); state('write 0x0C GI')
w(0x18, t2 & 0xFE); state('write 0x18')
print('  wait_ca_lock: read 0x13 x3')
for i in range(3): time.sleep(0.05); v=rd(0x13); print(f'    0x13={hex(v) if v is not None else "ERR"}')
state('after wait_ca_lock')

print('=== auto_detect: write 0x19 detected_param ===')
t19 = rd(0x19) or 0xFF
w(0x19, (t19 & 0x81) | (0x02 << 1)); state('write 0x19')
srst(); state('soft_reset (auto_detect end)')

print('=== set_mode_manual: write 0x0C clear bit7 ===')
t = rd(0x0C) or 0xFF
w(0x0C, t & ~0x80); state('write 0x0C &~0x80')
t = rd(0x0C) or 0xFF; t2 = rd(0x19) or 0xFF
print(f'  read 0x0C={t:#x} 0x19={t2:#x}')
cond = ((t & 0x03) == 0x01) and (t2 & 0x01)
print(f'  branch condition: {"if" if cond else "else"}')
if cond:
    w(0x6E, 0x05); state('write 0x6E=0x05')
    w(0x39, 0x02); state('write 0x39=0x02')
    w(0x39, 0x03); state('write 0x39=0x03')
    w(0x3D, 0x05); state('write 0x3D=0x05')
    w(0x3E, 0x28); state('write 0x3E=0x28')
    w(0x53, 0x80); state('write 0x53=0x80')
else:
    w(0x6E, 0x3F); state('write 0x6E=0x3F')
    w(0x39, 0x00); state('write 0x39=0x00')
    w(0x3D, 0x04); state('write 0x3D=0x04')
srst(); state('soft_reset (set_mode_manual end)')
