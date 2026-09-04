#!/usr/bin/env python3
import subprocess, time
BUS=1; A=0x21
RW='/sys/bus/pci/devices/0000:03:00.0/reg_write'
def wr(off,val): subprocess.run(['sh','-c',f'printf "0 {off} {val}\n" > {RW}'],capture_output=True)
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

# 1. revive
srst()
print('revive reg0 =', hex(rd(0x00)) if rd(0x00) is not None else None)
# 2. GPIO5 reset pulse
print('GPIO5 LOW'); wr('0x105018','0x20'); time.sleep(0.3)
print('  during reset reg0 =', hex(rd(0x00)) if rd(0x00) is not None else None)
print('GPIO5 HIGH'); wr('0x105014','0x20'); time.sleep(0.3)
print('  after release reg0 =', hex(rd(0x00)) if rd(0x00) is not None else None)
# 3. download fw (no reg8 test!)
print('download fw'); download()
print('  after dl reg0 =', hex(rd(0x00)) if rd(0x00) is not None else None)
# 4. soft reset
srst()
print('after soft_reset reg0 =', hex(rd(0x00)) if rd(0x00) is not None else None)
for r in [0x13,0x34,0x30,0x1f,0x19,0x0c,0x18]:
    v=rd(r)
    print(f'  reg{r:#x} =', hex(v) if v is not None else None)
