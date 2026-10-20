/* Minimal Linux-Image-compatible entry for read-only X96 boot measurements. */

.section .text.boot, "ax"
.global _image_start
.global _start
.type _start, %function

_image_start:
	b	_start
	nop
	.quad	0x0000000000080000      /* conventional arm64 text_offset */
	.quad	_image_end - _image_start
	.quad	0                       /* little-endian, page size unspecified */
	.quad	0
	.quad	0
	.quad	0
	.word	0x644d5241              /* ARM64 Linux Image magic */
	.word	0

_start:
	msr	daifset, #0xf
	mov	x19, x0                  /* live FDT pointer from U-Boot */
	adr	x0, stack_top
	mov	sp, x0
	mov	x29, xzr
	mov	x30, xzr
	mov	x0, x19
	bl	measure_main
1:
	wfe
	b	1b

.section .data.stack, "aw", %progbits
.balign 16
stack:
	.zero 0x10000
stack_top:
