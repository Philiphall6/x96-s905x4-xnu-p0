ENTRY(_image_start)

SECTIONS
{
    . = 0;
    .text : { KEEP(*(.text.boot)) *(.text*) }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .got : { *(.got*) *(.got.plt*) }
    .bss (NOLOAD) : { *(.bss*) *(COMMON) }
    _image_end = .;
    /DISCARD/ : { *(.comment*) *(.note*) *(.eh_frame*) }
}

