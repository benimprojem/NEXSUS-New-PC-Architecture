# NEXSUS CPU — OS / PX Pool / Context Control Interface
**Document ID:** NEXSUS-CPU-OS-PX-CONTEXT-INTERFACE-001  
**Status:** Architecture proposal — command semantics not yet frozen  
**Date:** 2026-11-13

## 1. Purpose

The OS owns task policy: task priority, scheduling, deadlines, admission, and resource requests. CPU hardware provides safe, low-latency mechanisms for PX instruction-page allocation/mapping, code refill tracking, and architectural register-context save/restore.

The design rule is:

> **OS decides which task and code region should run; CPU hardware validates and performs the resource operations.**

P0–P7 are eight equal, dynamically allocated physical page slots. They are a shared pool, not fixed task slots and not a permanent active/inactive hierarchy. Any valid mapped PX slot may supply the next instruction. The PC plus the task's logical-code mapping identifies the next instruction; no rule requires copying code into P0 before execution.

- Eight slots: P0–P7.
- Each slot: 2 KiB.
- Total: 16 KiB/core.
- Contents: executable application code only.
- Task data and register images remain outside PX.

This definition supersedes the earlier provisional description that treated P0 as the unique active execution page.

## 2. Responsibility split

| Function | OS / scheduler | CPU hardware |
|---|---|---|
| Task priority, deadline, fairness | Owns policy | Exposes status/events |
| Select next task | Chooses | Validates dispatch conditions |
| Request PX capacity | Requests | Finds/allocates eligible slot |
| Choose code source | Supplies logical region/source | Checks permissions and performs refill |
| Page-to-code mapping | Requests mapping | Validates and commits mapping |
| Context save/restore timing | Initiates at safe point | Transfers architectural state |
| Page/context integrity | Manages task lifecycle | Enforces ownership/generation checks |
| Final task switch | Requests commit | Performs atomic safe-point transition |

The OS must not be able to bypass page ownership, executable permissions, or context integrity checks. Privileged instructions or protected control registers are required.

## 3. PX page descriptor

Each physical slot P0–P7 has hardware-visible metadata. Proposed fields:

| Field | Meaning |
|---|---|
| valid | Descriptor and contents are valid |
| state | FREE / ALLOCATED / FETCHING / READY / MAPPED / INVALIDATING / ERROR |
| owner_task_id | Current owning task |
| owner_generation | Prevents stale references after task-ID reuse |
| code_region_id | Logical executable region |
| logical_page_id | Task-visible code page identifier |
| source_offset | Backing App-RAM code offset |
| valid_bytes | Number of valid bytes in this slot |
| permissions | Execute and applicable sharing permissions |
| refcount | Number of live mapping/restart references |
| pin_reason | Active execution, near-future PC, explicit OS pin, etc. |
| replacement_age | Replacement-policy metadata |
| transaction_id | Refill/map operation generation |

A page becomes executable/dispatchable only after the complete requested range has arrived and all validation checks pass. Publishing READY is an atomic metadata commit, never an early indication during a partial refill.

## 4. Proposed OS-visible command family

Names below are mnemonic proposals, not frozen ISA encodings. Some may ultimately become instructions, privileged service operations, or command-queue descriptors controlled through CSRs.

| Mnemonic | Proposed behavior |
|---|---|
| PX_ALLOC | Request one or more free PX slots for a task/code region |
| PX_LOAD | Start loading a logical code page from its approved App-RAM backing region |
| PX_QUERY | Read slot state, owner, generation, valid byte range, and error status |
| PX_MAP | Map a task logical code page to a physical PX slot |
| PX_UNMAP | Remove a mapping after references are safely detached |
| PX_PREFETCH | Request a future code page without making the task runnable |
| PX_PIN / PX_UNPIN | Protect a page from replacement for a bounded reason/lifetime |
| PX_RELEASE | Release an unreferenced slot to the pool |
| CTX_SAVE | Save the current architectural register image and execution metadata |
| CTX_RESTORE | Restore a validated context into the architectural register banks |
| CTX_QUERY | Query context state and residency (SPM or protected Data RAM) |
| TASK_COMMIT | Atomically commit a prepared task switch at a legal boundary |

PX_ALLOC should be allowed to return BUSY or NO_SLOT; it must not silently evict a pinned or referenced page. PX_LOAD and PX_PREFETCH should be asynchronous-capable: the OS can submit a request, continue other work, and observe completion through status or an interrupt/event.

## 5. Command semantics and safety

### 5.1 Allocation and load

1. OS submits task ID, task generation, logical code-page ID, backing source descriptor, requested byte range, and permissions.
2. Hardware checks privilege, task ownership, executable source permissions, and descriptor bounds.
3. PX Manager selects a free slot or returns a resource status.
4. Refill proceeds; the slot remains non-executable while FETCHING.
5. On successful completion, hardware commits descriptor metadata and publishes READY.
6. On failure, it publishes ERROR with a reason; partial contents are never executable.

### 5.2 Mapping

PX_MAP binds a task's logical code page to a physical slot. It checks owner task/generation, page validity, executable permission, and range. The mapping commit must be atomic from the fetch unit's perspective.

The physical slot number is not the task's code address. The task's PC and logical page mapping select the physical slot. This allows execution from any P0–P7 slot without copying code into a designated P0.

### 5.3 Release and replacement

A slot may be released only when:
- no current instruction fetch or in-flight transaction references it;
- no saved continuation or mapping reference requires it, unless that reference is first detached or made reconstructible;
- it is not pinned;
- ownership/generation metadata is invalidated safely.

Replacement policy should prefer free slots, then unpinned non-current pages with low expected reuse. The OS may provide hints, but hardware must enforce safety. A task's code may remain cached after its register context has been spilled; code residency and context residency are independent.

## 6. Context image interface

The current architectural register image is:
- RA0–RA31: 32 × 64-bit
- FA0–FA31: 32 × 64-bit
- DA0–DA31: 32 × 64-bit
- MA0–MA31: 32 × 256-bit

Register payload: 1,792 bytes. With a 64-byte context header, total is 1,856 bytes, fitting in a 2 KiB context slot.

SPM context residency:
- SPM3–SPM6: 4 × 8 KiB.
- 16 × 2 KiB context slots per core.
- If no resident slot is available, the OS/context subsystem may spill to protected Data RAM.

The context header must include at least task ID, task generation, context format/version, saved PC, status/control state, logical code-page ID and offset, and integrity/validity metadata. The precise header layout remains owned by the Context Save/Restore specification.

CTX_SAVE must commit the context as valid only after the complete image and header are stored. CTX_RESTORE must reject stale generation, invalid format, incomplete save, or failed integrity checks.

## 7. Task switch protocol

Proposed sequence:

1. OS scheduler chooses a candidate task based on policy.
2. At a legal preemption point, current task state is frozen.
3. CTX_SAVE stores the outgoing register image and continuation metadata.
4. PX Manager may retain outgoing code pages or release eligible pages.
5. In parallel where hardware permits, PX Manager loads/maps the incoming task's next code page.
6. Context Manager validates and prepares the incoming context.
7. Dispatch readiness checks task state, context validity, PC/mapping validity, page readiness, permissions, and absence of conflicting invalidation/transfer.
8. TASK_COMMIT atomically changes the architectural task identity and resumes at the saved PC.

Context restoration must not overwrite the outgoing task's live architectural registers before its save has completed. An implementation may add a shadow/staging register image to overlap restore with other work, but that is an optional microarchitectural optimization, not an assumed existing resource.

## 8. Scheduler readiness and fairness

The scheduler should distinguish:
- RUNNABLE: policy permits execution;
- CONTEXT_READY: valid context can be restored;
- CODE_READY: next instruction page is ready and mapped;
- DISPATCH_READY: all hardware preconditions pass.

A high-priority task whose code is still being refilled should not force the core to idle if another eligible task is dispatch-ready, unless its deadline/policy explicitly requires waiting. Fairness counters or aging are needed so a stream of high-priority arrivals cannot starve lower-priority tasks indefinitely.

## 9. Events and observability

Suggested events/status:
- PX_ALLOC_DONE, PX_LOAD_DONE, PX_LOAD_ERROR
- PX_PAGE_EVICTED, PX_MAPPING_FAULT
- CTX_SAVE_DONE, CTX_RESTORE_DONE, CTX_ERROR
- TASK_DISPATCH_READY, TASK_SWITCH_DONE

Suggested counters:
- PX hit/miss and page-ready rate;
- refill bytes and refill wait cycles;
- page evictions and pinned-page pressure;
- SPM context hits and Data-RAM context spills;
- context save/restore cycles;
- task switch cycles;
- dispatch-ready queue depth;
- per-task wait/dispatch latency and starvation/aging metrics.

## 10. Simulation plan

Compare policy variants with identical task traces:
1. no prefetch vs one-page lookahead;
2. context-only prefetch vs code-only prefetch vs both;
3. retain-on-switch vs aggressive release;
4. OS-only replacement hints vs hardware replacement;
5. fixed-priority vs priority plus aging.

Report measured simulation outputs, not estimated wins:
- mean / median / P95 task-switch latency;
- PX hit rate and refill stall cycles;
- context SPM hit rate and spill rate;
- code/context transfer bytes;
- page eviction rate;
- CPU idle cycles waiting for dispatch readiness;
- per-task fairness and starvation.

All cycle results must state refill latency, DRAM bandwidth, arbitration, and overlap assumptions. This document defines interfaces and invariants; opcode encodings, exact CSR layout, and cycle timing remain open.


## 11. SPM0 code workspace and PX metadata protocol

This section updates the earlier SPM0 sizing in the context/interface proposal.

### 11.1 SPM0 is not register context storage

SPM0 is the CPU's active instruction-code workspace. It is **4 KiB total**, organized as two independently managed 2 KiB banks (SPM0-A and SPM0-B). PX Manager fills these banks with executable code. PX does not write RA/FA/DA/MA architectural registers and does not transfer register context images through SPM0.

Register images continue to use Context Manager and the context residency/spill mechanism. SPM0 code residency and task-context residency are independent.

### 11.2 Bank operation

While CPU fetch consumes one SPM0 bank, PX Manager may fill the other. The hardware switches banks at a legal instruction boundary only after the destination bank is fully READY and its ownership, generation, logical-page mapping, permissions, and valid-byte range have passed validation. The consumed bank then becomes available for the next refill.

The intended sequence is A active/B filling, then B active/A filling, alternating continuously. If the next bank is not READY when needed, the fetch stream waits; no partially loaded bank is executable.

### 11.3 PX_NEXT / PX_END are metadata, not instructions

These markers are consumed only by PX Manager from code-stream/page metadata. They are not part of the CPU ISA, are never copied into either SPM0 bank, and never reach the instruction decoder.

- A full 2 KiB valid page continues automatically to the next logical page.
- PX_NEXT marks an intermediate page that intentionally ends before 2 KiB; PX Manager continues at the next logical page.
- PX_END marks a partial final code page; PX Manager closes the sequential code stream and does not request another page as continuation.
- Markers occupy no code bytes and do not consume an instruction slot.

The valid byte count must be explicit in the page descriptor and satisfy instruction-alignment and region-bound checks. Ordinary branches and calls still use logical PC mapping; metadata markers only describe sequential code-stream layout.

### 11.4 Page descriptor additions

Add/confirm these descriptor fields:
- valid_bytes: executable bytes in the page;
- stream_boundary_kind: FULL_PAGE, PX_NEXT, or PX_END;
- next_logical_page_id: required for PX_NEXT or full-page sequential continuation;
- stream_generation: binds metadata to the current task/code image.

The metadata and page contents must be validated and atomically published together before READY.

