# NEXSUS System IRQ & Exception Architecture — 001

**Status:** Architecture draft / behavior baseline  
**Scope:** CPU synchronous exceptions, asynchronous interrupts, System Fabric event routing, IRQ controller, interrupt return and software-visible state.  
**Related:** `NEXSUS-SYSTEM-NODE-COMMUNICATION-001.md`, `NEXSUS-CPU-ISA-001.md`, `NEXSUS-CPU-INSTRUCTION-ENCODING-001.md`

## 1. Core separation

NEXSUS distinguishes three mechanisms:

1. **Synchronous exception:** caused by the instruction currently executing (illegal instruction, access fault, arithmetic fault, explicit TRAP). It belongs to that CPU execution context and is precise.
2. **Asynchronous interrupt/event:** caused independently of the current instruction (timer, I/O, node completion, Fabric fault/event). It is delivered through the IRQ system and is taken at an architecturally safe instruction boundary.
3. **Task/data transfer:** payload movement is not an IRQ operation. Payload remains in memory and is moved by System Fabric under the applicable descriptor/access rules.

An interrupt is a notification, not a data transport.

## 2. System event path

External and node-originated events follow:

`Node / Peripheral / Fabric → System Event Router → IRQ Controller → selected CPU interface`

- A node never directly injects an interrupt into a CPU core.
- Fabric/Event Router carries a compact event record: source ID, event class, sequence or task token, status/cause, and optional descriptor reference.
- Payload and large completion records remain in memory. The IRQ path carries metadata/reference only.
- IRQ Controller validates source routing and policy, records pending state, and selects eligible target core/cluster.
- CPU observes the interrupt and reads event metadata/descriptor through normal authorized memory access.
- CPU acknowledgement/EOI changes interrupt-controller state; it does not itself transfer payload.

## 3. Event source classes

| Class | Examples | Delivery |
|---|---|---|
| Timer | local timer, system timer, deadline | asynchronous IRQ |
| Peripheral | device ready, input, output completion | Fabric-routed IRQ/event |
| Node task | accepted, completed, failed, canceled | event + task token/status reference |
| Fabric | transfer complete, access denied, route error, timeout | IRQ/event or polling status |
| Software | software-generated interrupt, inter-core notification | IRQ controller |
| CPU fault | illegal instruction, page/domain fault, alignment, arithmetic fault | synchronous exception |
| Explicit trap | TRAP instruction | synchronous exception |

Node task **accepted** and **completed** are separate event meanings. A task completion interrupt must not imply that payload has already been copied into CPU registers.

## 4. IRQ controller model

The IRQ controller is a system component, with a local interrupt interface per CPU/core. A scalable implementation may use hierarchical routing (system router → cluster controller → core interface); this is implementation topology, not a change to the architectural event path.

Each source has configurable or defined:

- source/event ID and enable mask;
- destination affinity (core, core set, or cluster);
- priority;
- trigger mode: edge or level, where supported by the source;
- pending state;
- in-service/active state;
- acknowledgement and end-of-interrupt (EOI) behavior;
- optional coalescing policy for repeated events.

### Pending and active

- **Pending:** event is recorded but not yet accepted by a CPU.
- **Active/In-service:** CPU has accepted the event and handler is executing.
- Acknowledgement/claim identifies the selected event/source and transitions it to active.
- EOI ends service. For level-triggered sources, the source must be deasserted or remain pending according to its level.
- Edge events are latched until accepted/cleared; pulses must not disappear merely because CPU is masked.
- Repeated events may be coalesced only if the source explicitly permits it. Task completion records must preserve token/sequence identity; coalescing IRQ notification cannot erase completion records.

### Masking and priority

- Global CPU interrupt enable controls asynchronous IRQ acceptance.
- Per-source masks and priority thresholds filter eligibility.
- Higher-priority events may preempt a lower-priority handler only when nesting is enabled and policy permits.
- Equal-priority ordering is deterministic (controller-defined source/sequence tie-break).
- Masked events remain pending unless source policy explicitly defines a non-latching event.
- Routing/affinity changes must not silently discard pending events.

## 5. CPU exception and interrupt state

The architecture requires separate state for synchronous exceptions and asynchronous IRQ entry. Minimum conceptual registers/state:

| State | Purpose |
|---|---|
| EPC | instruction address to resume/retry |
| CAUSE | exception/interrupt class and subtype |
| BADADDR | faulting virtual/physical/domain address when applicable |
| STATUS | privilege, interrupt enable, previous enable/privilege, handler state |
| IRQCAUSE / IRQID | accepted interrupt source/event ID |
| IRQPRIO | accepted priority (or equivalent controller-readable state) |
| VECTORBASE | exception/interrupt vector table base |
| EVENTREF | optional descriptor/token reference for event handling |

These are architectural concepts; exact register names, widths, banked context, and CSR encoding remain to be fixed.

## 6. Precise exception behavior

- Exceptions are precise: all older instructions are committed; the faulting instruction and younger instructions do not commit partial architectural state.
- A faulting LOAD/STORE/ATOM does not partially modify destination registers or memory (per the memory operation rules).
- EPC identifies the faulting instruction for retry-capable faults.
- TRAP may define EPC as the instruction after TRAP; this distinction is encoded in CAUSE/exception metadata and must be unambiguous.
- Handler may retry, skip, emulate, or terminate according to exception class and OS policy. Hardware does not silently skip a fault.
- BADADDR is valid only for address-related faults; validity is indicated in CAUSE/status.
- Nested synchronous exceptions during handler execution use a defined nested context or are escalated to a fatal/double-fault path. Exact depth/storage is implementation-defined but must not overwrite the only recoverable frame.

## 7. Interrupt entry and return

At a safe boundary, if an IRQ is eligible:

1. Finish/commit the current instruction.
2. Save the interrupted PC and minimum return state into a privileged interrupt context (or architecturally defined bank).
3. Record IRQ source/priority and previous interrupt-enable state.
4. Disable or adjust interrupt acceptance according to nesting policy.
5. Select vector and transfer control to the handler.
6. Handler claims/reads event metadata and services or defers work.
7. Handler acknowledges/EOIs the source at the defined point.
8. IRET restores saved state and resumes the interrupted instruction stream.

The architecture must support software context save for general RA/FA/DA/MA banks. Hardware automatic save of every register bank is **not** assumed; minimum hardware frame and ABI prologue policy will be specified separately.

IRET is privileged. Normal RET is not an interrupt return and cannot restore interrupt/privilege state.

## 8. Vector model

- VECTORBASE points to a privileged vector table.
- Synchronous exception classes and asynchronous IRQ vectors are distinguishable.
- Vector selection may use a fixed slot or a cause/source-indexed table; table layout and vector stride remain open.
- Handler entry receives enough cause/source metadata to identify the event without guessing.
- Vector address must satisfy instruction alignment and executable-domain permission.

## 9. Memory ordering and visibility

IRQ delivery alone is not a memory synchronization primitive.

For producer → event → consumer:

1. Producer writes payload and descriptor.
2. Producer publishes with the required release/visibility operation.
3. Fabric transports event metadata/reference.
4. Consumer handles event and performs matching acquire/visibility operation before reading published data.
5. Consumer acknowledges/completes according to task protocol.

The precise producer/consumer release-acquire mechanism is domain-aware and must align with the NEXSUS memory consistency model. IRQ arrival does not automatically invalidate caches or make arbitrary memory writes visible.

## 10. Error and overload handling

- Invalid source IDs or unauthorized routing are rejected and recorded; they do not become arbitrary CPU vectors.
- IRQ controller overflow must be detectable (overflow status/counter or fault event).
- Lossless sources require backpressure, queueing, or explicit overflow recovery; coalescible sources may use documented aggregation.
- Fabric delivery failure and node task failure are separate event causes.
- Acknowledgement/EOI mismatch, stale token, duplicate event, and timeout have defined status/error reporting (register details TBD).

## 11. ISA implications (opcode allocation not finalized)

The current system opcode window is `0x94–0xA3`. Candidate architectural operations/state access include:

- privileged CSR read/write or dedicated STATUS/VECTORBASE operations;
- interrupt enable/disable and mask/priority threshold controls;
- IRQ claim/acknowledge and EOI;
- wait-for-interrupt/event;
- IRET;
- exception return/context operations.

No exact opcode is assigned in this document. Encoding will follow after CSR/control semantics and privilege rules are reviewed. Existing `TRAP` remains a synchronous exception instruction.

## 12. Decisions fixed by this baseline

- Node/peripheral/Fabric event path is mediated by System Fabric/Event Router and IRQ Controller.
- IRQ transports metadata/reference only, never payload.
- Synchronous exceptions and asynchronous interrupts are separate architectural flows.
- Precise exceptions and safe-boundary IRQ acceptance are required.
- RET and IRET are distinct; IRET is privileged.
- IRQ notification alone does not establish memory visibility.
- Hardware does not automatically save all general register banks.

## 13. Open decisions

- IRQ source/event ID width and global namespace.
- Controller hierarchy and queue capacity.
- Vector table layout, slot count, stride, and per-core/per-cluster base.
- CSR names, widths, access encoding, privilege modes.
- Minimum hardware exception frame and nested/double-fault behavior.
- IRQ priority width, threshold semantics, nesting defaults.
- Edge/level support and per-source coalescing rules.
- Claim/ack/EOI protocol exact semantics.
- Event descriptor/token format and stale-event handling.
- IRQ opcode allocation in `0x94–0xA3`.
- Timer architecture and inter-core interrupt mechanism.

**Next design step:** define privileged CPU control/status registers (CSR), vector table layout, and minimum exception frame; then assign IRQ/IRET/wait/control opcodes.
