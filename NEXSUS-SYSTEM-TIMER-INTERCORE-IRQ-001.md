# NEXSUS System Timer and Inter-Core Interrupt Architecture
**Document ID:** NEXSUS-SYSTEM-TIMER-INTERCORE-IRQ-001  
**Status:** Architecture baseline (register details provisional)  
**Scope:** Monotonic time, per-core deadlines, timer events, inter-core notification (IPI)

## 1. Design principles
- Timekeeping and interrupt delivery are separate: timer hardware produces an event; the System IRQ Controller decides whether/when a core accepts it.
- Timer/IPI notifications carry metadata and tokens, never application payload.
- Shared data is published in memory with release semantics and consumed with acquire semantics.
- Timebase frequency and clock implementation are platform parameters, not ISA constants.
- Every interrupt source has observable pending/active state and defined acknowledgement/completion behavior.

## 2. System timebase
The platform exposes a monotonically increasing 64-bit counter, **TIME**. It advances at a platform-defined constant rate while the timebase is enabled. Software can read it without changing its state.

- TIME is system-wide: cores observe the same counter domain.
- TIME is not wall-clock time. Date/time conversion belongs to firmware/OS.
- Frequency is discoverable through platform configuration/firmware; software must not assume a fixed MHz value.
- TIME wraps modulo 2^64. Deadline comparisons use signed modular difference and are valid only when deadlines are less than 2^63 ticks into the future/past.
- Reads must be coherent 64-bit reads. If an implementation internally splits the counter, hardware provides a stable snapshot.

## 3. Per-core timer compare
Each core has a private **TIMECMP** deadline register and **TIMERCTL** control register.

- TIMECMP contains an absolute TIME-domain deadline.
- TIMERCTL enables/disables the compare and selects one-shot or periodic operation.
- When enabled and TIME reaches the deadline, the timer raises its configured timer event to the System IRQ Controller.
- One-shot: event is generated once; compare becomes disarmed after firing.
- Periodic: a platform/software-defined period advances the deadline. The implementation must avoid silently losing elapsed periods; missed-period status/count is observable.
- Reprogramming TIMECMP clears the old compare-pending condition only according to the timer's documented write/clear semantics; it must not erase an already accepted IRQ in the IRQ Controller.
- A timer event does not directly enter the CPU. Normal IRQ masks, priority, threshold and global IE rules apply.

### TIMERCTL fields (provisional)
| Bits | Field | Meaning |
|---|---|---|
| 0 | EN | Compare enable |
| 1 | PERIODIC | 0 one-shot, 1 periodic |
| 2 | MISSED | Read-only: at least one period elapsed while service was delayed |
| 3 | PENDING | Read-only timer event pending at timer source |
| 7:4 | Reserved | Read as zero |
| 63:8 | Reserved | Read as zero |

Timer-source pending and IRQ-controller pending are distinct. Clearing/servicing one does not implicitly clear the other.

## 4. Timer event lifecycle
1. TIME reaches TIMECMP.
2. Timer source records expiration and emits event metadata.
3. IRQ Controller records pending source/target and applies routing/mask/priority policy.
4. CPU accepts the IRQ at a safe instruction boundary if eligible.
5. Handler claims source, services timer state, programs next deadline if needed, and completes with IRQEOI.
6. Return uses IRET.

WFI may wake on a platform-defined eligible wake source even if global IRQ acceptance is disabled; wake does not imply handler entry. The wake-source policy is discoverable/configurable.

## 5. Inter-core interrupt (IPI)
IPI is a CPU-core notification routed through the System IRQ Controller. It is distinct from Node/Peripheral events and does not bypass the controller.

### Publication protocol
1. Sender writes message data or a descriptor into a shared, permitted memory domain.
2. Sender publishes it with RELEASE semantics.
3. Sender writes an IPI mailbox/notification slot and requests an IPI for the destination core.
4. Controller records/delivers the IPI as an interrupt source for that destination.
5. Receiver accepts and claims the IPI, reads mailbox metadata, then reads shared payload using ACQUIRE semantics.
6. Receiver acknowledges the mailbox sequence and completes the interrupt with IRQEOI.

The IPI contains only source-core ID, destination-core ID, mailbox slot, sequence/token and optional notification class. Payload bytes remain in memory.

## 6. Mailbox and delivery behavior
- Each core has a bounded inbound IPI mailbox with implementation-defined capacity exposed by CONFIG/platform discovery.
- Mailbox entries carry monotonically increasing sequence numbers; sequence wrap is handled modulo the defined width.
- A sender must distinguish **accepted** from **consumed/acknowledged** notifications.
- IPI may be coalesced only when mailbox state preserves all unconsumed entries or an explicit pending bit/sequence makes the coalescing lossless.
- Overflow is never silent: sender receives backpressure/error or receiver exposes an overflow/lost-sequence indicator and recovery path.
- Acknowledging a mailbox entry does not substitute for IRQEOI; mailbox consumption and controller interrupt completion are separate operations.
- Multiple senders are arbitrated by hardware/Fabric; ordering is guaranteed per sender/sequence unless a stronger platform contract is selected.
- Core offline/reset transitions must define whether pending IPI entries are drained, retained, or invalidated and reported.

## 7. IPI and memory ordering
An IPI by itself is **not** a memory fence and does not grant memory access.

- RELEASE publication before IPI request is required for sender data.
- Receiver performs ACQUIRE before consuming the published descriptor/data.
- Shared-memory permissions and ownership remain enforced by the memory-domain/Fabric rules.
- A mailbox token identifies a publication; it is not a pointer permission or capability unless explicitly granted by the memory system.

## 8. CSR interface (provisional IDs)
These are accessed through CSRR/CSRW/CSRS/CSRC; they are not separate opcodes.

| CSR ID | Name | Access | Description |
|---:|---|---|---|
| 0x030 | CYCLE | RO | Core-local cycle counter (may vary by core frequency) |
| 0x031 | INSTRET | RO | Retired instruction counter |
| 0x032 | TIME | RO | System monotonic timebase |
| 0x033 | TIMECMP | RW | Per-core absolute deadline |
| 0x034 | TIMERCTL | RW/RO fields | Per-core timer control/status |
| 0x060 | IPI_SEND | WO | Request notification to a target core/mailbox |
| 0x061 | IPI_STATUS | RO | Send acceptance/error status |
| 0x062 | IPI_MAILBOX | RO/RW | Receiver mailbox metadata/ack window |
| 0x063 | IPI_ACK | WO | Acknowledge mailbox sequence/slot |

IPI_SEND's exact operand packing and mailbox window addressing are platform-defined for now. The architectural contract requires target core, slot/token and sequence to be unambiguous; no payload is embedded.

## 9. Reset and privilege
- TIME reset origin is platform-defined; software must not assume zero after warm reset.
- Timer and IPI CSRs are privileged in the baseline (PL1/PL2); PL0 access is mediated by OS policy.
- Reset disables per-core timer compare and clears local mailbox state unless platform reset policy explicitly preserves it.
- TIME remains system-wide and monotonic across core resets; platform reset may restart it.

## 10. Open implementation decisions
- TIME frequency discovery field and whether a second always-on low-power counter exists.
- Exact periodic timer period encoding and missed-period counter width.
- IPI_SEND bit layout, mailbox capacity, per-core source allocation and acknowledgement window.
- Virtual timer support and timer virtualization under PL1/PL2.
- Timer/IPI source IDs and routing/affinity integration with IRQMASK/IRQPRIO.
- Debug/performance counter access policy.

## 11. Related documents
- NEXSUS-CPU-CSR-001.md
- NEXSUS-SYSTEM-IRQ-EXCEPTION-001.md
- NEXSUS-CPU-ISA-001.md
- NEXSUS-CPU-INSTRUCTION-ENCODING-001.md
- NEXSUS-SYSTEM-NODE-COMMUNICATION-001.md
