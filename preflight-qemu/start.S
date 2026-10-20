/*
 * X96/XNU P0 architectural preflight for QEMU virt + GICv2.
 *
 * This is not XNU and is never flashed.  It proves the EL2 -> EL1 drop,
 * architected counter access, the virtual timer PPI (INTID 27), and the
 * GIC-400-compatible memory-mapped CPU interface used by the X96 port.
 */

.section .text.boot, "ax"
.global _start
.type _start, %function

.equ UART0,        0x09000000
.equ UARTFR,       0x18
.equ UARTFR_TXFF,  5
.equ GICD,         0x08000000
.equ GICC,         0x08010000
.equ GICD_CTLR,    0x000
.equ GICD_IGROUPR0, 0x080
.equ GICD_ISENABLER0, 0x100
.equ GICD_IPRIORITYR0, 0x400
.equ GICC_CTLR,    0x00
.equ GICC_PMR,     0x04
.equ GICC_BPR,     0x08
.equ GICC_IAR,     0x0c
.equ GICC_EOIR,    0x10
.equ VTIMER_INTID, 27

_start:
	msr	daifset, #0xf
	ldr	x0, =stack_top
	mov	sp, x0
	mrs	x19, CurrentEL
	ldr	x0, =msg_start
	bl	uart_puts
	mov	x0, x19
	bl	uart_hex64
	ldr	x0, =msg_nl
	bl	uart_puts

	cmp	x19, #0x8
	b.eq	drop_el2
	cmp	x19, #0x4
	b.eq	el1_entry
	ldr	x0, =msg_bad_el
	bl	uart_puts
	b	hang

drop_el2:
	/*
	 * AArch64 EL1 with physical IRQ/FIQ delivery left at EL1.  Do not retain
	 * firmware/QEMU routing bits (IMO/FMO/AMO/TGE) from the EL2 environment.
	 */
	mov	x0, #0x80000000
	msr	hcr_el2, x0
	msr	cptr_el2, xzr
	mov	x0, #3
	msr	cnthctl_el2, x0
	msr	cntvoff_el2, xzr
	ldr	x0, =stack_top
	msr	sp_el1, x0
	ldr	x0, =el1_entry
	msr	elr_el2, x0
	/* EL1h with D/A/I/F masked while the GIC is configured. */
	mov	x0, #0x3c5
	msr	spsr_el2, x0
	eret

el1_entry:
	ldr	x0, =vectors
	msr	vbar_el1, x0
	isb

	ldr	x0, =msg_el1
	bl	uart_puts
	mrs	x20, cntfrq_el0
	ldr	x0, =msg_cntfrq
	bl	uart_puts
	mov	x0, x20
	bl	uart_hex64
	ldr	x0, =msg_nl
	bl	uart_puts

	/*
	 * QEMU virt exposes GICv2 without security extensions, so every interrupt
	 * belongs to the single primary group (IGROUPR=0).  On the physical X96,
	 * NS Group 1 is accessed through the same GICC_IAR/GICC_EOIR offsets.
	 */
	ldr	x1, =GICD
	mov	w0, #0
	str	w0, [x1, #GICD_IGROUPR0]
	mov	w0, #0xa0
	mov	w2, #0x01010101
	mul	w0, w0, w2
	str	w0, [x1, #(GICD_IPRIORITYR0 + 24)]
	mov	w0, #(1 << VTIMER_INTID)
	str	w0, [x1, #GICD_ISENABLER0]
	ldr	w0, [x1, #GICD_CTLR]
	orr	w0, w0, #1
	str	w0, [x1, #GICD_CTLR]

	ldr	x1, =GICC
	mov	w0, #0xff
	str	w0, [x1, #GICC_PMR]
	str	wzr, [x1, #GICC_BPR]
	ldr	w0, [x1, #GICC_CTLR]
	orr	w0, w0, #1
	str	w0, [x1, #GICC_CTLR]
	dsb	sy
	isb

	/* Fire the virtual timer after roughly 10 ms. */
	mov	x1, #100
	udiv	x0, x20, x1
	msr	cntv_tval_el0, x0
	mov	x0, #1
	msr	cntv_ctl_el0, x0
	isb
	/* Prove the timer itself asserted before relying on GIC delivery. */
	mrs	x6, cntvct_el0
	add	x6, x6, x20
1:
	mrs	x0, cntv_ctl_el0
	tbnz	x0, #2, 2f
	mrs	x0, cntvct_el0
	cmp	x0, x6
	b.lo	1b
	ldr	x0, =msg_timer_status_fail
	bl	uart_puts
	b	hang
2:
	ldr	x0, =msg_timer_pending
	bl	uart_puts
	/* The CPU interface must expose the pending PPI even while PSTATE.I=1. */
	ldr	x1, =GICC
	ldr	w21, [x1, #GICC_IAR]
	ldr	x0, =msg_iar
	bl	uart_puts
	mov	x0, x21
	bl	uart_hex64
	ldr	x0, =msg_nl
	bl	uart_puts
	and	w0, w21, #0x3ff
	cmp	w0, #VTIMER_INTID
	b.ne	gic_failed
	ldr	x1, =GICC
	str	w21, [x1, #GICC_EOIR]
	dsb	sy
	/* Re-arm after the diagnostic acknowledge, then test exception routing. */
	mov	x1, #100
	udiv	x0, x20, x1
	msr	cntv_tval_el0, x0
	mov	x0, #1
	msr	cntv_ctl_el0, x0
	isb
	msr	daifclr, #2
	wfi
	msr	daifset, #2

	ldr	x0, =timer_seen
	ldr	w0, [x0]
	cbz	w0, timer_failed
	ldr	x0, =msg_pass
	bl	uart_puts
	b	qemu_exit_success

timer_failed:
	ldr	x0, =msg_timer_fail
	bl	uart_puts
	b	hang

gic_failed:
	ldr	x0, =msg_gic_fail
	bl	uart_puts
	b	hang

qemu_exit_success:
	/* QEMU AArch64 semihosting SYS_EXIT_EXTENDED; never used on real X96. */
	mov	x0, #0x20
	ldr	x1, =exit_block
	hlt	#0xf000
	b	hang

.type irq_handler, %function
irq_handler:
	ldr	x1, =GICC
	ldr	w2, [x1, #GICC_IAR]
	and	w3, w2, #0x3ff
	cmp	w3, #VTIMER_INTID
	b.ne	1f
	msr	cntv_ctl_el0, xzr
	ldr	x0, =timer_seen
	mov	w3, #1
	str	w3, [x0]
1:
	str	w2, [x1, #GICC_EOIR]
	dsb	sy
	isb
	eret

.type sync_handler, %function
sync_handler:
	msr	daifset, #0xf
	ldr	x0, =msg_exception
	bl	uart_puts
	mrs	x0, esr_el1
	bl	uart_hex64
	ldr	x0, =msg_nl
	bl	uart_puts
	b	hang

.type uart_putc, %function
uart_putc:
	ldr	x1, =UART0
1:
	ldr	w2, [x1, #UARTFR]
	tbnz	w2, #UARTFR_TXFF, 1b
	strb	w0, [x1]
	ret

.type uart_puts, %function
uart_puts:
	mov	x3, x30
1:
	ldrb	w2, [x0], #1
	cbz	w2, 2f
	mov	w4, w0
	mov	w0, w2
	bl	uart_putc
	mov	w0, w4
	b	1b
2:
	ret	x3

.type uart_hex64, %function
uart_hex64:
	mov	x3, x30
	mov	x4, x0
	mov	x5, #16
1:
	lsr	x0, x4, #60
	cmp	w0, #10
	b.lo	2f
	add	w0, w0, #('a' - 10)
	b	3f
2:
	add	w0, w0, #'0'
3:
	bl	uart_putc
	lsl	x4, x4, #4
	subs	x5, x5, #1
	b.ne	1b
	ret	x3

hang:
	wfe
	b	hang

/* AArch64 vector table: only current-EL SPx IRQ is expected in P0. */
.balign 2048
vectors:
	b	sync_handler
	.org	vectors + 0x80
	b	hang
	.org	vectors + 0x100
	b	hang
	.org	vectors + 0x180
	b	hang
	.org	vectors + 0x200
	b	sync_handler
	.org	vectors + 0x280
	b	irq_handler
	.org	vectors + 0x300
	b	hang
	.org	vectors + 0x380
	b	hang
	.org	vectors + 0x400
	b	sync_handler
	.org	vectors + 0x480
	b	hang
	.org	vectors + 0x500
	b	hang
	.org	vectors + 0x580
	b	hang
	.org	vectors + 0x600
	b	sync_handler
	.org	vectors + 0x680
	b	hang
	.org	vectors + 0x700
	b	hang
	.org	vectors + 0x780
	b	hang

.section .rodata, "a"
msg_start:      .asciz "X96 P0 preflight CurrentEL=0x"
msg_el1:        .asciz "EL1 entered\r\n"
msg_cntfrq:     .asciz "CNTFRQ_EL0=0x"
msg_pass:       .asciz "PASS: GICv2 virtual timer INTID 27\r\n"
msg_timer_pending: .asciz "virtual timer asserted; unmasking IRQ\r\n"
msg_timer_status_fail: .asciz "FAIL: virtual timer never asserted\r\n"
msg_iar:        .asciz "GICC_IAR=0x"
msg_gic_fail:   .asciz "FAIL: GICv2 did not expose timer INTID 27\r\n"
msg_timer_fail: .asciz "FAIL: WFI returned without timer IRQ\r\n"
msg_bad_el:     .asciz "FAIL: expected EL1 or EL2\r\n"
msg_exception:  .asciz "FAIL: synchronous exception ESR=0x"
msg_nl:         .asciz "\r\n"

.section .data, "aw"
.balign 4
timer_seen: .word 0
.balign 8
exit_block:
	.quad 0x20026
	.quad 0

.section .bss, "aw", %nobits
.balign 16
stack: .skip 0x10000
stack_top:
