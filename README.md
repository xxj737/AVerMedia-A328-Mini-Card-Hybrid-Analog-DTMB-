AVerMedia Minipcie A328已知桥接芯片NXP SAA7231+解调芯片LGS8G75，Tuner芯片是NXP TDA18271

PCI\VEN 1131&DEV 7231&SUBSYS 02031461&REV AA

PCI\VEN_1131&DEV_7231&SUBSYS_02031461

PCI\VEN_1131&DEV_7231&CC_048000

PCI\VEN_1131&DEV 7231&CC 0480

Debian-11

tvheadend v4.3

CPU:J1900

ddr3 8gb ssd128gb


root@debian:~# dmesg | grep DVB
[49484.298892] saa7231_dvb_init (0): INFO: Device supoort 1 DVB adapters
[49484.298909] dvbdev: DVB: registering new adapter (SAA7231 DVB External Adapter:1)
[49484.731027] SAA7231 0000:04:00.0: DVB: registering adapter 0 frontend 0 (Legend Sili                       con LGS8913/LGS8GXX DMB-TH)...
[49488.216525] SAA7231 0000:04:00.0: DVB: adapter 0 frontend 0 frequency 0 out of range                        (474000000..858000000)
root@debian:~# ls -l /dev/dvb/adapter0/
总用量 0
crw-rw---- 1 root video 212, 0  9月  4 12:13 demux0
crw-rw---- 1 root video 212, 1  9月  4 12:13 dvr0
crw-rw---- 1 root video 212, 3  9月  4 12:13 frontend0
crw-rw---- 1 root video 212, 2  9月  4 12:13 net0
root@debian:~# lspci -vnn
00:00.0 Host bridge [0600]: Intel Corporation Atom Processor Z36xxx/Z37xxx Series SoC T                       ransaction Register [8086:0f00] (rev 11)
        Subsystem: Intel Corporation Atom Processor Z36xxx/Z37xxx Series SoC Transactio                       n Register [8086:2212]
        Flags: bus master, fast devsel, latency 0
        Kernel driver in use: iosf_mbi_pci

00:02.0 VGA compatible controller [0300]: Intel Corporation Atom Processor Z36xxx/Z37xx                       x Series Graphics & Display [8086:0f31] (rev 11) (prog-if 00 [VGA controller])
        DeviceName:  Onboard IGD
        Subsystem: Intel Corporation Atom Processor Z36xxx/Z37xxx Series Graphics & Dis                       play [8086:2212]
        Flags: bus master, fast devsel, latency 0, IRQ 94
        Memory at d0000000 (32-bit, non-prefetchable) [size=4M]
        Memory at c0000000 (32-bit, prefetchable) [size=256M]
        I/O ports at f080 [size=8]
        Expansion ROM at 000c0000 [virtual] [disabled] [size=128K]
        Capabilities: [d0] Power Management version 2
        Capabilities: [90] MSI: Enable+ Count=1/1 Maskable- 64bit-
        Capabilities: [b0] Vendor Specific Information: Len=07 <?>
        Kernel driver in use: i915
        Kernel modules: i915

00:13.0 SATA controller [0106]: Intel Corporation Atom Processor E3800 Series SATA AHCI                        Controller [8086:0f23] (rev 11) (prog-if 01 [AHCI 1.0])
        Subsystem: Intel Corporation Atom Processor E3800 Series SATA AHCI Controller [                       8086:7270]
        Flags: bus master, 66MHz, medium devsel, latency 0, IRQ 92
        I/O ports at f070 [size=8]
        I/O ports at f060 [size=4]
        I/O ports at f050 [size=8]
        I/O ports at f040 [size=4]
        I/O ports at f020 [size=32]
        Memory at d0f06000 (32-bit, non-prefetchable) [size=2K]
        Capabilities: [80] MSI: Enable+ Count=1/1 Maskable- 64bit-
        Capabilities: [70] Power Management version 3
        Capabilities: [a8] SATA HBA v1.0
        Kernel driver in use: ahci
        Kernel modules: ahci

00:1a.0 Encryption controller [1080]: Intel Corporation Atom Processor Z36xxx/Z37xxx Se                       ries Trusted Execution Engine [8086:0f18] (rev 11)
        Subsystem: Intel Corporation Atom Processor Z36xxx/Z37xxx Series Trusted Execut                       ion Engine [8086:7270]
        Flags: bus master, fast devsel, latency 0, IRQ 93
        Memory at d0d00000 (32-bit, non-prefetchable) [size=1M]
        Memory at d0c00000 (32-bit, non-prefetchable) [size=1M]
        Capabilities: [80] Power Management version 3
        Capabilities: [a0] MSI: Enable+ Count=1/1 Maskable- 64bit-
        Kernel driver in use: mei_txe
        Kernel modules: mei_txe

00:1b.0 Audio device [0403]: Intel Corporation Atom Processor Z36xxx/Z37xxx Series High                        Definition Audio Controller [8086:0f04] (rev 11)
        Subsystem: Intel Corporation Atom Processor Z36xxx/Z37xxx Series High Definitio                       n Audio Controller [8086:7270]
        Flags: bus master, fast devsel, latency 0, IRQ 95
        Memory at d0f00000 (64-bit, non-prefetchable) [size=16K]
        Capabilities: [50] Power Management version 2
        Capabilities: [60] MSI: Enable+ Count=1/1 Maskable- 64bit+
        Kernel driver in use: snd_hda_intel
        Kernel modules: snd_hda_intel

00:1c.0 PCI bridge [0604]: Intel Corporation Atom Processor E3800 Series PCI Express Ro                       ot Port 1 [8086:0f48] (rev 11) (prog-if 00 [Normal decode])
        Flags: bus master, fast devsel, latency 0, IRQ 87
        Bus: primary=00, secondary=01, subordinate=01, sec-latency=0
        I/O behind bridge: 0000e000-0000efff [size=4K]
        Memory behind bridge: d0e00000-d0efffff [size=1M]
        Prefetchable memory behind bridge: [disabled]
        Capabilities: [40] Express Root Port (Slot+), MSI 00
        Capabilities: [80] MSI: Enable+ Count=1/1 Maskable- 64bit-
        Capabilities: [90] Subsystem: Intel Corporation Atom Processor E3800 Series PCI                        Express Root Port 1 [8086:7270]
        Capabilities: [a0] Power Management version 3
        Kernel driver in use: pcieport

00:1c.1 PCI bridge [0604]: Intel Corporation Atom Processor E3800 Series PCI Express Ro                       ot Port 2 [8086:0f4a] (rev 11) (prog-if 00 [Normal decode])
        Flags: bus master, fast devsel, latency 0, IRQ 88
        Bus: primary=00, secondary=02, subordinate=02, sec-latency=0
        I/O behind bridge: 00001000-00001fff [size=4K]
        Memory behind bridge: [disabled]
        Prefetchable memory behind bridge: [disabled]
        Capabilities: [40] Express Root Port (Slot+), MSI 00
        Capabilities: [80] MSI: Enable+ Count=1/1 Maskable- 64bit-
        Capabilities: [90] Subsystem: Intel Corporation Atom Processor E3800 Series PCI                        Express Root Port 2 [8086:7270]
        Capabilities: [a0] Power Management version 3
        Kernel driver in use: pcieport

00:1c.2 PCI bridge [0604]: Intel Corporation Atom Processor E3800 Series PCI Express Ro                       ot Port 3 [8086:0f4c] (rev 11) (prog-if 00 [Normal decode])
        Flags: bus master, fast devsel, latency 0, IRQ 89
        Bus: primary=00, secondary=03, subordinate=03, sec-latency=0
        I/O behind bridge: 00002000-00002fff [size=4K]
        Memory behind bridge: [disabled]
        Prefetchable memory behind bridge: [disabled]
        Capabilities: [40] Express Root Port (Slot+), MSI 00
        Capabilities: [80] MSI: Enable+ Count=1/1 Maskable- 64bit-
        Capabilities: [90] Subsystem: Intel Corporation Atom Processor E3800 Series PCI                        Express Root Port 3 [8086:7270]
        Capabilities: [a0] Power Management version 3
        Kernel driver in use: pcieport

00:1c.3 PCI bridge [0604]: Intel Corporation Atom Processor E3800 Series PCI Express Ro                       ot Port 4 [8086:0f4e] (rev 11) (prog-if 00 [Normal decode])
        Flags: bus master, fast devsel, latency 0, IRQ 90
        Bus: primary=00, secondary=04, subordinate=04, sec-latency=0
        I/O behind bridge: 00003000-00003fff [size=4K]
        Memory behind bridge: d0400000-d0bfffff [size=8M]
        Prefetchable memory behind bridge: [disabled]
        Capabilities: [40] Express Root Port (Slot+), MSI 00
        Capabilities: [80] MSI: Enable+ Count=1/1 Maskable- 64bit-
        Capabilities: [90] Subsystem: Intel Corporation Atom Processor E3800 Series PCI                        Express Root Port 4 [8086:7270]
        Capabilities: [a0] Power Management version 3
        Kernel driver in use: pcieport

00:1d.0 USB controller [0c03]: Intel Corporation Atom Processor Z36xxx/Z37xxx Series US                       B EHCI [8086:0f34] (rev 11) (prog-if 20 [EHCI])
        Subsystem: Intel Corporation Atom Processor Z36xxx/Z37xxx Series USB EHCI [8086                       :7270]
        Flags: bus master, medium devsel, latency 0, IRQ 23
        Memory at d0f05000 (32-bit, non-prefetchable) [size=1K]
        Capabilities: [50] Power Management version 3
        Capabilities: [58] Debug port: BAR=1 offset=00a0
        Capabilities: [98] PCI Advanced Features
        Kernel driver in use: ehci-pci
        Kernel modules: ehci_pci

00:1f.0 ISA bridge [0601]: Intel Corporation Atom Processor Z36xxx/Z37xxx Series Power                        Control Unit [8086:0f1c] (rev 11)
        Subsystem: Intel Corporation Atom Processor Z36xxx/Z37xxx Series Power Control                        Unit [8086:7270]
        Flags: bus master, medium devsel, latency 0
        Capabilities: [e0] Vendor Specific Information: Len=0c <?>
        Kernel driver in use: lpc_ich
        Kernel modules: lpc_ich

00:1f.3 SMBus [0c05]: Intel Corporation Atom Processor E3800 Series SMBus Controller [8                       086:0f12] (rev 11)
        Subsystem: Intel Corporation Atom Processor E3800 Series SMBus Controller [8086                       :7270]
        Flags: medium devsel, IRQ 18
        Memory at d0f04000 (32-bit, non-prefetchable) [size=32]
        I/O ports at f000 [size=32]
        Capabilities: [50] Power Management version 3
        Kernel driver in use: i801_smbus
        Kernel modules: i2c_i801

01:00.0 Ethernet controller [0200]: Realtek Semiconductor Co., Ltd. RTL8111/8168/8411 P                       CI Express Gigabit Ethernet Controller [10ec:8168] (rev 15)
        Subsystem: Realtek Semiconductor Co., Ltd. RTL8111/8168/8411 PCI Express Gigabi                       t Ethernet Controller [10ec:0123]
        Flags: bus master, fast devsel, latency 0, IRQ 16
        I/O ports at e000 [size=256]
        Memory at d0e04000 (64-bit, non-prefetchable) [size=4K]
        Memory at d0e00000 (64-bit, non-prefetchable) [size=16K]
        Capabilities: [40] Power Management version 3
        Capabilities: [50] MSI: Enable- Count=1/1 Maskable- 64bit+
        Capabilities: [70] Express Endpoint, MSI 01
        Capabilities: [b0] MSI-X: Enable+ Count=4 Masked-
        Capabilities: [100] Advanced Error Reporting
        Capabilities: [140] Virtual Channel
        Capabilities: [160] Device Serial Number 01-00-00-00-68-4c-e0-00
        Capabilities: [170] Latency Tolerance Reporting
        Capabilities: [178] L1 PM Substates
        Kernel driver in use: r8169
        Kernel modules: r8169

04:00.0 Multimedia controller [0480]: Philips Semiconductors SAA7231 [1131:7231] (rev a                       a)
        Subsystem: Avermedia Technologies Inc SAA7231 [1461:8323]
        Flags: bus master, fast devsel, latency 0, IRQ 19
        Memory at d0800000 (64-bit, non-prefetchable) [size=4M]
        Memory at d0400000 (64-bit, non-prefetchable) [size=4M]
        Capabilities: [40] MSI: Enable- Count=1/16 Maskable- 64bit+
        Capabilities: [50] Express Endpoint, MSI 00
        Capabilities: [74] Power Management version 3
        Capabilities: [7c] Vendor Specific Information: Len=84 <?>
        Capabilities: [100] Vendor Specific Information: ID=0000 Rev=0 Len=094 <?>
        Kernel driver in use: SAA7231
        Kernel modules: saa7231_drv
