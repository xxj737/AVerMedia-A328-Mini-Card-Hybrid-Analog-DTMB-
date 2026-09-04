#!/bin/bash
# 从 Debian 的 linux-source-5.10 包提取 DVB 头文件到本目录 include/media/
# 运行:  su -c "bash fetch_dvbcore.sh"
#
# 说明: 内核 >=4.19 把 DVB 头文件放在 include/media/ 下 (公共头),
#       不再是 drivers/media/dvb-core/ (那里只剩 .c)。dvb_demux.h 已改名 demux.h。
set -e
cd "$(dirname "$0")"
mkdir -p include/media

echo "== 检查/安装 linux-source-5.10 =="
SRC=/usr/src/linux-source-5.10.tar.xz
if [ ! -f "$SRC" ]; then
  apt-get install -y linux-source-5.10
fi
[ -f "$SRC" ] || { echo "ERROR: 未能获得 $SRC"; exit 1; }
echo "OK: $SRC"

echo
echo "== 在归档中定位 include/media =="
MEDIAH=$(tar tf "$SRC" | grep -m1 'include/media/dvb_frontend.h$' || true)
if [ -z "$MEDIAH" ]; then
  echo "ERROR: 归档中找不到 include/media/dvb_frontend.h"
  echo "--- 归档中含 'include/media' 的行(前10) ---"
  tar tf "$SRC" | grep 'include/media/' | head -10
  exit 1
fi
echo "归档内 dvb_frontend.h 路径: $MEDIAH"
MEDIA_DIR=$(dirname "$MEDIAH")
echo "提取目录: $MEDIA_DIR"

echo
echo "== 提取 include/media 整个目录 =="
rm -rf /tmp/dvbhdr && mkdir -p /tmp/dvbhdr
tar xf "$SRC" -C /tmp/dvbhdr "$MEDIA_DIR"
MEDIA_LOCAL=$(find /tmp/dvbhdr -path '*include/media' -type d | head -1)
cp -r "$MEDIA_LOCAL"/* /home/xxj/A328_D_Driver/include/media/
echo "--- DVB 相关头文件: ---"
ls -l /home/xxj/A328_D_Driver/include/media/ | grep -E 'dvb|demux|dmxdev' || ls -l /home/xxj/A328_D_Driver/include/media/ | head

echo
echo "== 复制 DVB 头到驱动源码根目录 (双引号 include 直接命中) =="
DEST=/home/xxj/A328_D_Driver
for h in dvbdev.h dvb_frontend.h dvb_demux.h demux.h dmxdev.h dvb_net.h \
         dvb_ca_en50221.h dvb_math.h dvb_ringbuffer.h dvb_vb2.h \
         dvb-usb-ids.h videobuf2-dvb.h; do
  [ -f "/home/xxj/A328_D_Driver/include/media/$h" ] && cp "/home/xxj/A328_D_Driver/include/media/$h" "$DEST/"
done
ls -l "$DEST"/dvb*.h "$DEST"/demux.h "$DEST"/dmxdev.h 2>/dev/null

echo
echo "== 完成。编译:  bash build.sh =="
