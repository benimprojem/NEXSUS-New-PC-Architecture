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


## 14. CSR bit layouts — baseline v0.1

All CSR registers are **64-bit** in the initial architecture. Narrow fields occupy low bits; unused bits are reserved and read as zero.

### 14.1 STATUS

| Bits | Field | Definition |
|---:|---|---|
| 1:0 | PL | 00=PL0, 01=PL1, 10=PL2, 11=reserved |
| 2 | IE | Global asynchronous IRQ enable |
| 3 | PIE | Previous IE captured at entry |
| 5:4 | PPL | Previous privilege captured at entry |
| 6 | EXL | Exception/handler level |
| 7 | NEST | Permit eligible higher-priority IRQ nesting |
| 63:8 | Reserved | Read zero; write zero |

Software may modify IE/NEST only. PL/PIE/PPL/EXL are hardware-controlled on entry/IRET and cannot be forged by ordinary CSR writes.

### 14.2 CAUSE

| Bits | Field | Definition |
|---:|---|---|
| 0 | INT | 1=asynchronous interrupt, 0=synchronous exception |
| 7:1 | CODE | Primary cause code |
| 15:8 | SUBCODE | Cause-specific subtype |
| 16 | BADADDR_VALID | BADADDR contains valid fault address |
| 17 | EXCINFO_VALID | EXCINFO contains supplemental info |
| 18 | RETRYABLE | Faulting instruction may be retried |
| 19 | SKIP_ALLOWED | Handler may advance EPC for this cause |
| 63:20 | Reserved | Read zero |

### 14.3 EXCINFO

| Bits | Field | Definition |
|---:|---|---|
| 7:0 | ACCESS | Fetch/load/store/atomic/CSR/other class |
| 10:8 | DOMAIN | Memory domain selector when relevant |
| 18:11 | WIDTH | Access-width encoding |
| 26:19 | OPCLASS | Instruction/operation class |
| 31:27 | FLAGS | Cause-specific detail flags |
| 63:32 | IMPL | Platform supplemental code |

Non-applicable fields are zero. Enumerations will be defined with the cause table.

### 14.4 IRQ CSR rules

- IRQTHRESH: low 8 bits; larger priority is higher; accept only priority **greater than** threshold.
- IRQCAUSE: low 32 bits source/event ID; upper bits zero.
- IRQPRIO: low 8 bits accepted priority; upper bits zero.
- IRQMASK: indexed 64-source window; bit=1 masks source. Window selector encoding/source namespace width remain open.
- IRQCLAIM: read/claim returns source/token and valid bit; claim side effect occurs once per transaction.
- IRQEOI: write source ID + claim token; stale/invalid token cannot clear another active IRQ.
- STATUS.IE is the canonical global interrupt-enable bit. IRQENABLE, if retained, is a read-only alias—not a second independent control.

### 14.5 CSR ID map (12-bit, provisional)

| ID | Name | Access |
|---:|---|---|
| 0x000 | STATUS | restricted R/W |
| 0x001 | EPC | privileged R/W |
| 0x002 | CAUSE | R/O |
| 0x003 | BADADDR | R/O |
| 0x004 | EXCINFO | R/O |
| 0x005 | RETSTATE | privileged diagnostic; write restricted |
| 0x006 | VECTORBASE | privileged R/W |
| 0x010 | IRQTHRESH | privileged R/W |
| 0x011 | IRQCAUSE | R/O |
| 0x012 | IRQPRIO | R/O |
| 0x013 | IRQMASK | privileged indexed R/W |
| 0x014 | IRQCLAIM | claim/read side effect |
| 0x015 | IRQEOI | write/EOI side effect |
| 0x016 | IRQPENDING | R/O summary |
| 0x017 | IRQACTIVE | R/O summary |
| 0x020 | COREID | R/O |
| 0x021 | CLUSTERID | R/O |
| 0x022 | CONFIG | R/O |
| 0x030 | CYCLE | optional R/O |
| 0x031 | INSTRET | optional R/O |
| 0x040 | FSTATUS | FP status (policy TBD) |
| 0x041 | FCAUSE | R/O |
| 0x050 | FABRICSTATUS | Fabric event/error summary |
| 0x080–0x0FF | platform extension | privilege-gated |

CSR IDs are operands, not primary instruction opcodes.

## 15. Vector table baseline

Use a **common IRQ entry** and a compact **cause-indexed exception table**:

- VECTORBASE is 4 KiB aligned.
- Each entry is one 64-bit handler address (8-byte aligned).
- First 16 entries (0x000–0x078) are exception slots; code 0 is fallback/reserved.
- Common asynchronous IRQ entry: offset **0x100**. Handler obtains source via IRQCLAIM/IRQCAUSE; no vector per system node is required.
- Fatal/double-fault entry: offset **0x180**.
- Remaining region reserved for NMI/fast/platform vectors.
- VECTORBASE may be per-core or shared when permissions/handler validity allow.

## 16. Return/context clarification

- First ISA release uses **IRET** for both exception and IRQ return; CAUSE/RETSTATE identifies frame type. Separate ERET is not required initially.
- RET only returns from a normal call through its RA link register.
- EPC may be changed by privileged handler only for causes permitting skip/emulation; retryable faults default to unchanged EPC.
- IRQEOI releases controller service state; IRET restores CPU context. They are distinct operations.
- Nested handlers use separate frames. Frame storage/depth and double-fault policy remain open.

## 17. Baseline frozen for next ISA pass

**Frozen:** CSR width=64; CSR ID width=12; STATUS/CAUSE fields above; PL0/PL1/PL2; 8-bit IRQ priority; VECTORBASE 4 KiB alignment; exception slots + common IRQ + fatal vector; unified IRET; STATUS.IE canonical.

**Open:** source/token widths; IRQMASK selector; IRQCLAIM/EOI payload layout; numeric cause table; reset PC; exception-frame implementation; CSR instruction encoding/opcodes; NMI/timer CSRs.


### 14.6 Timer and inter-core notification CSRs

The following provisional IDs extend the CSR map; detailed behavior is specified in **NEXSUS-SYSTEM-TIMER-INTERCORE-IRQ-001.md**.

| ID | Name | Access | Description |
|---:|---|---|---|
| 0x032 | TIME | R/O | System-wide monotonic 64-bit counter; not wall-clock time |
| 0x033 | TIMECMP | privileged R/W | Per-core absolute deadline in TIME domain |
| 0x034 | TIMERCTL | restricted R/W | Per-core timer enable/mode and read-only pending/missed status |
| 0x060 | IPI_SEND | privileged W/O | Request an IPI to a target core/mailbox; metadata only |
| 0x061 | IPI_STATUS | R/O | IPI acceptance/error status |
| 0x062 | IPI_MAILBOX | privileged R/W window | Mailbox metadata and receiver-visible sequence |
| 0x063 | IPI_ACK | privileged W/O | Acknowledge a consumed mailbox sequence/slot |

TIME frequency is platform-discovered and is not fixed by the ISA. TIME wraps modulo 2^64; modular deadline comparisons are valid within a half-range (<2^63 ticks). Timer expiration is a source event routed through the IRQ Controller, never a direct CPU bypass. Timer-source pending and IRQ-controller pending are separate states.

IPI is a core-to-core interrupt notification, not a data transfer. Sender publishes shared data with RELEASE before IPI; receiver consumes with ACQUIRE. Mailbox overflow/lost sequence must be observable and recoverable. Mailbox acknowledgement and IRQEOI are separate operations. Exact IPI_SEND packing, mailbox capacity, and source IDs remain platform-defined.
