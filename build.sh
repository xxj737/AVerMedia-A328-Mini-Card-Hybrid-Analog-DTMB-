#!/bin/bash
# SAA7231 驱动编译 (Debian 11, kernel 5.10)
# 运行:  su -c "bash build.sh"
set -e
cd "$(dirname "$0")"

echo "== 编译 SAA7231 驱动 (kernel $(uname -r)) =="
make

echo
echo "== 编译成功，产物: =="
ls -l *.ko

echo
echo "== 下一步: 装载 =="
echo "   su -c \"bash load.sh\""
echo "  或手动:  insmod ./saa7231_core.ko; insmod ./saa7231_drv.ko"
echo "  装载后检查:  dmesg | tail -40"
