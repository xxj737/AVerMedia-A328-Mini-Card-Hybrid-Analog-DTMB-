# Makefile for SAA7231 - out-of-tree build for Debian 11 (kernel 5.10)
#
# Usage (as root or via su):
#   make                 # build against running kernel
#   make install         # copy .ko to /lib/modules/$(uname -r)/extra
#   make clean
#
# The kernel must have DVB support (CONFIG_DVB_CORE, CONFIG_I2C) enabled.
# This is satisfied by Debian's stock kernel (lgs8gxx/tda18271 modules ship
# with the kernel, which proves DVB core is present).

KERNELRELEASE ?= $(shell uname -r)
KDIR         ?= /lib/modules/$(KERNELRELEASE)/build
PWD           = $(shell pwd)

obj-m        += saa7231_core.o
obj-m        += saa7231_drv.o
obj-m        += lgs8gxx.o
ccflags-y    += -I$(PWD)/include/media

saa7231_core-objs := saa7231_pci.o \
                     saa7231_cgu.o \
                     saa7231_i2c.o \
                     saa7231_if.o \
                     saa7231_msi.o \
                     saa7231_dmabuf.o \
                     saa7231_gpio.o \
                     saa7231_ring.o \
                     saa7231_ts2dtl.o \
                     saa7231_stream.o \
                     saa7231_dvb.o

# The DVB headers live under include/media in kernel >=4.19 (public headers;
# drivers/media/dvb-core only keeps .c files there).  Debian's linux-headers
# does NOT ship them, so run ./fetch_dvbcore.sh first, which extracts
# include/media into $(PWD)/include/media from the linux-source-5.10 package.
DVB_CORE ?= $(shell for d in \
	$(PWD)/include/media \
	$(KDIR)/drivers/media/dvb-core \
	/usr/src/linux-headers-$(KERNELRELEASE)-common/drivers/media/dvb-core \
	/usr/src/linux-headers-$(KERNELRELEASE)/drivers/media/dvb-core ; do \
	if [ -f "$$d/dvb_frontend.h" ]; then echo "$$d"; break; fi; done)

LOCAL_INC := $(PWD)/include

# Use BOTH EXTRA_CFLAGS (classic, applied reliably by kbuild for out-of-tree
# builds) and ccflags-y, plus copy the DVB headers into the source dir (see
# fetch_dvbcore.sh) so the quoted includes resolve from the current directory.
EXTRA_CFLAGS += -I$(DVB_CORE) -I$(LOCAL_INC) -I$(PWD)
ccflags-y   += -I$(DVB_CORE) -I$(LOCAL_INC) -I$(PWD)

all:
	@if [ -z "$(DVB_CORE)" ]; then \
		echo "ERROR: dvb-core headers not found."; \
		echo "  searched: $(KDIR)/drivers/media/dvb-core and the -common tree."; \
		echo "  Install them:  apt install linux-headers-$(KERNELRELEASE)"; \
		echo "  or pass DVB_CORE=/path/to/drivers/media/dvb-core"; \
		exit 1; \
	fi
	@echo "Using dvb-core headers from: $(DVB_CORE)"
	$(MAKE) -C $(KDIR) M=$(PWD) modules

install:
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install
	depmod -a

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f *.o *.ko *.mod.c *.mod *.order *.symvers Module.markers .*.cmd
obj-m += saa_diag.o
