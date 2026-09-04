// saa_diag.c - minimal SAA7231 BAR0 diagnostic module (read/write)
// Usage:
//   read  : pread(fd, &val32, 4, offset)          -> 32-bit read at BAR0+offset
//   write : write(fd, {off32, val32}, 8)          -> 32-bit write at BAR0+offset
// CAREFUL: writing RGU CTRL0 (0x10E100) can reset the PCIe link (device drops).
#include <linux/init.h>
#include <linux/module.h>
#include <linux/pci.h>
#include <linux/io.h>
#include <linux/miscdevice.h>
#include <linux/uaccess.h>

#define SAA_VENDOR 0x1131
#define SAA_DEVICE 0x7231

static void __iomem *bar0;
static struct pci_dev *my_pdev;

static ssize_t diag_read(struct file *f, char __user *buf, size_t len, loff_t *off)
{
	uint32_t val;

	if (len < 4)
		return -EINVAL;
	if (*off < 0 || *off > 0x3FFFFC)
		return -EINVAL;
	val = readl(bar0 + *off);
	if (copy_to_user(buf, &val, 4))
		return -EFAULT;
	*off += 4;
	return 4;
}

static ssize_t diag_write(struct file *f, const char __user *buf, size_t len, loff_t *off)
{
	uint32_t data[2];

	if (len < 8)
		return -EINVAL;
	if (copy_from_user(data, buf, 8))
		return -EFAULT;
	if (data[0] > 0x3FFFFC)
		return -EINVAL;
	pr_info("saa_diag: write 0x%08X -> BAR0+0x%08X\n", data[1], data[0]);
	writel(data[1], bar0 + data[0]);
	*off += 8;
	return 8;
}

static const struct file_operations diag_fops = {
	.owner = THIS_MODULE,
	.read = diag_read,
	.write = diag_write,
};

static struct miscdevice diag_dev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = "saa_diag",
	.fops = &diag_fops,
};

static int __init diag_init(void)
{
	my_pdev = pci_get_device(SAA_VENDOR, SAA_DEVICE, NULL);
	if (!my_pdev) {
		pr_err("saa_diag: SAA7231 not found\n");
		return -ENODEV;
	}
	bar0 = pci_iomap(my_pdev, 0, 0x400000);
	if (!bar0) {
		pr_err("saa_diag: BAR0 iomap failed\n");
		pci_dev_put(my_pdev);
		return -EIO;
	}
	misc_register(&diag_dev);
	pr_info("saa_diag: BAR0 mapped, /dev/saa_diag ready\n");
	return 0;
}

static void __exit diag_exit(void)
{
	misc_deregister(&diag_dev);
	if (bar0)
		pci_iounmap(my_pdev, bar0);
	if (my_pdev)
		pci_dev_put(my_pdev);
	pr_info("saa_diag: unloaded\n");
}

module_init(diag_init);
module_exit(diag_exit);
MODULE_LICENSE("GPL");
