#!/usr/bin/env python3
"""DTMB 调谐测试 v2 - ctypes 精确复刻 dtv_property 结构"""
import os, struct, fcntl, time, sys, ctypes

# ioctls
FE_SET_PROPERTY = 0x6F52
FE_READ_STATUS = 0x6F39
FE_READ_BER = 0x6F3A
FE_READ_SNR = 0x6F3B
FE_READ_SIGNAL_STRENGTH = 0x6F3C

DTV_CLEAR = 0
DTV_FREQUENCY = 1
DTV_MODULATION = 2
DTV_BANDWIDTH_HZ = 3
DTV_INVERSION = 4
DTV_DELIVERY_SYSTEM = 28
DTV_CODE_RATE_HP = 5
DTV_CODE_RATE_LP = 6
DTV_GUARD_INTERVAL = 7
DTV_TRANSMISSION_MODE = 8
DTV_HIERARCHY = 9

QAM_AUTO = 0
INVERSION_AUTO = -1
FEC_AUTO = 0
GUARD_AUTO = 7
TMODE_AUTO = 7
HIERARCHY_NONE = 0
BANDWIDTH_8_MHZ = 8000000
SYS_DTMB = 16

FE_HAS_SIGNAL = 0x01
FE_HAS_CARRIER = 0x02
FE_HAS_VITERBI = 0x04
FE_HAS_SYNC = 0x08
FE_HAS_LOCK = 0x10
FE_TIMEDOUT = 0x20
FE_REINIT = 0x40

STATUS_NAMES = {
    FE_HAS_SIGNAL: 'SIGNAL', FE_HAS_CARRIER: 'CARRIER', FE_HAS_VITERBI: 'VITERBI',
    FE_HAS_SYNC: 'SYNC', FE_HAS_LOCK: 'LOCK', FE_TIMEDOUT: 'TIMEDOUT', FE_REINIT: 'REINIT',
}

class DtvProperty(ctypes.Structure):
    """struct dtv_property {
           __u32 cmd; __u32 reserved[3];
           union { __u32 data; __u8 data[32]+len+...; } u;  // size 56
           int result;
       }  -> total 4+12+56+4 = 76 bytes
    """
    _fields_ = [
        ('cmd', ctypes.c_uint32),
        ('reserved', ctypes.c_uint32 * 3),
        ('u', ctypes.c_uint8 * 56),
        ('result', ctypes.c_int32),
    ]
    def set_cmd(self, cmd):
        self.cmd = cmd
    def set_data(self, data):
        # write u32 at start of union (offset 16)
        ctypes.memmove(ctypes.addressof(self.u), ctypes.byref(ctypes.c_uint32(data & 0xFFFFFFFF)), 4)

class DtvProperties(ctypes.Structure):
    """struct dtv_properties { __u32 num; __u32 reserved[3]; struct dtv_property *props; }"""
    _fields_ = [
        ('num', ctypes.c_uint32),
        ('reserved', ctypes.c_uint32 * 3),
        ('props', ctypes.POINTER(DtvProperty)),
    ]

class FE_STATUS(ctypes.Structure):
    _fields_ = [('val', ctypes.c_uint32)]

class FE_U16(ctypes.Structure):
    _fields_ = [('val', ctypes.c_uint16)]

class FE_U32(ctypes.Structure):
    _fields_ = [('val', ctypes.c_uint32)]

def set_dtmb(fd, freq_khz):
    cmds = [
        (DTV_CLEAR, 0),
        (DTV_FREQUENCY, freq_khz * 1000),
        (DTV_DELIVERY_SYSTEM, SYS_DTMB),
        (DTV_MODULATION, QAM_AUTO),
        (DTV_BANDWIDTH_HZ, BANDWIDTH_8_MHZ),
        (DTV_INVERSION, 0xFFFFFFFF),  # INVERSION_AUTO as unsigned
        (DTV_CODE_RATE_HP, FEC_AUTO),
        (DTV_CODE_RATE_LP, FEC_AUTO),
        (DTV_GUARD_INTERVAL, GUARD_AUTO),
        (DTV_TRANSMISSION_MODE, TMODE_AUTO),
        (DTV_HIERARCHY, HIERARCHY_NONE),
    ]
    arr = (DtvProperty * len(cmds))()
    for i, (cmd, data) in enumerate(cmds):
        arr[i].set_cmd(cmd)
        arr[i].set_data(data)
    props = DtvProperties()
    props.num = len(cmds)
    props.props = ctypes.cast(arr, ctypes.POINTER(DtvProperty))
    fcntl.ioctl(fd, FE_SET_PROPERTY, props)

def read_u32(fd, req):
    s = FE_U32()
    fcntl.ioctl(fd, req, s)
    return s.val

def read_u16(fd, req):
    s = FE_U16()
    fcntl.ioctl(fd, req, s)
    return s.val

def status_str(st):
    parts = [n for m, n in STATUS_NAMES.items() if st & m]
    return '|'.join(parts) if parts else 'NONE'

candidates = [674000, 690000, 706000, 722000, 738000, 754000, 770000,
              786000, 802000, 818000, 834000, 850000, 866000,
              610000, 626000, 642000, 658000]

fe_path = sys.argv[1] if len(sys.argv) > 1 else '/dev/dvb/adapter0/frontend0'
fd = os.open(fe_path, os.O_RDWR)
print('FE path: %s' % fe_path)

for freq in candidates:
    try:
        set_dtmb(fd, freq)
        time.sleep(1.0)
        st = read_u32(fd, FE_READ_STATUS)
        snr = read_u16(fd, FE_READ_SNR)
        sig = read_u16(fd, FE_READ_SIGNAL_STRENGTH)
        ber = read_u32(fd, FE_READ_BER)
        print('freq=%d kHz  status=%s  SNR=%d  SIGNAL=%d  BER=%d' % (freq, status_str(st), snr, sig, ber))
        if st & FE_HAS_LOCK:
            print('*** LOCKED at %d kHz! ***' % freq)
            for t in range(5):
                time.sleep(1)
                st = read_u32(fd, FE_READ_STATUS)
                snr = read_u16(fd, FE_READ_SNR)
                sig = read_u16(fd, FE_READ_SIGNAL_STRENGTH)
                print('  +%ds status=%s SNR=%d SIGNAL=%d' % (t+1, status_str(st), snr, sig))
                if not (st & FE_HAS_LOCK):
                    print('  LOCK LOST!')
                    break
            break
    except Exception as e:
        print('freq=%d kHz  ERROR: %s' % (freq, str(e)[:100]))

os.close(fd)
print('Done.')
