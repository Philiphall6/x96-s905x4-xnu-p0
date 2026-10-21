/* Minimal, position-independent PID 1 for the X96SC2 mockfs QEMU test. */
#define SYS_write  4
#define SYS_open   5
#define SYS_getpid 20
#define SYS_select 93
#define O_RDWR     2

	.text
	.globl _start
	.p2align 2
_start:
	/* Darwin may provide a stack that is not yet aligned for our calls. */
	mov x9, sp
	and x9, x9, #~15
	mov sp, x9

	adr x0, console_path
	mov x1, #O_RDWR
	mov x2, #0
	mov x16, #SYS_open
	svc #0x80
	b.cs quiet_loop
	mov x19, x0

	adr x1, hello
	adr x2, pid_prefix_end
	sub x2, x2, x1
	bl write_console

	mov x16, #SYS_getpid
	svc #0x80
	add w0, w0, #'0'
	sub sp, sp, #16
	strb w0, [sp]
	mov x1, sp
	mov x2, #1
	bl write_console
	add sp, sp, #16

	adr x1, pid_prefix_end
	adr x2, alive
	sub x2, x2, x1
	bl write_console

alive_loop:
	mov x0, #0
	mov x1, #0
	mov x2, #0
	mov x3, #0
	adr x4, five_seconds
	mov x16, #SYS_select
	svc #0x80
	adr x1, alive
	adr x2, alive_end
	sub x2, x2, x1
	bl write_console
	b alive_loop

write_console:
	mov x0, x19
	mov x16, #SYS_write
	svc #0x80
	ret

quiet_loop:
	b quiet_loop

	.p2align 3
five_seconds:
	.quad 5
	.quad 0
console_path:
	.asciz "/dev/console"
hello:
	.ascii "\n*** X96SC2 userspace: init running as PID "
pid_prefix_end:
	.ascii " ***\n"
alive:
	.ascii "X96SC2 init: still alive\n"
alive_end:
