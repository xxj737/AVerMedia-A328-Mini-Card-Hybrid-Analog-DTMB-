// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * Realtek RTL2836 / RTL2836B DTMB demodulator driver
 *
 * Derived from the Realtek SDK (demod_rtl2836.c + dtmb_demod_base.c,
 * source: MyGica D690 / ambrosa DVB-Realtek-RTL2832U-2.2.2 project)
 * reimplemented as a standard kernel dvb_frontend driver for the
 * Yuan MC163ML (SAA7231 + RTL2836B + tuner) mini-PCIe card.
 *
 * Register access protocol (page-based):
 *   page select : write [0x00, page_no]
 *   write reg   : write [reg_addr, value]   (one byte per transaction)
 *   read  reg   : write [reg_addr] + read 1 byte
 *
 * Copyright (c) 2026
 */

#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/slab.h>
#include <linux/bitops.h>
#include <media/dvb_frontend.h>

static int rtl2836_if_freq_hz = 4570000;
module_param_named(if_freq_hz, rtl2836_if_freq_hz, int, 0644);
MODULE_PARM_DESC(if_freq_hz, "Demod IF frequency in Hz (default 4570000)");

static int rtl2836_ts_serial = 0;
module_param_named(ts_serial, rtl2836_ts_serial, int, 0644);
MODULE_PARM_DESC(ts_serial, "TS interface: 0=parallel, 1=serial (default 0)");

static int rtl2836_spec_inv = 0;
module_param_named(spec_inv, rtl2836_spec_inv, int, 0644);
MODULE_PARM_DESC(spec_inv, "Spectrum: 0=normal, 1=inverse (default 0)");

static int rtl2836_debug;
module_param_named(debug, rtl2836_debug, int, 0644);
MODULE_PARM_DESC(debug, "Enable verbose debug (default 0)");

#define dprintk(args...) \
	do { if (rtl2836_debug) printk(KERN_DEBUG "rtl2836: " args); } while (0)

/* ------------------------------------------------------------------ */
/* SDK constants                                                       */
/* ------------------------------------------------------------------ */

#define RTL2836_ADC_FREQ_HZ       48000000
#define RTL2836_IFFREQ_BIT_NUM    10
#define RTL2836_PER_DEN_VALUE     32768
#define RTL2836_EST_SNR_BIT_NUM   9
#define RTL2836_SNR_DB_DEN_VALUE  4
#define RTL2836_IF_AGC_BIT_NUM    14

#define PAGE_REG                  0x00

/* init register table entry */
struct rtl2836_reg_entry {
	u8 page;
	u8 addr;
	u8 msb;
	u8 lsb;
	u32 val;
};

/* 86 entries - RTL2836 init register table (from Realtek SDK
 * rtl2836_Initialize()) */
static const struct rtl2836_reg_entry rtl2836_init_table[] = {
	{0x0, 0x01, 0, 0, 0x1},
	{0x0, 0x02, 4, 4, 0x0},
	{0x0, 0x03, 2, 0, 0x0},
	{0x0, 0x0e, 5, 5, 0x1},
	{0x0, 0x11, 3, 3, 0x0},
	{0x0, 0x12, 1, 0, 0x1},
	{0x0, 0x16, 2, 0, 0x3},
	{0x0, 0x19, 7, 0, 0x19},
	{0x0, 0x1b, 7, 0, 0xcc},
	{0x0, 0x1f, 7, 0, 0x5},
	{0x0, 0x20, 2, 2, 0x1},
	{0x0, 0x20, 3, 3, 0x0},
	{0x1, 0x03, 7, 0, 0x38},
	{0x1, 0x31, 1, 1, 0x0},
	{0x1, 0x67, 7, 0, 0x30},
	{0x1, 0x68, 7, 0, 0x10},
	{0x1, 0x7f, 3, 2, 0x1},
	{0x1, 0xda, 7, 7, 0x1},
	{0x1, 0xdb, 7, 0, 0x5},
	{0x2, 0x09, 7, 0, 0x0a},
	{0x2, 0x10, 7, 0, 0x31},
	{0x2, 0x11, 7, 0, 0x31},
	{0x2, 0x1b, 7, 0, 0x1e},
	{0x2, 0x1e, 7, 0, 0x3a},
	{0x2, 0x1f, 5, 3, 0x3},
	{0x2, 0x21, 7, 0, 0x3f},
	{0x2, 0x24, 6, 5, 0x0},
	{0x2, 0x27, 7, 0, 0x17},
	{0x2, 0x31, 7, 0, 0x35},
	{0x2, 0x32, 7, 0, 0x3f},
	{0x2, 0x4f, 3, 2, 0x2},
	{0x2, 0x5a, 7, 0, 0x5},
	{0x2, 0x5b, 7, 0, 0x8},
	{0x2, 0x5c, 7, 0, 0x8},
	{0x2, 0x5e, 7, 5, 0x5},
	{0x2, 0x70, 0, 0, 0x0},
	{0x2, 0x77, 0, 0, 0x1},
	{0x2, 0x7a, 7, 0, 0x2f},
	{0x2, 0x81, 3, 2, 0x2},
	{0x2, 0x8d, 7, 0, 0x77},
	{0x2, 0x8e, 7, 4, 0x8},
	{0x2, 0x93, 7, 0, 0xff},
	{0x2, 0x94, 7, 0, 0x3},
	{0x2, 0x9d, 7, 0, 0xff},
	{0x2, 0x9e, 7, 0, 0x3},
	{0x2, 0xa8, 7, 0, 0xff},
	{0x2, 0xa9, 7, 0, 0x3},
	{0x2, 0xa3, 2, 2, 0x1},
	{0x3, 0x01, 7, 0, 0x0},
	{0x3, 0x04, 7, 0, 0x20},
	{0x3, 0x09, 7, 0, 0x10},
	{0x3, 0x14, 7, 0, 0xe4},
	{0x3, 0x15, 7, 0, 0x62},
	{0x3, 0x16, 7, 0, 0x8c},
	{0x3, 0x17, 7, 0, 0x11},
	{0x3, 0x1b, 7, 0, 0x40},
	{0x3, 0x1c, 7, 0, 0x14},
	{0x3, 0x23, 7, 0, 0x40},
	{0x3, 0x24, 7, 0, 0xd6},
	{0x3, 0x2b, 7, 0, 0x60},
	{0x3, 0x2c, 7, 0, 0x16},
	{0x3, 0x33, 7, 0, 0x40},
	{0x3, 0x3b, 7, 0, 0x44},
	{0x3, 0x43, 7, 0, 0x41},
	{0x3, 0x4b, 7, 0, 0x40},
	{0x3, 0x53, 7, 0, 0x4a},
	{0x3, 0x58, 7, 0, 0x1c},
	{0x3, 0x5b, 7, 0, 0x5a},
	{0x3, 0x5f, 7, 0, 0xe0},
	{0x4, 0x02, 7, 0, 0x7},
	{0x4, 0x03, 5, 0, 0x9},
	{0x4, 0x04, 5, 0, 0xb},
	{0x4, 0x05, 5, 0, 0xd},
	{0x4, 0x07, 2, 1, 0x3},
	{0x4, 0x07, 4, 3, 0x3},
	{0x4, 0x0e, 4, 0, 0x18},
	{0x4, 0x10, 4, 0, 0x1c},
	{0x4, 0x12, 4, 0, 0x1c},
	{0x4, 0x2f, 7, 0, 0x0},
	{0x4, 0x30, 7, 0, 0x20},
	{0x4, 0x31, 7, 0, 0x40},
	{0x4, 0x3e, 0, 0, 0x0},
	{0x4, 0x3e, 1, 1, 0x1},
	{0x4, 0x3e, 5, 2, 0x0},
	{0x4, 0x3f, 5, 0, 0x10},
	{0x4, 0x4a, 0, 0, 0x1},
};

/* pseudo-register bit positions (from SDK rtl2836_InitRegTable()) */
#define REG_SOFT_RST_N      0x0, 0x04, 0, 0    /* page, addr, msb, lsb */
#define REG_I2CT_EN_CTRL    0x0, 0x06, 0, 0
#define REG_CHIP_ID         0x5, 0x10, 15, 0
#define REG_EN_SP_INV       0x1, 0x31, 1, 1
#define REG_EN_DCR          0x1, 0x31, 0, 0
#define REG_BBIN_EN         0x1, 0x6a, 0, 0
#define REG_IFFREQ          0x1, 0x32, 9, 0
#define REG_TARGET_VAL      0x1, 0x03, 7, 0
#define REG_SERIAL          0x4, 0x50, 7, 7
#define REG_CDIV_PH0        0x4, 0x51, 4, 0
#define REG_CDIV_PH1        0x4, 0x52, 4, 0
#define REG_TPS_LOCK        0x8, 0x2a, 6, 6
#define REG_PN_PEAK_EXIST   0x6, 0x53, 0, 0
#define REG_FSM_STATE_R     0x6, 0xc0, 4, 0
#define REG_RO_PKT_ERR_RATE 0x9, 0x2d, 15, 0
#define REG_EST_SNR         0x8, 0x3e, 8, 0
#define REG_GAIN_OUT_R      0x6, 0xb4, 12, 1
#define REG_RF_AGC_VAL      0x6, 0x16, 13, 0
#define REG_IF_AGC_VAL      0x6, 0x14, 13, 0

/* ------------------------------------------------------------------ */
/* state / config                                                      */
/* ------------------------------------------------------------------ */

struct rtl2836_config {
	u8 i2c_addr;
	u8 ts_serial;   /* 0 = parallel, 1 = serial */
	u8 spec_inv;    /* 0 = normal, 1 = inverse */
};

struct rtl2836_state {
	struct i2c_adapter *i2c;
	const struct rtl2836_config *cfg;
	struct dvb_frontend fe;

	u8 page;            /* cached page register */
	bool page_valid;
	bool is_init;
	bool is_if_set;
	u32 if_freq_hz;
};

static inline struct rtl2836_state *fe_to_state(struct dvb_frontend *fe)
{
	return fe->demodulator_priv;
}

/* ------------------------------------------------------------------ */
/* I2C primitives                                                      */
/* ------------------------------------------------------------------ */

static int rtl2836_wr(struct rtl2836_state *s, u8 reg, u8 val)
{
	u8 buf[2] = { reg, val };
	struct i2c_msg msg = {
		.addr = s->cfg->i2c_addr, .flags = 0, .buf = buf, .len = 2
	};
	int r = i2c_transfer(s->i2c, &msg, 1);

	if (r != 1) {
		dprintk("wr fail reg=0x%02x val=0x%02x r=%d\n", reg, val, r);
		return (r < 0) ? r : -EREMOTEIO;
	}
	return 0;
}

static int rtl2836_rd(struct rtl2836_state *s, u8 reg, u8 *val)
{
	struct i2c_msg msg[2] = {
		{ .addr = s->cfg->i2c_addr, .flags = 0, .buf = &reg, .len = 1 },
		{ .addr = s->cfg->i2c_addr, .flags = I2C_M_RD, .buf = val, .len = 1 },
	};
	int r = i2c_transfer(s->i2c, msg, 2);

	if (r != 2) {
		dprintk("rd fail reg=0x%02x r=%d\n", reg, r);
		return (r < 0) ? r : -EREMOTEIO;
	}
	return 0;
}

static int rtl2836_set_page(struct rtl2836_state *s, u8 page)
{
	int r;

	if (s->page_valid && s->page == page)
		return 0;

	r = rtl2836_wr(s, PAGE_REG, page);
	if (r)
		return r;

	s->page = page;
	s->page_valid = true;
	return 0;
}

/* read up to 3 bytes from (page, addr), big-endian composed; SDK reads
 * one byte per transaction which works on all pages */
static int rtl2836_get_bytes(struct rtl2836_state *s, u8 page, u8 addr,
			     u8 nbytes, u32 *out)
{
	u32 v = 0;
	int i, r;

	r = rtl2836_set_page(s, page);
	if (r)
		return r;

	for (i = 0; i < nbytes; i++) {
		u8 b = 0;

		r = rtl2836_rd(s, addr + i, &b);
		if (r)
			return r;
		v |= (u32)b << (8 * i);
	}
	*out = v;
	return 0;
}

/* read-modify-write masked bits: msb/lsb may span up to 3 bytes */
static int rtl2836_set_mask_bits(struct rtl2836_state *s, u8 page, u8 addr,
				 u8 msb, u8 lsb, u32 value)
{
	u8 nbytes = msb / 8 + 1;
	u32 mask, reg;
	int i, r;

	mask = (msb >= 31) ? ~0u : (BIT(msb + 1) - 1);
	mask &= ~((BIT(lsb)) - 1);

	r = rtl2836_get_bytes(s, page, addr, nbytes, &reg);
	if (r)
		return r;

	reg = (reg & ~mask) | ((value << lsb) & mask);

	/* write back byte by byte */
	r = rtl2836_set_page(s, page);
	if (r)
		return r;
	for (i = 0; i < nbytes; i++) {
		r = rtl2836_wr(s, addr + i, (u8)(reg >> (8 * i)));
		if (r)
			return r;
	}
	return 0;
}

static int rtl2836_get_mask_bits(struct rtl2836_state *s, u8 page, u8 addr,
				 u8 msb, u8 lsb, u32 *value)
{
	u8 nbytes = msb / 8 + 1;
	u32 mask, v;
	int r;

	r = rtl2836_get_bytes(s, page, addr, nbytes, &v);
	if (r)
		return r;

	mask = (msb >= 31) ? ~0u : (BIT(msb + 1) - 1);
	mask &= ~((BIT(lsb)) - 1);

	*value = (v & mask) >> lsb;
	return 0;
}

/* diagnostic: try writing then reading back a register */
static void rtl2836_diag_rw(struct rtl2836_state *s)
{
	u32 v = 0;
	int r;

	/* page0 0x19 is written 0x19 by the init table; try a distinct
	 * value first, read back, then restore */
	r = rtl2836_set_mask_bits(s, 0x0, 0x19, 7, 0, 0x5a);
	if (r) {
		printk(KERN_ERR "rtl2836-diag: write p0/0x19 failed=%d\n", r);
		return;
	}
	r = rtl2836_get_bytes(s, 0x0, 0x19, 1, &v);
	printk(KERN_INFO "rtl2836-diag: p0/0x19 wrote 0x5a read=0x%02x (%s)\n",
	       v, (v == 0x5a) ? "WRITE WORKS" : "WRITE NOT STICKING");
	/* restore init value */
	rtl2836_set_mask_bits(s, 0x0, 0x19, 7, 0, 0x19);

	/* also probe a few raw registers for the FF pattern */
	rtl2836_get_bytes(s, 0x5, 0x10, 2, &v);
	printk(KERN_INFO "rtl2836-diag: chip_id raw = 0x%04x\n", v);
	rtl2836_get_bytes(s, 0x0, 0x01, 4, &v);
	printk(KERN_INFO "rtl2836-diag: p0 regs 01..04 = 0x%08x\n", v);
}

/* convert a two's-complement binary value with bit_num bits to signed */
static long rtl2836_bin_to_signed(u32 v, int bit_num)
{
	long s = (long)v;

	if (s & (1L << (bit_num - 1)))
		s -= (1L << bit_num);
	return s;
}

/* ------------------------------------------------------------------ */
/* DTMB demod operations (from SDK rtl2836_*)                          */
/* ------------------------------------------------------------------ */

static int rtl2836_init_regs(struct rtl2836_state *s)
{
	unsigned int i;
	int r;

	/* apply the 86-entry init table */
	for (i = 0; i < ARRAY_SIZE(rtl2836_init_table); i++) {
		const struct rtl2836_reg_entry *e = &rtl2836_init_table[i];

		r = rtl2836_set_mask_bits(s, e->page, e->addr, e->msb, e->lsb,
					  e->val);
		if (r) {
			dev_err(&s->i2c->dev,
				"rtl2836: init table[%u] p%u/0x%02x failed=%d\n",
				i, e->page, e->addr, r);
			return r;
		}
	}

	/* TS interface: DTMB_SERIAL(p4/0x50/b7), CDIV_PH0(p4/0x51/4:0),
	 * CDIV_PH1(p4/0x52/4:0); parallel {0,0xf,0xf} serial {1,1,1} */
	if (s->cfg->ts_serial) {
		r = rtl2836_set_mask_bits(s, REG_SERIAL, 1);
		if (!r) r = rtl2836_set_mask_bits(s, REG_CDIV_PH0, 1);
		if (!r) r = rtl2836_set_mask_bits(s, REG_CDIV_PH1, 1);
	} else {
		r = rtl2836_set_mask_bits(s, REG_SERIAL, 0);
		if (!r) r = rtl2836_set_mask_bits(s, REG_CDIV_PH0, 0xf);
		if (!r) r = rtl2836_set_mask_bits(s, REG_CDIV_PH1, 0xf);
	}
	if (r)
		return r;

	s->is_init = true;
	return 0;
}

static int rtl2836_software_reset(struct rtl2836_state *s)
{
	int r;

	/* SOFT_RST_N (p0/0x04/b0): 0 then 1 */
	r = rtl2836_set_mask_bits(s, REG_SOFT_RST_N, 0);
	if (r)
		return r;
	return rtl2836_set_mask_bits(s, REG_SOFT_RST_N, 1);
}

static int rtl2836_set_if_freq_hz(struct rtl2836_state *s, u32 if_freq_hz)
{
	u32 bbin_en, en_dcr, if_freq_adj, iffreq_bin;
	long iffreq_int;
	int r;

	bbin_en = (if_freq_hz == 0) ? 1 : 0;
	en_dcr  = (if_freq_hz == 0) ? 1 : 0;

	r = rtl2836_set_mask_bits(s, REG_BBIN_EN, bbin_en);
	if (r)
		return r;
	r = rtl2836_set_mask_bits(s, REG_EN_DCR, en_dcr);
	if (r)
		return r;

	/* IFFREQ = -round(IfFreqHzAdj * 2^10 / 48MHz), 10-bit two's comp;
	 * IfFreqHzAdj = IfFreqHz (if < 24MHz) else 48MHz - IfFreqHz */
	if_freq_adj = (if_freq_hz < RTL2836_ADC_FREQ_HZ / 2) ?
		      if_freq_hz : (RTL2836_ADC_FREQ_HZ - if_freq_hz);

	iffreq_int = (long)DIV_ROUND_CLOSEST_ULL(
		(u64)if_freq_adj << RTL2836_IFFREQ_BIT_NUM,
		RTL2836_ADC_FREQ_HZ);
	iffreq_int = -iffreq_int;

	/* 10-bit two's complement */
	iffreq_bin = (u32)(iffreq_int) & ((BIT(RTL2836_IFFREQ_BIT_NUM)) - 1);

	r = rtl2836_set_mask_bits(s, REG_IFFREQ, iffreq_bin);
	if (r)
		return r;

	dprintk("if=%uHz adj=%u iffreq_int=%ld bin=0x%03lx\n",
		if_freq_hz, if_freq_adj, iffreq_int, (unsigned long)iffreq_bin);

	s->is_if_set = true;
	return 0;
}

static int rtl2836_set_spectrum_mode(struct rtl2836_state *s, u8 spec_inv)
{
	return rtl2836_set_mask_bits(s, REG_EN_SP_INV, spec_inv ? 1 : 0);
}

/* ------------------------------------------------------------------ */
/* dvb_frontend ops                                                    */
/* ------------------------------------------------------------------ */

static int rtl2836_set_frontend(struct dvb_frontend *fe)
{
	struct rtl2836_state *s = fe_to_state(fe);
	struct dtv_frontend_properties *c = &fe->dtv_property_cache;
	int r;

	if (c->delivery_system != SYS_DTMB) {
		dev_err(&s->i2c->dev, "rtl2836: delsys %d not supported\n",
			c->delivery_system);
		return -EINVAL;
	}

	if (!s->is_init) {
		r = rtl2836_init_regs(s);
		if (r)
			return r;
	}

	if (!s->is_if_set || s->if_freq_hz != (u32)rtl2836_if_freq_hz) {
		r = rtl2836_set_if_freq_hz(s, rtl2836_if_freq_hz);
		if (r)
			return r;
		s->if_freq_hz = rtl2836_if_freq_hz;
	}

	r = rtl2836_set_spectrum_mode(s, s->cfg->spec_inv);
	if (r)
		return r;

	/* hand the RF frequency to the tuner if one is attached */
	if (fe->ops.tuner_ops.set_params) {
		r = fe->ops.tuner_ops.set_params(fe);
		if (r)
			return r;
	}

	/* start acquisition */
	r = rtl2836_software_reset(s);
	if (r)
		return r;

	dprintk("tuned: freq=%u if=%d spec_inv=%d ts_serial=%d\n",
		c->frequency, rtl2836_if_freq_hz, s->cfg->spec_inv,
		s->cfg->ts_serial);
	return 0;
}

static int rtl2836_init(struct dvb_frontend *fe)
{
	return 0;
}

static int rtl2836_sleep(struct dvb_frontend *fe)
{
	return 0;
}

/* SNR: 9-bit signed value * 1/4 dB */
static int rtl2836_read_snr(struct dvb_frontend *fe, u16 *snr)
{
	struct rtl2836_state *s = fe_to_state(fe);
	u32 v = 0;
	long db_x4;
	int r;

	r = rtl2836_get_mask_bits(s, REG_EST_SNR, &v);
	if (r)
		return r;

	db_x4 = rtl2836_bin_to_signed(v, RTL2836_EST_SNR_BIT_NUM);
	if (db_x4 < 0)
		db_x4 = 0;

	/* scale (db_x4 / 4) to 0-0xffff, clamp 40 dB */
	*snr = (u16)min_t(long, (db_x4 * 0xffff) / (4 * 400), 0xffff);
	return 0;
}

/* BER: RO_PKT_ERR_RATE / 32768, scale to 0-0xffffffff over ~65536 */
static int rtl2836_read_ber(struct dvb_frontend *fe, u32 *ber)
{
	struct rtl2836_state *s = fe_to_state(fe);
	u32 v = 0;
	int r;

	r = rtl2836_get_mask_bits(s, REG_RO_PKT_ERR_RATE, &v);
	if (r)
		return r;

	*ber = v * 65536 / RTL2836_PER_DEN_VALUE;
	return 0;
}

static int rtl2836_read_status(struct dvb_frontend *fe, enum fe_status *status)
{
	struct rtl2836_state *s = fe_to_state(fe);
	u32 snr_v = 0, per_v = 0, fsm = 0;
	long snr_int;
	int r;

	*status = 0;

	r = rtl2836_get_mask_bits(s, REG_EST_SNR, &snr_v);
	if (r)
		return r;
	r = rtl2836_get_mask_bits(s, REG_RO_PKT_ERR_RATE, &per_v);
	if (r)
		return r;

	/* FSM state (p6/0xc0/4:0) - informational */
	rtl2836_get_mask_bits(s, REG_FSM_STATE_R, &fsm);

	snr_int = rtl2836_bin_to_signed(snr_v, RTL2836_EST_SNR_BIT_NUM) / 4;

	dprintk("status: snr_raw=0x%03lx(%ld dB*4) per=%lu fsm=%lu\n",
		(unsigned long)snr_v, rtl2836_bin_to_signed(snr_v,
		RTL2836_EST_SNR_BIT_NUM), (unsigned long)per_v,
		(unsigned long)fsm);

	*status |= FE_HAS_SIGNAL | FE_HAS_CARRIER | FE_HAS_VITERBI |
		   FE_HAS_SYNC;

	/* SDK lock criterion: 0 < SNR_dB < 40 && PER < 1 */
	if (snr_int > 0 && snr_int < 40 && per_v < RTL2836_PER_DEN_VALUE)
		*status |= FE_HAS_LOCK;

	return 0;
}

static int rtl2836_read_signal_strength(struct dvb_frontend *fe, u16 *strength)
{
	struct rtl2836_state *s = fe_to_state(fe);
	u32 agc = 0;
	long if_agc;
	int r;

	*strength = 0xffff;

	r = rtl2836_get_mask_bits(s, REG_IF_AGC_VAL, &agc);
	if (r)
		return r;

	if_agc = rtl2836_bin_to_signed(agc, RTL2836_IF_AGC_BIT_NUM);

	/* SDK mapping: 54 - IfAgc / 183  =>  10..99 (higher = weaker) */
	{
		long q = 54 - if_agc / 183;

		if (q < 0)
			q = 0;
		if (q > 100)
			q = 100;
		/* dvb semantics: 0 = max strength, 0xffff = none */
		*strength = (u16)(0xffff - (q * 0xffff / 100));
	}
	return 0;
}

static void rtl2836_release(struct dvb_frontend *fe)
{
	struct rtl2836_state *s = fe_to_state(fe);

	kfree(s);
}

static const struct dvb_frontend_ops rtl2836_ops = {
	.delsys = { SYS_DTMB },
	.info = {
		.name = "Realtek RTL2836 (DTMB)",
		.frequency_min_hz =  470 * MHz,
		.frequency_max_hz =  862 * MHz,
		.frequency_stepsize_hz = 62.5 * kHz,
		.caps = FE_CAN_FEC_AUTO	| FE_CAN_QAM_AUTO |
			FE_CAN_TRANSMISSION_MODE_AUTO |
			FE_CAN_GUARD_INTERVAL_AUTO |
			FE_CAN_HIERARCHY_AUTO |
			FE_CAN_RECOVER,
	},
	.release			= rtl2836_release,
	.init				= rtl2836_init,
	.sleep				= rtl2836_sleep,
	.set_frontend			= rtl2836_set_frontend,
	.read_status			= rtl2836_read_status,
	.read_ber			= rtl2836_read_ber,
	.read_snr			= rtl2836_read_snr,
	.read_signal_strength		= rtl2836_read_signal_strength,
};

/* ------------------------------------------------------------------ */
/* attach / detach                                                     */
/* ------------------------------------------------------------------ */

struct dvb_frontend *rtl2836_attach(const struct rtl2836_config *cfg,
				    struct i2c_adapter *i2c)
{
	struct rtl2836_state *s;
	u32 chip_id = 0;
	int r;

	s = kzalloc(sizeof(*s), GFP_KERNEL);
	if (!s)
		return NULL;

	s->cfg = cfg;
	s->i2c = i2c;

	/* verify the chip answers and read its ID (page5/0x10/15:0).
	 * Do not hard-fail on an unexpected value but log it. */
	r = rtl2836_get_mask_bits(s, REG_CHIP_ID, &chip_id);
	if (r) {
		dev_err(&i2c->dev, "rtl2836: probe failed at 0x%02x (%d)\n",
			cfg->i2c_addr, r);
		kfree(s);
		return NULL;
	}
	dev_info(&i2c->dev, "rtl2836: chip @ 0x%02x, chip_id=0x%04x\n",
		 cfg->i2c_addr, chip_id);

	rtl2836_diag_rw(s);

	memcpy(&s->fe.ops, &rtl2836_ops, sizeof(struct dvb_frontend_ops));
	s->fe.demodulator_priv = s;

	return &s->fe;
}
EXPORT_SYMBOL_GPL(rtl2836_attach);

MODULE_DESCRIPTION("Realtek RTL2836/RTL2836B DTMB demodulator driver");
MODULE_AUTHOR("Yuan MC163ML bring-up");
MODULE_LICENSE("GPL");
