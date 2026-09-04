#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add write/read-back diagnostics to rtl2836.c"""

F = '/home/xxj/saa7231_debian/rtl2836/rtl2836.c'
t = open(F).read()


def rep(old, new, tag):
    global t
    n = t.count(old)
    assert n == 1, f"{tag}: count={n}"
    t = t.replace(old, new)


# 1) add diag helper after rtl2836_get_mask_bits's bin_to_signed
rep(
    '''/* convert a two's-complement binary value with bit_num bits to signed */
static long rtl2836_bin_to_signed(u32 v, int bit_num)''',
    '''/* diagnostic: try writing then reading back a register */
static void rtl2836_diag_rw(struct rtl2836_state *s)
{
	u32 v = 0;
	int r;

	/* page0 0x19 is written 0x19 by the init table; try a distinct
	 * value first, read back, then restore */
	r = rtl2836_set_mask_bits(s, 0x0, 0x19, 7, 0, 0x5a);
	if (r) {
		printk(KERN_ERR "rtl2836-diag: write p0/0x19 failed=%d\\n", r);
		return;
	}
	r = rtl2836_get_bytes(s, 0x0, 0x19, 1, &v);
	printk(KERN_INFO "rtl2836-diag: p0/0x19 wrote 0x5a read=0x%02x (%s)\\n",
	       v, (v == 0x5a) ? "WRITE WORKS" : "WRITE NOT STICKING");
	/* restore init value */
	rtl2836_set_mask_bits(s, 0x0, 0x19, 7, 0, 0x19);

	/* also probe a few raw registers for the FF pattern */
	rtl2836_get_bytes(s, 0x5, 0x10, 2, &v);
	printk(KERN_INFO "rtl2836-diag: chip_id raw = 0x%04x\\n", v);
	rtl2836_get_bytes(s, 0x0, 0x01, 4, &v);
	printk(KERN_INFO "rtl2836-diag: p0 regs 01..04 = 0x%08x\\n", v);
}

/* convert a two's-complement binary value with bit_num bits to signed */
static long rtl2836_bin_to_signed(u32 v, int bit_num)''',
    'diag-helper')

# 2) call it in attach after the chip id read
rep(
    '''	dev_info(&i2c->dev, "rtl2836: chip @ 0x%02x, chip_id=0x%04x\\n",
		 cfg->i2c_addr, chip_id);''',
    '''	dev_info(&i2c->dev, "rtl2836: chip @ 0x%02x, chip_id=0x%04x\\n",
		 cfg->i2c_addr, chip_id);

	rtl2836_diag_rw(s);''',
    'attach-call')

open(F, 'w').write(t)
print('DIAG_PATCH_OK')
