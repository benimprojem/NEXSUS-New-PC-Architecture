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
