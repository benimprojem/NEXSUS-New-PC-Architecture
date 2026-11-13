# NEXSUS CPU Exception Frame and Context Preservation
**Document ID:** NEXSUS-CPU-EXCEPTION-FRAME-001  
**Status:** Architecture baseline proposal  
**Scope:** Hardware exception entry, nested contexts, register preservation, IRET and double-fault recovery

## 1. Design objective
NEXSUS uses a hybrid model:
1. Hardware atomically captures the minimum control state needed to make exception entry precise and restartable.
2. Hardware stores that control state in a protected, core-local Exception Context Stack (ECS).
3. General-purpose and execution-bank registers are saved by the handler prologue/compiler only when required.
4. A privileged per-core exception stack is used for software spill frames; interrupted application memory/stack is never trusted as the handler's stack.

This avoids saving every RA/FA/DA/MA register on every interrupt while ensuring that asynchronous handlers can preserve all state they modify.

## 2. Comparison and design rationale
- x86-64 hardware saves instruction/flags/privilege-return state and, on privilege transition, switches to a privileged stack; general registers are normally saved by software. The Intel manual describes the interrupt stack frame and IRET restoration.
- AArch64 hardware saves the return address and prior PSTATE in ELR_ELx/SPSR_ELx and records syndrome/fault address in system registers; general-purpose registers are saved by software in the handler.
- RISC-V trap entry records EPC, cause, status and optional trap value in CSRs; general registers are software-managed.
- NEXSUS adopts this efficient minimal-entry principle, but improves nesting robustness with a hardware-managed, bounded per-core context stack rather than relying on a single EPC/STATUS bank that a nested exception could overwrite.

## 3. Hardware Exception Context Stack (ECS)
Each core implements an eight-entry minimum ECS in core-local protected storage, independent of application RAM, Data RAM, L1–L4, SPM0 and the software exception stack.

Each entry is 128 bytes, 64-bit aligned, and hardware-managed. Eight entries consume 1 KiB/core.

### 3.1 Entry layout
| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0x00 | 8 | SAVED_PC | Precise return/restart address |
| 0x08 | 8 | SAVED_STATUS | Prior privilege and interrupt/control state |
| 0x10 | 8 | CAUSE | INT flag, code, subcode and validity flags |
| 0x18 | 8 | BADADDR | Fault address when valid |
| 0x20 | 8 | EXCINFO | Supplemental fault/access information |
| 0x28 | 8 | RETSTATE | Return/restart policy and packet state |
| 0x30 | 8 | IRQ_SOURCE | Source ID / event identity when asynchronous |
| 0x38 | 8 | CLAIM_TOKEN | IRQ controller claim token; zero for non-IRQ |
| 0x40 | 8 | PREV_FRAME | Previous ECS slot/depth and integrity metadata |
| 0x48 | 8 | ENTRY_FLAGS | Frame type, privilege transition, nesting and validity |
| 0x50–0x7F | 48 | RESERVED | Must be zero on entry; future architectural use |

ECS is not a general register save area. It stores control/diagnostic state only.

### 3.2 Entry atomicity
- Hardware reserves the next ECS slot and captures all required fields as one architectural entry operation.
- No handler instruction executes before the frame is marked valid and the CPU has entered the target privilege/handler state.
- The prior IE state is captured; asynchronous IRQ acceptance is disabled during the initial entry prologue.
- EPC/CAUSE/BADADDR/EXCINFO CSR reads refer to the top ECS frame. Nested entry pushes a new frame; it does not overwrite the outer frame.
- Handler software may inspect/update only the top frame through the defined CSR window.
- A frame is released only by successful IRET or fatal recovery; software cannot arbitrarily pop it.

## 4. Nesting and depth
- Minimum ECS depth: 8 entries/core.
- Synchronous exception entry has priority over maskable IRQ acceptance.
- IRQ nesting is disabled during the initial prologue. The handler may re-enable eligible higher-priority IRQs after its software save frame is complete.
- Priority threshold and source mask rules still apply.
- Each nested event consumes a new ECS slot. Outer entries remain immutable except for explicitly writable return fields.
- At depth 8, another exception/IRQ cannot overwrite an existing frame. It enters the double-fault/fatal path using the emergency recovery record.
- Implementations may provide a deeper ECS, discoverable through CONFIG; software must work with depth 8.

## 5. General register preservation
NEXSUS has independent banks:
- RA0–RA31: integer
- FA0–FA31: floating point
- DA0–DA31: data/staging
- MA0–MA31: 256-bit vector/matrix

Hardware does not automatically spill these banks on ordinary exception entry.

### 5.1 Required handler contract
- An asynchronous handler must preserve every architectural register it modifies that may contain interrupted-program state.
- The ABI defines an interrupt-handler calling convention distinct from an ordinary function convention.
- Compiler-generated handler prologues save the required register banks before calling ordinary code or enabling nested IRQs.
- A handler may use a documented minimal clobber set only when the interrupt source/entry contract explicitly guarantees that set is not live or must be preserved.
- User/low-privilege code cannot select or modify the kernel exception spill area.

### 5.2 Bank-selective preservation
Save only the banks/register ranges the handler can touch:
- Integer-only timer/IPI handlers normally need RA preservation, plus any DA/FA/MA registers used by called code.
- FP handlers preserve touched FA state and FSTATUS/FCAUSE as required.
- Vector/matrix handlers preserve touched MA registers; each register is 256 bits, so blanket MA spilling is especially expensive.
- Lazy FP/vector state management may be added by the OS, but the baseline handler must not assume the interrupted bank is disposable.

The software spill frame records a bank-valid/save mask and register payloads. Frame layout is ABI-defined, not hardwired into the ECS.

## 6. Privileged exception stack
Each core has a privileged **KESP** (Kernel Exception Stack Pointer) and **KELIMIT** bound. KESP addresses a protected, bounded region in the existing Data RAM domain; it is not a new memory type. On transition from PL0 to PL1/PL2, hardware switches to the configured per-core exception stack before the first handler instruction.

- The interrupted application stack pointer is preserved in the software-visible exception frame metadata or a dedicated saved-stack field.
- Same-privilege interrupts use the current privileged exception stack, with a new software frame; nested handlers must not overwrite prior frames.
- Stack bounds/alignment are checked before entry. Invalid KESP or insufficient emergency space causes double-fault handling.
- The exception stack is per-core and must not be shared by concurrent cores.
- The stack is protected Data RAM, not SPM0 (which remains execution workspace, not a LIFO stack). SPM7 is reserved for the temporary exception workspace described in this document.

## 7. Precise exception behavior
- Faulting instruction side effects are not architecturally committed unless the instruction explicitly defines partial completion.
- SAVED_PC identifies the faulting instruction for restartable synchronous faults; for asynchronous IRQ it identifies the next instruction boundary to resume.
- RETSTATE records packet/EXT continuation details where needed, so IRET can resume at a valid instruction boundary.
- EPC/SAVED_PC may be changed by privileged software only when cause flags permit emulation/skip/recovery.
- For a faulting multi-lane/vector operation, architecturally visible state is all-or-nothing unless the opcode explicitly defines restartable partial progress and exposes progress state.

## 8. IRET semantics
IRET is a privileged, frame-aware return:
1. Validate current ECS top frame, integrity metadata and return privilege.
2. Ensure source-specific IRQ completion/acknowledgement requirements are satisfied. For IRQ, IRQEOI remains a separate controller operation; IRET must reject return while an owned claim remains active unless platform policy explicitly permits deferred completion.
3. Restore saved PC and prior STATUS/privilege/interrupt state.
4. Restore prior stack selection/pointer as required by privilege transition.
5. Pop exactly one ECS frame.
6. Resume at SAVED_PC/validated return target.

IRET does not automatically restore RA/FA/DA/MA payloads. The handler/compiler restores its software spill frame before IRET. IRET cannot be used as ordinary RET.

## 9. Double-fault and emergency recovery
- Double fault occurs when exception entry itself cannot complete, ECS overflows, exception stack bounds fail, or a fatal exception occurs while servicing another exception.
- A separate per-core emergency record (not part of the normal ECS ring) captures at least current PC, original top-frame index, double-fault cause and entry-failure flags.
- Fatal vector is entered with maskable IRQs disabled and a dedicated emergency stack/area.
- No attempt is made to unwind arbitrary partially written software spill frames.
- Platform may reset the core or enter a machine-check monitor if emergency recovery also fails.
- Double-fault record is sticky until privileged clear/reset and is readable for diagnostics.

## 10. Context switching is not interrupt entry
A process/thread context switch is an OS scheduling operation, not the hardware interrupt frame.
- The scheduler saves/restores the full ABI-required thread state, including RA/FA/DA/MA as needed, memory-domain context and relevant CSR state.
- An interrupt may trigger a context switch, but the hardware ECS frame remains the short-lived record for the interrupted execution.
- The OS must not treat an ECS slot as a persistent thread context.

## 11. Provisional control registers
| CSR | Access | Purpose |
|---|---|---|
| KESP | privileged R/W | Per-core exception stack pointer |
| KELIMIT | privileged R/W | Lower/upper bound descriptor or stack limit |
| ECSDEPTH | R/O | Current ECS nesting depth |
| ECSCAP | R/O | Implemented ECS capacity (minimum 8) |
| ECSCTRL | privileged R/W | Controlled diagnostics/overflow policy; no arbitrary frame pop |
| DFCAUSE | R/O | Double-fault cause |
| DFPC | R/O | PC captured on double fault |

Exact CSR IDs will be allocated in the CSR map after field semantics are frozen.

## 12. Baseline decisions and open points
**Baseline selected:** minimal hardware frame + 8-entry core-local ECS + SPM7 depth-banked exception workspace + software bank-selective spill + privileged per-core exception stack + dedicated double-fault record.

**Still to specify:** exact stack CSR encoding/bounds model; frame integrity mechanism; nested same-privilege stack frame ABI; whether ECS depth may be 16+ in high-end cores; FP/vector lazy-state ownership; exact IRET validation/error behavior; reset/debug interactions.


## 13. SPM7 exception workspace

SPM7 is the exception-entry temporary workspace. No additional ESCR register bank is introduced.

- SPM7 is 8 KiB per core, consistent with the SPM bank baseline.
- The 8 KiB exception workspace is divided into eight 1 KiB slices, one slice for each minimum ECS nesting level.
- Hardware selects the active slice from the ECS depth before the first handler instruction. Nested entry selects the next slice and cannot overwrite the outer handler's temporary values.
- The active slice is directly addressable through the SPM7 exception window; the handler does not need to consume an RA register merely to locate its initial scratch storage.
- SPM7 exception slices are reserved while exception handling is active and are not simultaneously available to interrupted application code.
- On IRET, the corresponding slice is released for reuse. Its contents are unspecified after release.
- SPM7 is temporary bootstrap/spill workspace, not the persistent kernel exception stack and not a replacement for the software save frame on KESP.
- The 1 KiB per-level slice is sufficient for initial scratch preservation and small prologue metadata. Larger RA/FA/DA/MA save sets use the bounded privileged exception stack.

This reuses existing SPM capacity, avoids extra architectural registers and keeps nested exception scratch state isolated by depth.


## 14. Register save/restore integration

The exact interrupt save masks, variable-size Data RAM software frame, SPM7 use, and full task-context contract are defined in **NEXSUS-CPU-CONTEXT-SAVE-RESTORE-001.md**. ECS remains control metadata only; it does not duplicate RA/FA/DA/MA payload. KESP/KELIMIT delimit the protected Data RAM save-frame stack. SPM7 supplies a depth-selected temporary slice and is not the persistent save area.
