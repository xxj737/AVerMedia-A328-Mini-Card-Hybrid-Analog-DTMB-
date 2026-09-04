#!/bin/bash
# SAA7231 驱动装载 (Debian 11)
# 运行:  su -c "bash load.sh"
#
# 注意: 这是"只读侦察 + 驱动正式初始化"阶段。
# 装载前先确认没有残留模块。
cd "$(dirname "$0")"

echo "== 卸载旧模块(如有) =="
rmmod saa7231_drv 2>/dev/null || true
rmmod saa7231_core 2>/dev/null || true

echo "== 先确保依赖: dvb_core / lgs8gxx / tda18271 =="
modprobe lgs8gxx 2>/dev/null || true
modprobe tda18271 2>/dev/null || true

echo "== 装载 saa7231_core =="
insmod ./saa7231_core.ko || { echo "core 装载失败:"; dmesg | tail -20; exit 1; }
sleep 1

echo "== 装载 saa7231_drv =="
insmod ./saa7231_drv.ko verbose=1 || { echo "drv 装载失败:"; dmesg | tail -30; exit 1; }
sleep 2

echo
echo "== 结果 =="
echo "--- dmesg (最近40行) ---"
dmesg | tail -40

echo
echo "--- 是否出现 SAA7231 I2C 总线 ---"
ls -l /dev/i2c-* 2>/dev/null
echo "--- DVB adapter ---"
ls -l /dev/dvb/ 2>/dev/null || echo "(无 /dev/dvb - 未注册 adapter 则说明 probe 中断)"
