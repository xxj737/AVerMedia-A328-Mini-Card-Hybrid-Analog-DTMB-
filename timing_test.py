#!/usr/bin/env python3
import subprocess, time

BUS = 1
ADDR = 0x21
FW = '/lib/firmware/lgs8g75.fw'

def w(reg, val):
    r = subprocess.run(['i2cset','-y',str(BUS),f'{ADDR:#x}',f'{reg:#x}',f'{val:#x}'], capture_output=True, text=True)
    return r.returncode == 0

def rd(reg):
    r = subprocess.run(['i2cget','-y',str(BUS),f'{ADDR:#x}',f'{reg:#x}'], capture_output=True, text=True)
    try:
        return int(r.stdout.strip(), 16)
    except Exception:
        return None

def download():
    fw = open(FW,'rb').read()
    w(0xC6,0x40); w(0x3D,0x04); w(0x39,0x00)
    w(0x3A,0x00); w(0x38,0x00); w(0x3B,0x00); w(0x38,0x00)
    for i,b in enumerate(fw):
        w(0x38,0x00); w(0x3A,i&0xff); w(0x3B,i>>8); w(0x3C,b)
    w(0x38,0x00)

def srst():
    w(0x02,0x00); time.sleep(0.01)
    w(0x02,0x01); time.sleep(0.3)

print('step1: current reg0 =', hex(rd(0x00)))
print('step2: download firmware only (no reset)')
download()
print('  reg0 right after dl =', hex(rd(0x00)))
time.sleep(1)
print('  reg0 after 1s wait  =', hex(rd(0x00)))
print('step3: soft_reset now (mimic driver: dl then reset 1s later)')
srst()
print('  reg0 after reset    =', hex(rd(0x00)))
