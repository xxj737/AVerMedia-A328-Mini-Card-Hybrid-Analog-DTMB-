#!/usr/bin/env python3
"""DTMB 调谐测试：对每个频点设置频率并读取前端锁定状态"""
import os, struct, fcntl, time, sys

# DVB frontend ioctls
FE_GET_INFO = 0x6F3D
FE_READ_STATUS = 0x6F39
FE_READ_BER = 0x6F3A
FE_READ_SNR = 0x6F3B
FE_READ_SIGNAL_STRENGTH = 0x6F3C
FE_READ_UCBLOCKS = 0x6F3D  # actually FE_GET_PROPERTY territory; keep simple
FE_SET_PROPERTY = 0x6F52
FE_GET_PROPERTY = 0x6F53

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
DTV_INTERLEAVING = 17

QAM_AUTO = 0
INVERSION_AUTO = -1
FEC_AUTO = 0
GUARD_AUTO = 7
TMODE_AUTO = 7
HIERARCHY_NONE = 0
BANDWIDTH_8_MHZ = 8000000

SYS_DTMB = 16
SYS_DVBT = 0

# delivery systems accepted by lgs8gxx
DTV_ENUM_DELSYS = 28

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

def fe_open(path):
    return os.open(path, os.O_RDWR)

def fe_ioctl(fd, req, buf):
    return fcntl.ioctl(fd, req, buf)

def set_dtmb(fd, freq_khz):
    """构造 DTV_SET_PROPERTY: 清空->frequency->delivery_system->modulation等"""
    props = [
        (DTV_CLEAR, 0),
        (DTV_FREQUENCY, freq_khz * 1000),
        (DTV_DELIVERY_SYSTEM, SYS_DTMB),
        (DTV_MODULATION, QAM_AUTO),
        (DTV_BANDWIDTH_HZ, BANDWIDTH_8_MHZ),
        (DTV_INVERSION, INVERSION_AUTO),
        (DTV_CODE_RATE_HP, FEC_AUTO),
        (DTV_CODE_RATE_LP, FEC_AUTO),
        (DTV_GUARD_INTERVAL, GUARD_AUTO),
        (DTV_TRANSMISSION_MODE, TMODE_AUTO),
        (DTV_HIERARCHY, HIERARCHY_NONE),
    ]
    # struct dtv_property { u32 cmd; u32 reserved[3]; union{ u32 data; ...}; }  -> 24 bytes
    # struct dtv_properties { u32 num; u32 reserved[3]; struct dtv_property *props; }
    buf_props = bytearray()
    for cmd, data in props:
        buf_props += struct.pack('<IIII', cmd, 0, 0, 0)  # cmd, reserved[3]
        # union part: data as u32 -> need 8 more bytes (union is 8 bytes: u32 data + pad?)
        # Actual dtv_property: { u32 cmd; u32 reserved[3]; union { u32 data; struct {u8 data...}; } } -> 16+8
        buf_props += struct.pack('<I', data & 0xFFFFFFFF)
        buf_props += struct.pack('<I', 0)
    # 24 bytes per property
    n = len(props)
    # allocate C-side? No, python ioctl passes buffer; kernel expects pointer in struct
    # Must allocate memory via ctypes to pass pointer
    import ctypes
    class DtvProperty(ctypes.Structure):
        _fields_ = [('cmd', ctypes.c_uint32), ('reserved', ctypes.c_uint32 * 3),
                    ('u', ctypes.c_uint32 * 2)]
    class DtvProperties(ctypes.Structure):
        _fields_ = [('num', ctypes.c_uint32), ('reserved', ctypes.c_uint32 * 3),
                    ('props', ctypes.POINTER(DtvProperty))]
    arr = (DtvProperty * n)()
    for i, (cmd, data) in enumerate(props):
        arr[i].cmd = cmd
        arr[i].u[0] = data & 0xFFFFFFFF
    propset = DtvProperties()
    propset.num = n
    propset.props = arr
    # copy to raw buffer for ioctl
    return fcntl.ioctl(fd, FE_SET_PROPERTY, bytes(propset))

def read_status(fd):
    st = struct.pack('<I', 0)
    st = fcntl.ioctl(fd, FE_READ_STATUS, st)
    return struct.unpack('<I', st)[0]

def read_snr(fd):
    s = struct.pack('<H', 0)
    s = fcntl.ioctl(fd, FE_READ_SNR, s)
    return struct.unpack('<H', s)[0]

def read_signal(fd):
    s = struct.pack('<H', 0)
    s = fcntl.ioctl(fd, FE_READ_SIGNAL_STRENGTH, s)
    return struct.unpack('<H', s)[0]

def read_ber(fd):
    s = struct.pack('<I', 0)
    s = fcntl.ioctl(fd, FE_READ_BER, s)
    return struct.unpack('<I', s)[0]

def status_str(st):
    parts = [n for m, n in STATUS_NAMES.items() if st & m]
    return '|'.join(parts) if parts else 'NONE'

# Candidate DTMB frequencies (kHz) - common Chinese DTMB channels
candidates = [674000, 690000, 706000, 722000, 738000, 754000, 770000,
              786000, 802000, 818000, 834000, 850000, 866000, 610000, 626000, 642000, 658000]

fe_path = sys.argv[1] if len(sys.argv) > 1 else '/dev/dvb/adapter0/frontend0'
fd = fe_open(fe_path)

# First do a clean property query of delivery systems
print('FE path: %s' % fe_path)

# Try tune each frequency
for freq in candidates:
    try:
        set_dtmb(fd, freq)
        time.sleep(1.2)
        st = read_status(fd)
        snr = read_snr(fd)
        sig = read_signal(fd)
        print('freq=%d kHz  status=%s  SNR=%d  SIGNAL=%d' % (freq, status_str(st), snr, sig))
        if st & FE_HAS_LOCK:
            print('*** LOCKED at %d kHz! ***' % freq)
            # keep tuning loop a bit more to confirm
            for t in range(5):
                time.sleep(1)
                st = read_status(fd)
                snr = read_snr(fd)
                sig = read_signal(fd)
                print('  +%ds status=%s SNR=%d SIGNAL=%d' % (t+1, status_str(st), snr, sig))
                if not (st & FE_HAS_LOCK):
                    print('  LOCK LOST!')
                    break
            break
    except Exception as e:
        print('freq=%d kHz  ERROR: %s' % (freq, str(e)[:80]))

os.close(fd)
print('Done.')
