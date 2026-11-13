# NEXSUS CPU PX Manager — P0–P7 Instruction Page Pool
**Document ID:** NEXSUS-CPU-PX-MANAGER-001  
**Status:** Architecture baseline proposal  
**Date:** 2026-11-13

## 1. Fixed definition

- There are exactly **eight instruction pages: P0–P7**. P8 does not exist.
- Each page is **2 KiB**; total PX instruction-page capacity is **16 KiB/core**.
- PX pages contain **executable application/instruction code only**. They are not task context storage, data RAM, or register-image storage.
- P0 is the current execution page. P1–P7 are page-pool resources that can hold active-task continuation code, prefetched code, or code belonging to another scheduled task.
- The architectural instruction fetch stream is **64-bit aligned**. Page assignment/refill must preserve instruction alignment and page-boundary rules defined by the ISA.

## 2. PX Manager responsibility

PX Manager is the logical controller responsible for the P0–P7 pool. It coordinates with Task Scheduler, Fetch Engine, and Context Manager; it does not replace them.

Responsibilities:
1. Track each page's owner task, code-region identity, generation, and valid byte range.
2. Allocate free pages to a task's executable stream or code block.
3. Request code refill from App-RAM / instruction backing storage.
4. Track refill completion and make a page `READY` only after all required bytes and metadata are valid.
5. Promote a ready page to the active P0 role at a legal instruction boundary.
6. Release, recycle, or reassign pages after the previous owner no longer references them.
7. Prevent stale task/page mappings from being used after reassignment.
8. Coordinate page availability with task scheduling so a task is selected only when its next executable segment is ready (or a defined fetch-stall policy applies).

PX Manager must not copy application code into SPM register-context slots. Code pages and register images are different resource classes.

## 3. Page state machine

Each page has one state:

| State | Meaning |
|---|---|
| `FREE` | No current allocation; may be assigned |
| `ALLOCATED` | Assigned to a task/code stream; not yet fetch-complete |
| `FETCHING` | Refill transaction is in progress |
| `READY` | Valid executable contents available |
| `ACTIVE` | Currently used as P0 execution page |
| `RETAINED` | Contents preserved for a task continuation or near-future use |
| `INVALIDATING` | References are being drained before reuse |

Legal high-level transitions:

`FREE → ALLOCATED → FETCHING → READY → ACTIVE`

and, for non-active pages:

`READY ↔ RETAINED → INVALIDATING → FREE`

A refill failure returns the allocation to a defined error/retry path; it must never mark incomplete code as `READY`. P0 replacement occurs only at an instruction-safe boundary, with the next PC and page mapping committed atomically.

## 4. Page allocation and task scheduling

P0–P7 are a **shared page pool**, not eight permanently assigned task IDs. Example allocation (illustrative):

- Task-A: P0 active, P1 continuation/prefetch, P5–P6 retained code.
- Task-B: P2–P4 ready code segments; can be scheduled when its context is restored and its entry/continuation page is ready.
- Task-C: P7 staged code; can be promoted when a page becomes available.

The exact allocation is dynamic. The scheduler may keep a task's next code segment ready while another task executes. A page is not reassigned merely because a task is descheduled: reuse requires the page reference/continuation metadata to be safely detached or saved.

When a task is preempted:
- Save its execution PC/page offset and page mapping references in its context metadata.
- Keep its code pages resident if useful and capacity permits.
- Otherwise invalidate/release its code pages only after the continuation can be reconstructed from backing application code.
- Save architectural registers through Context Manager to its SPM resident slot or protected Data RAM context.

When a task resumes:
- Context Manager restores the register image and execution metadata.
- PX Manager ensures the next instruction page is `READY`.
- Scheduler dispatches only when both context and code readiness satisfy the dispatch contract.

## 5. Context Manager integration (register image ↔ SPM)

Context Manager owns architectural register save/restore; PX Manager owns instruction-page residency. They share a task identity and context-generation token.

On task switch-out:
1. Reach the defined preemption/exception-safe point.
2. Capture PC, status/control state, page/offset continuation, and scheduler-visible metadata.
3. Store RA0–RA31, FA0–FA31, DA0–DA31, and MA0–MA31 register image into the task's SPM3–SPM6 resident context slot (or spill to protected Data RAM if no slot is available).
4. Mark the context valid only after the full image and header are committed.
5. Notify PX Manager that the task is no longer executing; pages may remain retained or become reclaimable according to references.

On task switch-in:
1. Scheduler selects a READY task.
2. Context Manager validates task ID, generation, and context integrity; restores the register image and control/PC metadata from SPM (or Data RAM).
3. PX Manager validates the continuation page and ensures it is `READY`.
4. Dispatch begins at the restored PC/page offset.

**SPM residency does not imply code-page residency**, and code-page residency does not imply register-context residency. Both must be independently valid.

## 6. Dispatch readiness contract

A task is dispatch-ready only if all required conditions are true:
- task state is `READY`;
- a valid context exists (or a defined first-entry context can be initialized);
- PC and page/offset continuation are valid;
- the required instruction page is `READY` or `ACTIVE`;
- memory-protection and page ownership checks pass;
- no unresolved context transfer or page invalidation affects the task.

This contract permits overlapped work: while Task-A executes P0, PX Manager can refill or stage Task-B code in P2–P4; Context Manager can independently keep Task-B's register image resident in SPM. The scheduler then minimizes switch latency by choosing tasks whose **context and code are both ready**.

## 7. Resource and sizing summary

| Resource | Count / size | Role |
|---|---:|---|
| PX pages | P0–P7: 8 × 2 KiB | Executable code |
| PX total | 16 KiB/core | Instruction page pool |
| Register banks | 4 × 32 entries | RA/FA/DA/MA architectural state |
| Register payload | 1,792 B | Context image |
| Context header | 64 B | Context metadata |
| Resident context slot | 2 KiB | Register image + header |
| SPM3–SPM6 | 4 × 8 KiB | 16 resident context slots/core |

## 8. Non-goals and safeguards

- PX is not a data cache and does not contain task data.
- PX pages do not replace App-RAM or Data-RAM backing storage.
- PX pages are not directly interchangeable with SPM slots.
- Task creation is not limited by the eight PX pages; pages are reusable resources.
- The sixteen SPM resident contexts are a fast-residency limit, not a total task limit.
- Page replacement and context replacement are separate decisions, coordinated by task identity and generation.
- Precise cycle costs, refill latency, arbitration, and hardware implementation remain simulation/RTL validation work.

## 9. Next design stage

Define PX allocation policy and arbitration:
- task priority / deadline;
- next-page prediction;
- refill queue ordering;
- retained-page replacement;
- P0 promotion boundary;
- simultaneous context restore and code refill;
- fairness and starvation prevention.

This document establishes the resource roles and correctness contract, not final silicon timing.


## 10. Clarification — equal shared physical slots

**Correction to the provisional wording in Sections 1–4:** P0 is not a permanently designated active page. P0–P7 are eight equal physical slots in one shared, dynamically managed pool. A task may execute from any valid mapped slot; the instruction PC and logical-page mapping identify the next code location. No mandatory promotion or copy into P0 is required.

The earlier state label ACTIVE should be interpreted as a page currently referenced by instruction fetch, not as a special privilege exclusive to P0. Multiple slots may be fetch-referenced over a task's execution stream, subject to the fetch implementation's mapping rules. The OS requests allocation/mapping/release; hardware enforces permissions, generation checks, in-flight reference draining, and atomic mapping publication.

For the OS command family, descriptor fields, context handoff, and dispatch protocol, see [OS / PX / Context Control Interface](NEXSUS-CPU-OS-PX-CONTEXT-INTERFACE-001.md). That document supersedes any implication here that P0 alone is the active execution destination.


## 11. SPM0 double-bank instruction feed (architecture update)

**This section supersedes earlier statements that describe SPM0 as a 2 KiB workspace or PX as directly feeding a single 2 KiB execution page.**

SPM0 is now a **4 KiB code execution workspace**, split into two independently controlled 2 KiB banks:

- SPM0-A: 2 KiB
- SPM0-B: 2 KiB
- Combined SPM0 capacity: 4 KiB

The two banks operate as a ping-pong instruction buffer. While the CPU fetches/executes instructions from one bank, PX Manager may fill the other bank with the next logical code page. At a legal page boundary, hardware switches the active bank if the next bank is READY. The bank that has become inactive/consumed is then available for the following refill.

The bank roles are dynamic; A and B are not permanently assigned to CPU or PX. Each bank has an independent state such as EMPTY, FILLING, READY, ACTIVE, and DRAINING. A bank must never be overwritten while instruction fetch or execution still references its contents.

### 11.1 PX data path

```text
PX P0–P7 shared page pool
          |
      PX Manager
          |
    +-----+-----+
    |           |
 SPM0-A       SPM0-B
  2 KiB        2 KiB
    \           /
     CPU instruction fetch
```

PX P0–P7 remain the backing/residency pool of eight equal 2 KiB physical code slots (16 KiB/core total). SPM0-A/B are the active double-buffered execution workspace. They are distinct resource layers: PX pool slots are not the SPM0 banks.

PX transfers **instruction code only** into SPM0. It does not feed RA/FA/DA/MA register banks, task data, or register context images. Register context save/restore remains the responsibility of Context Manager and the designated context storage resources.

### 11.2 Automatic full-page transition

When a logical code page supplies its full 2 KiB of valid instruction bytes, the next logical page follows automatically. No in-band CPU instruction is required for a full page boundary.

While one SPM0 bank is active, PX Manager prepares the next page in the other bank. At the boundary, the hardware changes the active-bank selector atomically, provided the next bank is READY and its task/generation/logical-page mapping is valid. The consumed bank becomes eligible for refill.

The intended steady state is:
1. CPU consumes SPM0-A while PX fills SPM0-B.
2. CPU switches to SPM0-B when the boundary is reached.
3. PX fills the now-free SPM0-A with the following page.
4. CPU switches back to SPM0-A, and the cycle repeats.

This overlap aims to hide code-page transfer latency. It does not guarantee zero stalls unless measured refill service time, source-memory latency, arbitration, and available execution time permit the next 2 KiB to be ready before the bank switch.

### 11.3 PX_NEXT and PX_END metadata markers

`PX_NEXT` and `PX_END` are **PX Manager metadata/control markers**, not CPU ISA instructions.

- They are not encoded as executable instructions.
- They are not copied into SPM0-A or SPM0-B.
- The CPU never decodes or executes them.
- They consume no instruction bytes and no 64-bit instruction slots.
- PX Manager reads them from the task's code-page/region metadata.

Semantics:

| Marker/condition | PX Manager action |
|---|---|
| Full 2 KiB valid page, no terminal marker | Automatically continue to the next logical page |
| `PX_NEXT` before 2 KiB is filled | End the current logical page at its declared valid-byte boundary and continue at the next logical page |
| `PX_END` before 2 KiB is filled | Mark the task code stream as ended at the declared valid-byte boundary; do not request another page for sequential continuation |

The markers describe code-stream/page metadata. They are not arbitrary control-flow instructions. Normal branch/call/return targets remain governed by the architectural PC and logical code mapping. A branch to another logical page must resolve through the mapping system and cannot be inferred from sequential page continuation alone.

### 11.4 Partial-page validity and alignment

Each page descriptor carries a valid byte count. The valid range must be checked against instruction alignment and the code-region bounds. With 64-bit instruction alignment, executable instruction bytes must end on a legal 8-byte boundary unless a future variable-length encoding specification explicitly changes that rule.

Unused tail bytes are not copied as executable code and must never be fetched. For a partial final page, PX_END identifies the end of the code stream; for a partial intermediate page, PX_NEXT identifies the next logical page. Full pages need neither marker.

The marker metadata is validated before a bank is published READY. A malformed marker, invalid byte count, misaligned boundary, missing continuation mapping, or stale task generation raises a defined PX/code-stream fault; it must not cause execution of padding or stale bytes.

### 11.5 Refill and boundary safety

- A bank becomes READY only after all declared valid bytes and its metadata have been transferred and validated.
- Bank switch is atomic at an instruction-safe boundary.
- No partial or FILLING bank may become ACTIVE.
- If the next bank is not READY at the boundary, the fetch stream stalls or raises the configured refill-wait event; the CPU may schedule another DISPATCH_READY task.
- PX Manager must not overwrite a bank with outstanding fetch references.
- On task switch, both SPM0 bank tags (task ID, generation, logical page ID, valid range) must be saved, invalidated, or safely detached according to the context protocol.

### 11.6 Open timing parameters

The 4 KiB SPM0 size and 2×2 KiB bank organization are the current architecture proposal. Refill latency, copy bandwidth, source-memory contention, bank-switch latency, prefetch distance, and arbitration policy remain simulator/RTL parameters. The idealized 64 B/cycle transfer rate implies 32 payload cycles for 2 KiB, excluding all overhead; this is a lower-bound calculation, not a guaranteed refill time.



### Full-page task termination

If the final task page is exactly 2 KiB, it needs no PX_END marker. The code-region descriptor carries an explicit stream-end/final-page flag (`stream_end=true` or equivalent code-region length metadata). PX_END remains reserved for a partial final page. A full non-final page continues automatically to the next logical page.


## 12. L0I task-based code staging (architecture update)

The application-code path now includes a dedicated 64 KiB L0I before the PX pool:

```text
App RAM -> L0I (64 KiB) -> PX P0–P7 (8 x 2 KiB) -> SPM0 (4 KiB, 2 x 2 KiB)
```

### 12.1 L0I role and data width

- L0I is an application-instruction cache/staging level; it contains executable application code only, not task data or register images.
- Its proposed capacity is 64 KiB per core, organized as 32 logical 2 KiB page regions for the initial model.
- The baseline App-code transfer path is a single 64-bit (8-byte) read lane. One transfer beat carries one 64-bit instruction word. The number of beats per cycle, clock relationship, outstanding request depth and arbitration latency remain configurable and are not frozen by the lane width.
- Multiword/multilane reads are excluded from the baseline. A future four-lane option means four independent 64-bit paths (256 bits aggregate) and requires additional ports, routing, buffering and arbitration; it is a separate simulator experiment, not an assumed current capability.
- L0I is not an execution bypass: code still enters the PX pool and then SPM0 before instruction execution.

### 12.2 Incremental App RAM fills

L0I is filled progressively in chunks rather than waiting for a complete 64 KiB refill. The OS identifies task/code regions and gives the prefetch policy task-aware priorities. App RAM reads may target non-contiguous source addresses. Completed chunks become valid independently; a partially filled region must never be advertised as a complete 2 KiB PX source page unless its valid-byte range and page metadata explicitly describe a legal partial page.

### 12.3 Task-based L0I-to-PX transfers

L0I-to-PX selection is not a sequential address walk. The OS chooses which task and logical code pages should be staged, including pages whose App RAM source addresses are far apart. It submits requests containing task ID/generation, logical page ID, source code-region/address, valid byte count, stream-boundary metadata and priority/deadline hints.

PX Manager:
- validates task ownership, generation, code-region bounds and executable permissions;
- checks whether the requested source page is fully valid in L0I;
- allocates an available P0–P7 physical slot;
- copies the selected logical 2 KiB page (or its declared valid partial-page length) into PX;
- validates PX_NEXT/PX_END/full-page continuation metadata;
- publishes the PX page READY atomically only after data and metadata are complete.

The OS owns scheduling policy and task/page priority. PX Manager owns hardware safety, physical slot allocation, transfer execution, completion state and protection against stale or unauthorized requests. OS does not directly write executable bytes into SPM0 or bypass PX validation.

### 12.4 Independent pipeline stages and queues

Model three independently progressing stages:
1. App RAM -> L0I chunk-fill queue;
2. L0I -> PX task/page-transfer queue;
3. PX -> inactive SPM0 bank refill queue.

Each stage has its own request, in-flight, completion and error state. A downstream stage may consume already-valid data while an upstream stage continues filling other chunks/pages. Backpressure is applied only to the affected request/resource; do not require the entire L0I to become full before PX work can begin.

The simulator must model queue capacity, service width, source latency, arbitration, contention, task priority, fairness/aging and valid-data dependencies. Do not assume zero latency or unlimited outstanding transfers.

### 12.5 Replacement and task isolation

L0I entries are tagged by task/code-region identity and generation, with logical page/chunk range and valid-byte information. Replacement must not evict data referenced by an in-flight PX transfer. Shared immutable code may be deduplicated only when executable identity and permissions match; otherwise task ownership remains isolated. A stale generation must never satisfy a new task's request.
