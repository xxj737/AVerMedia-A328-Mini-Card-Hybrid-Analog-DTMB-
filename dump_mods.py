import os, struct
def rd32(fd, off): return struct.unpack('<I', os.pread(fd, 4, off))[0]
def wr32(fd, off, val): os.write(fd, struct.pack('<II', off, val & 0xFFFFFFFF))
fd = os.open('/dev/saa_diag', os.O_RDWR)
print('=== full 4-module register dump (card0) ===')
for base in (0x109000, 0x10a000, 0x10b000, 0x10c000):
    print('module 0x%06X:' % base)
    for off in (0x00, 0x04, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30):
        print('   +0x%02X = 0x%08X' % (off, rd32(fd, base+off)))
    print('   +0xfd4(MOD_CONF) = 0x%08X' % rd32(fd, base+0xfd4))
    print('   +0xfd8(INT_CLR_EN) = 0x%08X' % rd32(fd, base+0xfd8))
    print('   +0xfdc(INT_SET_EN) = 0x%08X' % rd32(fd, base+0xfdc))
    print('   +0xfe0(INT_STATUS) = 0x%08X' % rd32(fd, base+0xfe0))
    print('   +0xfe4(INT_ENABLE) = 0x%08X' % rd32(fd, base+0xfe4))
    print('   +0xfe8(INT_CLR_ST) = 0x%08X' % rd32(fd, base+0xfe8))
    print('   +0xffc(MOD_ID)     = 0x%08X' % rd32(fd, base+0xffc))
print()
print('=== GPIO module 0x105000, first 64 words ===')
for i in range(0, 0x100, 4):
    print('   +0x%03X = 0x%08X' % (i, rd32(fd, 0x105000+i)))
os.close(fd)
