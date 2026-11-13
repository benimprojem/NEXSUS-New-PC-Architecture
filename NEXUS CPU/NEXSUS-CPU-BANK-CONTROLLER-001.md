# NEXSUS CPU — Bank Controller Behavior Specification

**Document ID:** NEXSUS-CPU-BANK-CONTROLLER-001  
**Status:** Behavioral architecture baseline; queue depths and cycle timings remain implementation-defined  
**Scope:** Per-bank request queues, multi-bank request admission, local arbitration, read/write turnaround, wide-access completion and independent App/Data RAM progress

## 1. Purpose and boundaries

This document defines how the 8-bank × 64-bit bank-group proposal is serviced after address mapping. It does not define a new ISA instruction, architectural register bank, memory domain, global lock, or coherence protocol.

The controller must preserve the existing contracts in:
- `NEXSUS-CPU-MEMORY-BANK-TOPOLOGY-001.md` — bank grouping and address mapping;
- `NEXSUS-CPU-MEMORY-ACCESS-CONTROL-001.md` — validation, protection, commit and fault behavior;
- `NEXSUS-CPU-SRA-001.md` — arbitration classes, aging and bounded service;
- the CPU ISA and NDC rules — ordering, atomics and visibility.

App RAM and Data RAM have separate physical controller paths. They may progress concurrently and must not share a single global bank queue.

## 2. Controller organization

Each physical bank has a local service queue and local port/arbitration state. A bank group has a lightweight group-request tracker for operations that touch multiple banks.

The logical organization is:

```
Architectural request
        |
  Validate full range
        |
  Bank-map and split into 64-bit slices
        |
  Group admission / descriptor
        |
  +-----+-----+-----+-----+-----+-----+-----+-----+
  | B0  | B1  | B2  | B3  | B4  | B5  | B6  | B7  |
  | Q0  | Q1  | Q2  | Q3  | Q4  | Q5  | Q6  | Q7  |
  +-----+-----+-----+-----+-----+-----+-----+-----+
        |
  Per-bank arbitration and port service
        |
  Group completion / architectural commit
```

A group descriptor tracks the parent request, required bank slices, completed slices, operation class and fault status. It is internal microarchitectural state; it is not a new architectural register or software-visible queue slot.

A request that touches one bank uses that bank's local path. A wide request can create multiple bank subrequests under one parent descriptor.

## 3. Multi-bank admission: all-or-none queue insertion

A multi-bank request must not acquire a bank port or hold a bank lock while waiting for another bank. That pattern can create cross-bank deadlock and head-of-line blocking.

The baseline admission rule is:

1. Complete decode, address, alignment, bounds, ownership and permission validation for the entire architectural access before any bank side effect.
2. Determine every 64-bit bank slice required by the request, including repeated slices to the same bank if the byte range crosses an interleave stripe.
3. Allocate one group descriptor.
4. Reserve queue-entry capacity for all required bank subrequests as one admission decision.
5. If every required queue has capacity, insert all subrequests and accept the parent request.
6. If any required queue lacks capacity, insert none; retain or retry the parent at the controller ingress under backpressure. Do not partially enqueue and then wait while occupying other banks' queue slots.
7. Queue admission reserves queue capacity only. It does not lock a bank port, block unrelated traffic, or reserve the bank for the full lifetime of the parent request.

For a request with multiple slices mapped to one bank, that bank must have capacity for the complete number of required entries before admission succeeds.

This all-or-none rule applies to multi-bank architectural requests. It does not create a global lock: only the affected bank queues participate in the admission decision, and unrelated bank groups/domains continue operating.

## 4. Per-bank scheduling and service

Each bank arbitrates only among requests eligible for that bank. The existing service classes and fairness policy apply locally:

1. **URGENT:** CPU exception/IRQ context-frame traffic, with a bounded budget.
2. **CPU-DEMAND:** normal CPU LOAD/STORE/ATOM.
3. **LATENCY-SENSITIVE:** authorized latency-bound Fabric/Node traffic.
4. **BULK:** MEMXFER beats/chunks and large payload movement.
5. **BACKGROUND:** deferrable maintenance.

The scheduler uses weighted fair service (weighted round-robin or deficit-based equivalent) among active classes, with aging for requests waiting too long. No active class may be assigned zero service indefinitely. URGENT cannot become unlimited strict priority.

A bank conflict delays only requests requiring that bank. Requests queued for other banks may continue, subject to their own ports and shared upstream resources.

Long BULK transfers are serviced in bounded beat/chunk quanta. A transfer may yield between quanta without releasing its architectural range reservation or consuming its completion token. The existing MEMXFER rules remain authoritative.

ATOM requests use the existing atomic serialization mechanism. Once an ATOM operation is accepted into its serialization point, it remains indivisible as required by the ISA; bank arbitration must not split its read-modify-write sequence into independently visible operations.

## 5. Read/write port behavior

The architecture does not assume that a physical bank can read and write in the same cycle.

Each bank implementation declares one of the following capabilities to its controller:
- shared single-direction port;
- separate read and write ports;
- another physically validated port arrangement.

For a shared single-direction port:
- the bank may need a read-to-write or write-to-read turnaround interval;
- direction changes are scheduled in bounded batches;
- aging prevents one direction from starving the other;
- the turnaround interval is a physical implementation parameter, not a fixed ISA latency.

For separate read/write ports, simultaneous service is permitted only to the extent that the physical bank, sense/write circuitry, power and timing validate it. The architectural model must not infer dual-port capability merely from the existence of separate logical queues.

## 6. Wide access completion and architectural visibility

A 128/256/512-bit access remains one architectural instruction even when it is internally split across 2/4/8 64-bit slices.

**Wide LOAD**
- All required slices are tracked by one parent descriptor.
- The destination DA register group is updated only after every required slice has returned successfully.
- If any slice faults, the architectural destination remains unchanged and the existing precise-fault path reports the failure.
- Results may arrive in any bank completion order; bank number does not define architectural ordering.

**Wide STORE**
- The complete byte range is validated before queue admission.
- All required bank subrequests are admitted together or none are admitted.
- The instruction completes only after all required bank writes have reached the controller's defined completion point.
- Ordinary STORE is not thereby promoted to an atomic multi-bank operation. Cross-core visibility and ordering continue to follow NDC and the ISA synchronization rules.
- Physical rollback after a late media/ECC failure is not promised by this document; exact write-failure recovery remains a physical/controller design item.

A 512-bit aligned access to one 64-byte stripe normally touches all eight banks once. A request crossing a stripe boundary can touch a bank more than once and may need additional local service rounds. ISA alignment and fault rules decide whether a particular unaligned access is legal; the mapping model alone does not legalize it.

## 7. MEMXFER integration

MEMXFER continues to use the existing Fabric/domain transaction resources and BULK service class. It does not get a private bank controller or bypass local arbitration.

- Source and target range reservations are checked before accepting the transfer, according to Memory Access Control.
- A transfer is segmented into bounded bank beats/chunks.
- A chunk may touch multiple banks and follows the same all-or-none multi-bank queue admission rule.
- A chunk yields only at a defined chunk boundary; the transfer's source/target reservation remains active while it is paused.
- Other non-conflicting requests may use banks between chunks.
- Target publication, token lifecycle, successful WAIT acquire-completion and failure behavior remain exactly as defined by the ISA/NDC and Memory Access Control specifications.
- A bank-level completion is not equivalent to architectural transfer completion. Only the parent transfer state determines completion.

## 8. Faults, backpressure and progress

- Queue-full is backpressure, not data loss and not a memory-permission fault.
- If a multi-bank request cannot reserve all required queue entries, no bank subrequest is inserted.
- A request already accepted must retain enough parent/child tracking to complete or report a defined fault; it must not silently disappear.
- A bank-local ECC/media error is reported through the parent request. For a wide LOAD, no partial DA result is committed.
- Independent banks and the separate App/Data RAM path continue where resources permit.
- Arbitration aging and bounded service quanta prevent permanent starvation under sustained mixed traffic.
- A controller must not wait while holding a bank port for another bank to become available.

The exact queue depth, group-descriptor count, bank port count, service weights, URGENT budget, turnaround cycles, chunk size and retry policy are implementation parameters. They must be exposed to the simulator as configuration values rather than silently assumed.

## 9. Required behavioral-model tests

| Test | Expected behavior |
|---|---|
| 64-bit request to one bank | Enters and is serviced by that bank only |
| Aligned 512-bit LOAD | Eight child slices, one parent; DA commit only after all eight succeed |
| Aligned 512-bit STORE | All eight bank queue entries admitted together or none |
| One required bank queue full | No partial multi-bank enqueue; ingress backpressure |
| Two multi-bank requests with opposite bank order | No bank locks; no cross-bank deadlock |
| One bank stalled, seven others ready | Other banks continue independent requests |
| Two child slices map to same bank | Admission checks capacity for both local entries |
| Shared-port READ/WRITE alternation | Bounded direction batches and aging |
| Separate read/write ports | Concurrent operation only when capability enabled |
| URGENT burst under CPU/BULK load | Bounded URGENT budget; other active classes progress |
| Sustained BULK MEMXFER | Chunk yielding; reservations persist |
| Wide LOAD child fault | No partial DA architectural commit |
| App RAM refill + Data RAM LOAD | Separate controllers progress concurrently |
| Queue-full then capacity release | Parent request retries/admitted without lost or duplicated children |

## 10. Open implementation parameters

The following are deliberately not frozen:
- per-bank queue depth and whether queue entries are physically unified or split by operation;
- group-descriptor capacity and allocation policy;
- exact atomic queue-admission circuit and retry/backpressure protocol;
- bank service weights, aging threshold and URGENT budget;
- shared-port turnaround cycles or separate-port physical capability;
- wide-request child ordering and result assembly pipeline;
- MEMXFER chunk size and maximum outstanding chunks;
- error recovery after a physical write has partially reached multiple banks.

These parameters belong in the behavioral simulator first, then in RTL/physical validation. They must not be guessed from the 512-bit aggregate datapath width.

## 11. References

- [NEXSUS CPU Memory Bank Topology](NEXSUS-CPU-MEMORY-BANK-TOPOLOGY-001.md)
- [NEXSUS CPU Memory Access Control](NEXSUS-CPU-MEMORY-ACCESS-CONTROL-001.md)
- [NEXSUS CPU Special Register Architecture](NEXSUS-CPU-SRA-001.md)
- [NEXSUS System Fabric](../NEXSUS%20System%20Fabric.md)
