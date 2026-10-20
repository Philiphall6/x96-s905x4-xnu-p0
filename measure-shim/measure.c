/*
 * Read-only S905X4 preflight.  No storage, clocks, GPIOs or partition access.
 * It relies on U-Boot's existing UART and logo framebuffer configuration.
 */

typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef __UINTPTR_TYPE__ uptr;

#ifdef MEASURE_QEMU
#define UART_BASE       0x09000000ULL
#define UART_WFIFO      0x00
#define UART_STATUS     0x18
#define UART_TX_FULL    (1U << 5)
#else
#define UART_BASE       0xfe07a000ULL
#define UART_WFIFO      0x00
#define UART_STATUS     0x0c
#define UART_TX_FULL    (1U << 21)
#endif

#define FB_BASE         0xdf800000ULL
#define FB_WIDTH        1920U
#define FB_HEIGHT       1080U
#define FB_STRIDE       1920U
#define FB_BAND_HEIGHT  300U

#define FDT_MAGIC       0xd00dfeedU

static inline u32
mmio_read32(u64 address)
{
	return *(volatile u32 *)(uptr)address;
}

static inline void
mmio_write32(u64 address, u32 value)
{
	*(volatile u32 *)(uptr)address = value;
}

static inline u64
read_currentel(void)
{
	u64 value;
	__asm__ volatile("mrs %0, CurrentEL" : "=r"(value));
	return value;
}

static inline u64
read_cntfrq(void)
{
	u64 value;
	__asm__ volatile("mrs %0, CNTFRQ_EL0" : "=r"(value));
	return value;
}

static inline u64
read_cntpct(void)
{
	u64 value;
	__asm__ volatile("mrs %0, CNTPCT_EL0" : "=r"(value));
	return value;
}

static inline u64
read_mpidr(void)
{
	u64 value;
	__asm__ volatile("mrs %0, MPIDR_EL1" : "=r"(value));
	return value;
}

static inline u64
read_sctlr(u64 currentel)
{
	u64 value;
	if (currentel == 0x8) {
		__asm__ volatile("mrs %0, SCTLR_EL2" : "=r"(value));
	} else {
		__asm__ volatile("mrs %0, SCTLR_EL1" : "=r"(value));
	}
	return value;
}

static inline u64
read_hcr_if_el2(u64 currentel)
{
	u64 value = 0;
	if (currentel == 0x8) {
		__asm__ volatile("mrs %0, HCR_EL2" : "=r"(value));
	}
	return value;
}

static void
uart_putc(char value)
{
	/* Never hang if firmware did not leave this UART usable. */
	for (u32 timeout = 0; timeout < 1000000; timeout++) {
		if ((mmio_read32(UART_BASE + UART_STATUS) & UART_TX_FULL) == 0) {
			mmio_write32(UART_BASE + UART_WFIFO, (u8)value);
			return;
		}
	}
}

static void
uart_puts(const char *value)
{
	while (*value != 0) {
		if (*value == '\n') {
			uart_putc('\r');
		}
		uart_putc(*value++);
	}
}

static char
hex_digit(u32 value)
{
	return value < 10 ? (char)('0' + value) : (char)('A' + value - 10);
}

static void
uart_hex64(u64 value)
{
	uart_puts("0x");
	for (u32 shift = 60;; shift -= 4) {
		uart_putc(hex_digit((u32)(value >> shift) & 0xf));
		if (shift == 0) {
			break;
		}
	}
}

static u32
be32(const void *pointer)
{
	const u8 *p = (const u8 *)pointer;
	return ((u32)p[0] << 24) | ((u32)p[1] << 16) | ((u32)p[2] << 8) | p[3];
}

#ifndef MEASURE_QEMU
/* Original compact 5x7 glyphs, one five-bit row per byte. */
static u8
glyph_row(char c, u32 row)
{
	static const u8 digits[16][7] = {
		{14,17,19,21,25,17,14}, {4,12,4,4,4,4,14},
		{14,17,1,2,4,8,31}, {30,1,1,14,1,1,30},
		{2,6,10,18,31,2,2}, {31,16,16,30,1,1,30},
		{14,16,16,30,17,17,14}, {31,1,2,4,8,8,8},
		{14,17,17,14,17,17,14}, {14,17,17,15,1,1,14},
		{14,17,17,31,17,17,17}, {30,17,17,30,17,17,30},
		{14,17,16,16,16,17,14}, {30,17,17,17,17,17,30},
		{31,16,16,30,16,16,31}, {31,16,16,30,16,16,16}
	};
	if (c >= '0' && c <= '9') return digits[c - '0'][row];
	if (c >= 'A' && c <= 'F') return digits[10 + c - 'A'][row];
	switch (c) {
	case 'X': { static const u8 v[7] = {17,17,10,4,10,17,17}; return v[row]; }
	case 'P': { static const u8 v[7] = {30,17,17,30,16,16,16}; return v[row]; }
	case 'L': { static const u8 v[7] = {16,16,16,16,16,16,31}; return v[row]; }
	case 'R': { static const u8 v[7] = {30,17,17,30,20,18,17}; return v[row]; }
	case 'Q': { static const u8 v[7] = {14,17,17,17,21,18,13}; return v[row]; }
	case 'M': { static const u8 v[7] = {17,27,21,21,17,17,17}; return v[row]; }
	case 'I': { static const u8 v[7] = {14,4,4,4,4,4,14}; return v[row]; }
	case 'D': { static const u8 v[7] = {30,17,17,17,17,17,30}; return v[row]; }
	case 'T': { static const u8 v[7] = {31,4,4,4,4,4,4}; return v[row]; }
	case 'S': { static const u8 v[7] = {15,16,16,14,1,1,30}; return v[row]; }
	case 'C': { static const u8 v[7] = {14,17,16,16,16,17,14}; return v[row]; }
	case 'H': { static const u8 v[7] = {17,17,17,31,17,17,17}; return v[row]; }
	case 'O': { static const u8 v[7] = {14,17,17,17,17,17,14}; return v[row]; }
	case 'K': { static const u8 v[7] = {17,18,20,24,20,18,17}; return v[row]; }
	case ' ': return 0;
	case ':': return (row == 2 || row == 5) ? 4 : 0;
	default: return 0;
	}
}

static void
fb_rect(u32 x, u32 y, u32 width, u32 height, u32 color)
{
	volatile u32 *fb = (volatile u32 *)(uptr)FB_BASE;
	if (x >= FB_WIDTH || y >= FB_HEIGHT) return;
	if (x + width > FB_WIDTH) width = FB_WIDTH - x;
	if (y + height > FB_HEIGHT) height = FB_HEIGHT - y;
	for (u32 py = 0; py < height; py++) {
		for (u32 px = 0; px < width; px++) {
			fb[(y + py) * FB_STRIDE + x + px] = color;
		}
	}
}

static void
fb_char(u32 x, u32 y, char c, u32 scale, u32 color)
{
	for (u32 row = 0; row < 7; row++) {
		u8 bits = glyph_row(c, row);
		for (u32 col = 0; col < 5; col++) {
			if (bits & (1U << (4 - col))) {
				fb_rect(x + col * scale, y + row * scale, scale, scale, color);
			}
		}
	}
}

static void
fb_puts(u32 x, u32 y, const char *text, u32 scale, u32 color)
{
	while (*text != 0) {
		fb_char(x, y, *text++, scale, color);
		x += 6 * scale;
	}
}

static void
fb_hex64(u32 x, u32 y, u64 value, u32 color)
{
	for (u32 shift = 60;; shift -= 4) {
		fb_char(x, y, hex_digit((u32)(value >> shift) & 0xf), 3, color);
		x += 18;
		if (shift == 0) break;
	}
}
#endif

static void
emit_uart_value(const char *name, u64 value)
{
	uart_puts(name);
	uart_hex64(value);
	uart_putc('\n');
}

void
measure_main(void *fdt)
{
	u64 currentel = read_currentel();
	u64 sctlr;
	u64 cntfrq;
	u64 cntpct;
	u64 mpidr;
	u64 hcr;
	uptr fdt_address = (uptr)fdt;
	u32 fdt_magic = 0;
	u32 fdt_size = 0;

	/*
	 * Do not touch physical MMIO or the FDT unless the entry state is the
	 * one required by the arm64 Linux boot ABI.  A return drops into the
	 * WFE loop in start.S without accessing any device.
	 */
	if (currentel != 0x4 && currentel != 0x8) {
		return;
	}
	sctlr = read_sctlr(currentel);
	if ((sctlr & ((1U << 0) | (1U << 2))) != 0) {
		return;
	}

	cntfrq = read_cntfrq();
	cntpct = read_cntpct();
	mpidr = read_mpidr();
	hcr = read_hcr_if_el2(currentel);

	/* x0 is supplied by U-Boot; reject obviously unsafe FDT addresses. */
	if (fdt_address >= 0x1000 && fdt_address < 0x100000000ULL &&
	    (fdt_address & 7) == 0) {
		fdt_magic = be32(fdt);
		if (fdt_magic == FDT_MAGIC) {
			fdt_size = be32((const u8 *)fdt + 4);
			if (fdt_size < 40 || fdt_size > 0x200000) {
				fdt_size = 0;
			}
		}
	}

	uart_puts("\nX96 S905X4 P0 READ-ONLY MEASUREMENT\n");
	emit_uart_value("CURRENTEL=", currentel);
	emit_uart_value("MPIDR_EL1=", mpidr);
	emit_uart_value("CNTFRQ_EL0=", cntfrq);
	emit_uart_value("CNTPCT_EL0=", cntpct);
	emit_uart_value("SCTLR=", sctlr);
	emit_uart_value("HCR_EL2=", hcr);
	emit_uart_value("FDT_POINTER=", (u64)(uptr)fdt);
	emit_uart_value("FDT_MAGIC=", fdt_magic);
	emit_uart_value("FDT_TOTALSIZE=", fdt_size);

#ifndef MEASURE_QEMU
	fb_rect(0, 0, FB_WIDTH, FB_BAND_HEIGHT, 0xff000000);
	fb_puts(32, 24, "X96 P0", 6, 0xffffffff);
	fb_puts(32, 90, "EL", 4, 0xff00ffff);
	fb_hex64(140, 90, currentel, 0xff00ffff);
	fb_puts(32, 130, "FREQ", 4, 0xff00ff00);
	fb_hex64(200, 130, cntfrq, 0xff00ff00);
	fb_puts(32, 170, "MPIDR", 4, 0xffffc000);
	fb_hex64(240, 170, mpidr, 0xffffc000);
	fb_puts(32, 210, "FDT", 4, fdt_magic == FDT_MAGIC ? 0xff00ff00 : 0xffff0000);
	fb_hex64(180, 210, (u64)(uptr)fdt, 0xffffffff);
	fb_puts(32, 250, fdt_magic == FDT_MAGIC ? "OK" : "ERROR", 4,
	    fdt_magic == FDT_MAGIC ? 0xff00ff00 : 0xffff0000);
	__asm__ volatile("dsb sy" ::: "memory");
#endif
	uart_puts(fdt_magic == FDT_MAGIC ? "MEASUREMENT COMPLETE\n" : "FDT INVALID\n");
}
