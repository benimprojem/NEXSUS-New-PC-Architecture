# NEXSUS CPU Control & Status Registers (CSR) — 001

**Status:** Architecture draft / privileged state baseline  
**Related:** `NEXSUS-SYSTEM-IRQ-EXCEPTION-001.md`, `NEXSUS-CPU-ISA-001.md`, `NEXSUS-CPU-INSTRUCTION-ENCODING-001.md`

## 1. Purpose and rules

CSR is the privileged control plane for CPU execution, exceptions, IRQs, translation/protection and system observation. It is separate from general register banks RA/FA/DA/MA.

- CSR access is explicit; normal arithmetic instructions cannot implicitly read or modify CSR.
- CSR writes are validated and take effect atomically at an architecturally defined boundary.
- Reserved bits read as zero and must be written as zero unless a CSR explicitly defines otherwise.
- Unsupported or privilege-denied CSR access raises a precise synchronous exception.
- CSR state is per-core unless marked system/cluster scoped.
- CSR access does not transfer node payload; payload stays in memory/Fabric paths.

## 2. Privilege model (initial)

Initial privilege levels:

| Level | Name | Intent |
|---|---|---|
| PL0 | User | Application code; restricted CSR and system access |
| PL1 | Supervisor | OS/kernel, scheduling, memory and IRQ management |
| PL2 | Machine | Firmware, platform initialization and full CPU control |

Privilege is ordered PL0 < PL1 < PL2. A lower level cannot directly enter a higher level by writing STATUS or PC. Transitions occur through exception/interrupt entry, privileged return, or a separately defined controlled call mechanism.

The exact boot/reset privilege and optional virtualization level remain open.

## 3. CSR inventory (architectural names)

### 3.1 Execution and exception state

| CSR | Scope | Meaning |
|---|---|---|
| PC | core | Current instruction/packet address; normally not directly writable while executing |
| EPC | core/context | Return/restart address for exception or interrupt frame |
| CAUSE | core/context | Exception class, subtype and synchronous/asynchronous indicator |
| BADADDR | core/context | Faulting address/domain when address fault applies |
| STATUS | core | Current privilege and interrupt/handler controls |
| VECTORBASE | core | Base address of exception/interrupt vector table |
| EXCINFO | core/context | Supplemental fault metadata and validity bits |
| RETSTATE | core/context | Saved privilege/interrupt state for return |

PC is execution state rather than an ordinary writable CSR. Redirecting execution uses branch/jump or privileged exception-return mechanisms.

### 3.2 IRQ state

| CSR | Scope | Meaning |
|---|---|---|
| IRQENABLE | core | Global asynchronous IRQ acceptance enable |
| IRQMASK | core | Local source mask bitmap/window or mask selector |
| IRQTHRESH | core | Minimum priority eligible for acceptance (threshold semantics defined below) |
| IRQCAUSE | core | Source/event ID of currently claimed IRQ |
| IRQPRIO | core | Priority of currently claimed IRQ |
| IRQPENDING | controller/core view | Read-only pending summary; detailed pending state belongs to controller |
| IRQACTIVE | controller/core view | Read-only active/in-service summary |
| IRQCLAIM | controller interface | Claim/acknowledge highest eligible event; returns source/token |
| IRQEOI | controller interface | End-of-interrupt for active source/token |

IRQCLAIM/IRQEOI are controller operations exposed through CSR or a dedicated system interface. They do not carry event payload. Exact access encoding is not frozen.

### 3.3 System and diagnostics

| CSR | Scope | Meaning |
|---|---|---|
| COREID | core | Read-only core identity |
| CLUSTERID | core | Read-only cluster identity |
| CONFIG | core | Read-only implemented features/widths |
| CYCLE | core | Cycle counter (if implemented) |
| INSTRET | core | Retired instruction counter (if implemented) |
| FSTATUS/FCAUSE | core | FP exception status/cause (future detailed definition) |
| FABRICSTATUS | core | CPU-visible Fabric/event fault summary; no direct payload access |

Counters may be optional; reading absent optional counters returns a defined unavailable result or raises a defined unsupported-CSR exception (policy to be selected consistently).

## 4. STATUS fields (conceptual)

STATUS is a privileged state register. Suggested fields:

| Field | Meaning |
|---|---|
| PL[1:0] | Current privilege (PL0/PL1/PL2; other encoding reserved) |
| IE | Global asynchronous interrupt enable |
| PIE | Previous interrupt enable captured on exception entry |
| PPL[1:0] | Previous privilege captured on exception entry |
| EXL | Exception/handler level indicator |
| NEST | Allow eligible IRQ nesting while in handler |
| Reserved | Read zero; write zero |

Exception entry saves current PL and IE into PPL/PIE, then enters the configured handler privilege and updates EXL/IE according to entry policy. IRET restores saved state from the active exception frame/RETSTATE.

STATUS does not itself identify the interrupt source; IRQCAUSE/IRQPRIO and controller claim state do.

## 5. CAUSE and EXCINFO

CAUSE must distinguish at minimum:

- synchronous exception vs asynchronous interrupt;
- illegal/reserved instruction;
- instruction fetch/access fault;
- data load/store/atomic access fault;
- alignment fault;
- integer arithmetic fault (divide-by-zero, signed overflow where trapping);
- explicit TRAP;
- privilege/CSR access fault;
- double/fatal exception;
- interrupt entry and source/event class.

CAUSE includes a validity indicator for optional BADADDR and supplemental information. Numeric cause IDs and bit layout are intentionally not assigned here.

EXCINFO may carry access type, memory domain, width, operation subtype, or implementation fault code. It must not replace a stable primary CAUSE.

## 6. Vector table

VECTORBASE is aligned to a defined table boundary. Vector selection distinguishes synchronous exception codes and asynchronous IRQ classes/source IDs.

Initial design direction:
- one common exception entry plus optional cause-specific slots;
- IRQ entry can be common or source/priority indexed;
- vector table entries contain executable handler addresses or fixed-size branch stubs;
- each selected target must be aligned and authorized executable memory.

**Not yet fixed:** vector stride, table size, direct vs vectored mode, per-core vs shared table, and whether IRQ source IDs index vectors directly.

## 7. Exception frame and nesting

Minimum hardware-managed return state must preserve:

- interrupted/faulting EPC;
- CAUSE and relevant BADADDR/EXCINFO;
- previous privilege and interrupt-enable state (RETSTATE/STATUS fields);
- IRQ source/token and priority for asynchronous entry.

General RA/FA/DA/MA banks are not automatically saved in full by default. Handler ABI prologue saves the banks it clobbers. A dedicated frame stack or banked context must prevent nested entry from overwriting the only recoverable outer state.

- First-level entry uses a privileged exception frame.
- Nested entry requires a distinct frame/context.
- If no safe frame exists, CPU enters a defined double-fault/fatal path; it must not silently corrupt EPC.
- Exact frame depth, storage (hardware bank vs privileged memory), and overflow path remain implementation decisions.

## 8. Interrupt acceptance and return

1. IRQ Controller marks source pending and routes it to a core.
2. Core checks IRQENABLE, source mask, priority threshold, privilege and nesting policy.
3. At instruction boundary, eligible IRQ is claimed.
4. CPU records EPC/RETSTATE and IRQ metadata, enters handler privilege, and redirects to vector.
5. Handler reads event metadata/descriptor; optionally services or defers work.
6. Handler performs IRQEOI when protocol requires it.
7. IRET restores EPC and prior execution state.

IRQ acceptance does not automatically clear a level source; EOI and source deassertion rules remain source/controller-specific. Masking never implies that pending state is erased.

## 9. IRQ priority threshold

Define priority numbers so larger numeric values mean higher priority.

- IRQTHRESH is a minimum eligible priority.
- An event is eligible when its priority is strictly greater than IRQTHRESH (equal priority does not preempt).
- A reset/default threshold may be the lowest representable value; reset IRQENABLE is disabled until firmware enables it.
- Priority width and tie-break (source ID then sequence) remain open.
- NEST=0 blocks nested asynchronous IRQ acceptance in handler; NEST=1 permits higher-priority events satisfying threshold/masks.

This is a baseline convention; numeric priority width will be set with the controller specification.

## 10. CSR access instruction direction

A CSR access instruction family is required (candidate `CSRR`, `CSRW`, `CSRS`, `CSRC` or a smaller read/write pair). It must specify:

- CSR ID encoding;
- RA operand selector;
- read/write and atomic set/clear semantics;
- privilege check;
- read-only/write-only behavior;
- serialization/fence effect for control changes.

No numeric opcode is allocated here. Candidate placement is SYS opcode window `0x94–0xA3`; allocation follows the complete SYS command list.

## 11. Reset and boot baseline (provisional)

- CPU begins at a platform-defined reset PC in executable App/code memory.
- Initial privilege is PL2 (Machine) for firmware initialization.
- Asynchronous IRQ acceptance begins disabled.
- VECTORBASE is initialized by firmware before enabling IRQs.
- IRQ controller routing/masks and event queues are initialized before source enable.
- Reset vector address and reset CSR values are platform-specific and remain open.

## 12. Decisions in this baseline

- PL0/PL1/PL2 privilege levels.
- CSR is distinct from RA/FA/DA/MA.
- PC is execution state, not a normal writable register.
- STATUS carries privilege and interrupt-entry state.
- EPC/CAUSE/BADADDR/EXCINFO describe precise exceptions.
- VECTORBASE controls privileged vector routing.
- IRQENABLE, IRQMASK, IRQTHRESH, IRQCAUSE/IRQPRIO and claim/EOI interface exist conceptually.
- Larger priority number means higher priority; eligibility is priority > threshold.
- General register banks are software-saved by handler ABI, not fully auto-saved.
- IRET restores interrupt/privilege context; RET does not.
- Reset enters Machine privilege with IRQs disabled (provisional platform baseline).

## 13. Open decisions / next

- Exact CSR ID map, CSR widths, read/write access classes.
- STATUS and CAUSE bit positions/numeric cause IDs.
- Vector table mode, stride, and reset vector.
- Exception frame implementation, nesting depth and double-fault policy.
- IRQ priority width, default threshold and source tie-break.
- IRQMASK addressing for large source namespaces (bitmap vs indexed mask).
- IRQCLAIM/IRQEOI protocol and token encoding.
- CSR opcodes and SYS opcode allocations.
- FP status CSR details.
- Timer/inter-core IRQ registers and architecture.
- User-mode syscall/trap transition ABI.

**Next design step:** freeze CSR bit layouts and vector-table scheme, then allocate SYS/IRQ/IRET opcodes and define timer + inter-core notification.
