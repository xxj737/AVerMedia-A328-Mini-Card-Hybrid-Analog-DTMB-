#!/usr/bin/env python3
import subprocess, time
BUS=1; A=0x21
def w(r,v): subprocess.run(['i2cset','-y',str(BUS),f'{A:#x}',f'{r:#x}',f'{v:#x}'],capture_output=True)
def rd(r):
    x=subprocess.run(['i2cget','-y',str(BUS),f'{A:#x}',f'{r:#x}'],capture_output=True,text=True)
    try: return int(x.stdout.strip(),16)
    except: return None
fw=open('/lib/firmware/lgs8g75.fw','rb').read()
def download():
    w(0xC6,0x40); time.sleep(0.01)
    w(0x3D,0x04); w(0x3D,0x04)
    w(0x39,0x00); w(0x3A,0x00); w(0x38,0x00); w(0x3B,0x00); w(0x38,0x00)
    for i,b in enumerate(fw):
        w(0x38,0x00); w(0x3A,i&0xff); w(0x3B,i>>8); w(0x3C,b)
    w(0x38,0x00)
def srst():
    w(0x02,0x00); time.sleep(0.02); w(0x02,0x01); time.sleep(0.4)
def state(tag):
    v=rd(0x00); print(f'  {tag}: reg0={hex(v) if v is not None else "ERR"}'); return v

print('step1: revive'); srst(); state('reg0')
print('step2: download fw')
download()
print('  reg0 after dl =', hex(rd(0x00)))
print('step3: EXIT download mode (0x39=0x00)')
w(0x39,0x00); time.sleep(0.2)
state('after 0x39=0x00')
print('step4: soft_reset')
srst(); state('after soft_reset')
print('--- register sweep ---')
for r in [0x13,0x34,0x30,0x1f,0x19,0x0c,0x18,0x07,0x02,0xb0,0xb1]:
    v=rd(r); print(f'  reg{r:#x} =', hex(v) if v is not None else None)
