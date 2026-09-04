#!/bin/bash
# SAA7231 驱动环境诊断 (Debian 11)
# 运行:  su -c "bash check.sh"
echo "========== 1. 内核版本 =========="
uname -r

echo
echo "========== 2. PCI 设备识别 =========="
lspci -nnk -s 03:00.0 2>/dev/null | head -6
lspci -nnk -s 04:00.0 2>/dev/null | head -6

echo
echo "========== 3. DVB 内核配置 =========="
grep -E 'CONFIG_DVB_CORE|CONFIG_DVB_LGS8GXX|CONFIG_MEDIA_TUNER_TDA18271|CONFIG_DVB_DEMUX|CONFIG_I2C=' /boot/config-$(uname -r) 2>/dev/null

echo
echo "========== 4. dvb-core 头文件位置 =========="
for d in /lib/modules/$(uname -r)/build/drivers/media/dvb-core \
         /usr/src/linux-headers-$(uname -r)-common/drivers/media/dvb-core \
         /usr/src/linux-headers-$(uname -r)/drivers/media/dvb-core ; do
  if [ -f "$d/dvbdev.h" ]; then
    echo "FOUND: $d"
    ls "$d"/dvbdev.h "$d"/dvb_frontend.h "$d"/dvb_demux.h "$d"/dmxdev.h 2>&1
  fi
done

echo
echo "========== 5. 相关内核模块 =========="
lsmod | grep -E 'dvb_core|dvb|lgs8|tda18271|^i2c' || echo "(dvb_core 未加载 - 属正常，装载时会自动拉起)"

echo
echo "========== 6. 已有 I2C 总线 (装载后会有 SAA7231 总线) =========="
ls -l /dev/i2c-* 2>/dev/null || echo "无 /dev/i2c-*"

echo
echo "========== 7. 编译工具链 =========="
gcc --version 2>/dev/null | head -1
make --version 2>/dev/null | head -1
ls -d /usr/src/linux-headers-$(uname -r) 2>/dev/null || echo "WARN: 未安装 linux-headers-$(uname -r)"
