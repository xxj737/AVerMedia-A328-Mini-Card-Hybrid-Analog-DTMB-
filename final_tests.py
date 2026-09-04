#!/usr/bin/env python3
import subprocess, time
BUS=1; A=0x21
def w(r,v): subprocess.run(['i2cset','-y',str(BUS),f'{A:#x}',f'{r:#x}',f'{v:#x}'],capture_output=True)
def rd(r):
    x=subprocess.run(['i2cget','-y',str(BUS),f'{A:#x}',f'{r:#x}'],capture_output=True,text=True)
    try: return int(x.stdout.strip(),16)
    except: return None
fw=open('/lib/firmware/lgs8g75.fw','rb').read()
def download(c6=0x40):
    w(0xC6,c6); time.sleep(0.01)
    w(0x3D,0x04); w(0x3D,0x04)
    w(0x39,0x00); w(0x3A,0x00); w(0x38,0x00); w(0x3B,0x00); w(0x38,0x00)
    for i,b in enumerate(fw):
        w(0x38,0x00); w(0x3A,i&0xff); w(0x3B,i>>8); w(0x3C,b)
    w(0x38,0x00)
def srst():
    w(0x02,0x00); time.sleep(0.02); w(0x02,0x01); time.sleep(0.4)

srst(); print('state reg0 =', hex(rd(0x00)))
print('--- test1: fw download, NO soft_reset, read immediately ---')
download()
for t in [0, 0.5, 2]:
    if t: time.sleep(t)
    print(f'  +{t}s: reg0={hex(rd(0x00)) if rd(0x00) is not None else None} reg13={hex(rd(0x13)) if rd(0x13) is not None else None}')
print('--- test2: write 0x08=0x00 (AFC init safe), read ---')
w(0x08,0x00); time.sleep(0.3)
print(f'  reg0={hex(rd(0x00)) if rd(0x00) is not None else None} reg13={hex(rd(0x13)) if rd(0x13) is not None else None}')
print('--- test3: soft_reset then immediate read ---')
srst()
print(f'  reg0={hex(rd(0x00)) if rd(0x00) is not None else None} reg13={hex(rd(0x13)) if rd(0x13) is not None else None}')
print('--- test4: fw download with 0xC6=0x00 ---')
download(c6=0x00); srst()
print(f'  reg0={hex(rd(0x00)) if rd(0x00) is not None else None} reg13={hex(rd(0x13)) if rd(0x13) is not None else None}')
