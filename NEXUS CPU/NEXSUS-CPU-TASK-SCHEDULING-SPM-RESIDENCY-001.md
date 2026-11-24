# NEXSUS CPU Task Scheduling and SPM Residency
**Document ID:** NEXSUS-CPU-TASK-SCHEDULING-SPM-RESIDENCY-001  
**Status:** Architecture baseline proposal

## 1. Scope and fixed memory roles

This document defines same-core scheduling, task state transitions, resident SPM context selection, wake-up, priority changes, and cross-core migration. It reuses the fixed SPM map:

| SPM | Role |
|---|---|
| SPM0 | 2 KiB CPU execution workspace |
| SPM1 | 8 KiB privileged OS workspace and OS-defined syscall exchange |
| SPM2 | 8 KiB user/programmer workspace |
| SPM3–SPM6 | 32 KiB OS-managed resident task-context pool |
| SPM7 | 8 KiB exception workspace; eight 1 KiB depth slices |

SPM3–SPM6 contain sixteen 2 KiB resident context slots per core. Each slot can hold the full 1,792-byte RA/FA/DA/MA payload and the existing 64-byte context header. This is a per-core resident fast-context maximum, not a system-wide task limit. All additional task contexts reside in protected Data RAM.

## 2. Task states

The OS scheduler maintains at least these logical states:

- **READY:** eligible to run when selected by the scheduler.
- **RUNNING:** currently owns the core's architectural execution state.
- **BLOCKED:** waiting for an event, I/O completion, lock, message, or other dependency.
- **SLEEPING:** not eligible until a timer/deadline or explicit wake condition.
- **STOPPED:** not currently schedulable; retained state may remain in Data RAM.
- **EXITED:** execution has ended; resources can be reclaimed after outstanding references and operations are resolved.

State transitions are OS policy. A notification or IRQ makes a condition observable; it does not itself make arbitrary task data visible. Release/acquire synchronization remains required.

## 3. Resident context slot policy

1. A slot is owned by exactly one task identity and generation at a time.
2. A slot is marked valid only after the complete context payload and metadata are stored.
3. A slot may be assigned to a READY, BLOCKED, or SLEEPING task. Residency does not imply schedulability.
4. When all sixteen slots are occupied and another task needs residency, the OS selects an evictable non-running owner, writes its complete context to protected Data RAM, verifies completion, then marks the slot invalid and reusable.
5. Never evict the RUNNING task's only current architectural state, a context being restored, or a slot participating in an incomplete transfer.
6. Prefer retaining contexts of frequently scheduled, latency-sensitive, or soon-to-wake tasks. This is an OS scheduling heuristic, not a hardware guarantee.
7. A task without a resident slot remains fully schedulable from Data RAM. Slot exhaustion must never reject task creation or corrupt an existing context.
8. Context slot ownership metadata includes task ID, generation, valid state, payload size, and integrity/version information. Stale task IDs or generations cannot validate a reused slot.

The OS may choose any replacement policy (for example, recency plus priority), but correctness cannot depend on a particular policy.

## 4. SPM2 user-workspace lifecycle

SPM2 is a single 8 KiB user workspace per core, not sixteen private copies and not part of the register-context pool.

- While a task runs, it owns the user-visible SPM2 contents under the user SPM ABI.
- Before switching SPM2 to another task, the OS preserves the outgoing image if it is live. The baseline preservation destination is that task's protected Data RAM context backing.
- The incoming task's saved SPM2 image is restored before user instructions execute if its workspace is live.
- A task may explicitly relinquish the workspace or declare its contents dead through the OS/runtime ABI; only then may the OS omit the save.
- A task that never uses SPM2 need not allocate an 8 KiB backing image.
- The OS must not use SPM2 as scratch while a user task's live image is the only preserved copy. SPM1 is the OS workspace.
- On migration, a live SPM2 image is first preserved to source-core accessible protected Data RAM or another explicitly shared transfer staging region; the destination core then loads its local SPM2. SPM contents are not coherent or automatically transferred between cores.

The implementation may optimize copying when it can prove a region unchanged or unused, but it must preserve byte-for-byte observable contents.

## 5. Same-core context switch sequence

For Task A to Task B:

1. Enter the privileged scheduler path through the defined exception/context-switch mechanism. SPM7 is used only for exception-entry temporary state; SPM1 is used for OS bookkeeping.
2. Reach a defined architectural boundary and quiesce A so its state cannot change during save.
3. Save A's complete RA/FA/DA/MA architectural context to its assigned SPM3–SPM6 slot, or protected Data RAM if it is not resident. Preserve DA before DA is used as staging; restore DA last, following the context-save/restore ABI.
4. Preserve A's live SPM2 user image to protected Data RAM before SPM2 is reassigned.
5. Update A's task control block and state (READY, BLOCKED, SLEEPING, etc.) only after its saved state is valid.
6. Select B, validate its task identity/generation, PC, privilege state, address-space mapping, memory-domain permissions, and dependency state.
7. Restore B's RA/FA/DA/MA context from its resident slot or Data RAM. Allocate/evict a slot only using the complete-save-before-release rule.
8. Restore B's SPM2 image if live.
9. In parallel with context and SPM2 transfers where independent paths permit, invalidate/replace and refill P0 from B's App RAM instruction stream at B's saved PC and code-domain identity.
10. Install B's controlled PC/STATUS and required execution state. Resume only when register state, SPM2, permissions, and required first P0 instruction(s) are valid.
11. Publish the handoff using the required release/acquire ordering.

Context restore and P0 refill are independent opportunities for overlap, not a fixed-latency promise. Whichever finishes first waits for the other required dependency.

## 6. Wake-up and blocking

- A task enters BLOCKED only after the OS has recorded the exact wait condition and ensured that a completion arriving during the transition cannot be lost.
- Device/node completion is represented by status and descriptor/sequence metadata in the established memory/Fabric path. IRQ notification is not the payload.
- The IRQ handler acknowledges the source according to the IRQ controller protocol, publishes/observes completion with the required memory ordering, and makes the waiting task READY only after its wait condition is satisfied.
- A timer expiry may move a SLEEPING task to READY. Timer interrupt delivery alone does not imply that a task's data dependencies are complete.
- If a task wakes while nonresident, it remains eligible in READY with its context in Data RAM. The scheduler may load it into a free slot or evict another context safely.
- Duplicate or stale wake notifications are filtered using task identity plus wait sequence/generation.

The scheduler must close the lost-wakeup race by registering the wait condition before relinquishing the core and rechecking completion before committing the BLOCKED state.

## 7. Priority changes and selection

Priority is scheduler metadata, not part of the register payload.

- Changing a READY task's priority updates its queue/order metadata; it does not require rewriting RA/FA/DA/MA context.
- Changing a RUNNING task's priority takes effect at the next defined scheduling point unless the OS explicitly requests preemption.
- A BLOCKED task's priority is retained and used when it becomes READY.
- Priority changes do not invalidate a resident SPM slot or move its contents.
- If priority inheritance/ceiling is implemented, effective priority is tracked separately from base priority and restored when the dependency ends.
- The policy for time slices, equal-priority fairness, and starvation prevention is OS-defined; hardware does not assume one universal policy.

## 8. Sixteen-slot pressure and fallback

When all sixteen resident slots are occupied:

1. Keep the currently running task's live architectural state in the execution banks.
2. Choose a non-running, fully saved resident context as an eviction candidate.
3. Write its complete context to protected Data RAM and verify the write/transfer completion.
4. Mark the slot invalid and release it only after successful preservation.
5. Load the newly selected task into the freed slot if beneficial; otherwise restore directly from Data RAM using the established path.
6. If every resident context is in-flight or otherwise non-evictable, defer slot allocation and use Data RAM directly. Never overwrite a live slot.

Task count is limited by OS resources, Data RAM capacity, identifiers, and policy—not by the sixteen SPM slots.

## 9. Cross-core migration

Migration is an explicit OS operation, not an implicit side effect of a task becoming READY.

1. Select a destination core and verify its execution capabilities, permissions, and available local resources.
2. Stop the source task at a safe architectural boundary.
3. Save its complete register context to protected Data RAM. A source-core resident slot may be used as a temporary source, but it is not a destination-core context.
4. Preserve live SPM2 user-workspace bytes to a memory region accessible to the destination.
5. Record task PC/STATUS, address-space identity, memory-domain handles, synchronization state, and any SPM ownership metadata in the task control block.
6. Transfer shared task data using the established Fabric/XFER mechanisms where their supported domains apply. Do not assume XFER directly addresses local SPM banks.
7. On the destination core, restore register state through its local SPM/register transfer paths and load the SPM2 image into that core's local SPM2.
8. Refill destination P0 from App RAM for the task's saved PC and code-domain identity.
9. Publish the new core affinity/ownership only after all required state and mappings are valid. Use release/acquire ordering and the existing IPI notification path as appropriate.
10. Release source-core local resources only after the destination has accepted the context and no source-side operation still references them.

If a task holds a core-local resource that cannot be migrated safely, the OS must retain affinity, release/reacquire the resource, or reconstruct it. Migration must not silently move local SPM contents or assume cache coherence.

## 10. Core affinity and migration policy

A task may be:
- pinned to one core;
- eligible for a selected core set; or
- freely migratable among compatible cores.

Affinity is scheduler metadata. It does not alter the task's architectural context format. The OS must account for core-specific capabilities and local SPM availability before dispatch.

## 11. Required invariants

- Exactly one core may own a task's RUNNING architectural state at a time.
- A saved context has one authoritative valid copy or a clearly defined in-flight transfer owner; no ambiguous dual-writer state is allowed.
- A resident slot is never reused before its previous owner's complete context is safely preserved elsewhere.
- SPM2 is saved before reassignment whenever live; it is restored before user execution.
- SPM1 remains privileged OS space; SPM2 remains user workspace; SPM3–SPM6 remain context slots; SPM7 remains exception workspace.
- P0 is refilled, not context-saved.
- IRQ/IPI notification does not itself provide memory visibility.
- Task state changes and slot ownership publication use release/acquire synchronization.
- DA staging save/restore order remains mandatory.
- No new register bank, memory type, cache level, or ISA opcode is introduced by this scheduling policy.

## 12. Open implementation details

The following remain OS/simulator policy or implementation choices rather than architectural changes:
- exact ready-queue data structure and priority levels;
- time-slice and preemption policy;
- resident-slot replacement heuristic;
- task ID/generation width;
- task control block binary layout;
- whether SPM2 save/restore uses full-image copy or proven dirty-range optimization;
- exact migration acceptance handshake and timeout recovery;
- treatment of non-migratable device/core-local handles.


## 13. SPM access-control reference

The scheduler must enforce the privilege and ownership boundaries in `NEXSUS-CPU-SPM-ACCESS-PROTECTION-001.md`. In particular, it must not expose SPM3–SPM6 context slots to PL0, must assign SPM2 to exactly the currently running task on that core, and must not repurpose SPM7 for scheduling or ordinary OS work. SPM2 ownership and the incoming task's memory permissions must be valid before returning to PL0.


## 14. Memory protection reference

The scheduler must apply `NEXSUS-CPU-MEMORY-PROTECTION-DOMAINS-001.md` during dispatch and migration. Incoming task-private App RAM/Data RAM ranges and shared grants must be validated before PL0 resumes; outgoing ownership and in-flight shared/Fabric operations must be handled before memory is reassigned or reclaimed.


## 15. Stall-triggered automatic task switching (proposal)

This extends the existing OS-controlled task scheduling model with a proposed fast scheduling opportunity: when the current task/core execution stream reaches a qualifying stall, the scheduler may automatically select another READY task rather than leaving execution resources idle.

### 15.1 Trigger and eligibility

Potential stall classes include:
- Data RAM or App-RAM data access waiting for a response;
- unresolved dependency or operand wait;
- execution-resource wait when the task cannot make useful progress;
- another explicitly modeled wait condition with a known wake event.

A short stall is not automatically worth switching around. The scheduler must consider estimated wait duration, switch/restore cost, whether another task is READY, and resource compatibility. Thresholds and prediction policy remain OPEN pending simulation.

A task is switch-eligible only if its state can be preserved at a safe architectural boundary and the candidate task has valid context, permissions, dependencies, and required resources. The current task becomes BLOCKED/WAITING on the exact cause or remains READY if the policy permits; this classification must not be ambiguous.

### 15.2 Context pool capacity (preserved baseline)

The existing fast resident context capacity remains **16 slots per core × 2 KiB each = 32 KiB total**. These are the SPM3–SPM6 resident task-context slots, four slots per SPM. SPM2 remains the 8 KiB user workspace and is not part of this context pool. P0–P7 are App/code pages and must not be confused with task-context slots.

This capacity permits quick context selection among resident tasks; it does not mean 16 tasks execute simultaneously or that task count is limited to 16. Nonresident task contexts remain in protected Data RAM under the established residency policy.

### 15.3 Conceptual switch flow

1. Detect a modeled stall and identify its cause and expected wake condition.
2. Evaluate the stall against switch-cost/benefit criteria.
3. Select a compatible READY task whose dependencies and required resources are currently satisfied.
4. Preserve the outgoing task's architectural context and live SPM2 image according to the existing context-save ABI and ownership rules.
5. Restore the candidate context and its SPM2 image; refill P0 from the candidate's App RAM code at the saved PC.
6. Resume the candidate only when its required state, permissions, mappings, and instruction availability are valid.
7. Keep the waiting task associated with its wake condition; when that condition completes, make it READY using the established wake-up protocol.

This is an optimization proposal layered on the established context-switch sequence, not a relaxation of safe-save, precise-state, or memory-visibility invariants.

### 15.4 Switch-cost safeguards

The design must avoid thrashing when stalls are short or repeated. Candidate policy inputs include minimum stall threshold, predicted wait length, context residency, expected restore/refill cost, candidate readiness, fairness, and resource match. Exact policy, thresholds, and whether a trigger is hardware-assisted, OS-driven, or hybrid remain OPEN.

## 16. Task-aware AppRAM code-page organization (proposal)

AppRAM code pages (P0–P7) may be organized or annotated by task identity and execution flow so the scheduler can quickly identify a candidate task's next code region. The organization is a code-page placement/metadata idea; it does not change the fixed P0–P7 page count, their size, or the established rule that P0 is refilled for the selected task rather than context-saved.

Task-aware code-page metadata could include task identity/generation, code-domain identity, saved PC or region, page residency/validity, dependency/readiness hints, and expected next-region information. The authoritative task PC and access permissions still come from the task's protected state; metadata is advisory and must be validated before execution.

A code-page organizer may group regions by task, continuation, or predicted execution order. The exact mapping and placement algorithm is OPEN. Code-page organization must not be interpreted as dedicating a fixed pair of P pages per task or guaranteeing all pages are resident for every task.

## 17. Combined Global Scheduler: task-level and instruction-level scheduling

The proposed **Global Scheduler** coordinates two distinct scheduling layers using shared task/resource metadata:

- **Task scheduling (TLP):** chooses which READY task/context should run, including stall-triggered switching and wake-up/fairness.
- **Instruction scheduling (ILP):** within the chosen task, finds independent operations, applies dependency analysis and register allocation, and matches operations to existing execution resources and available memory/register-bank capacity (see Cross-Bank Pairing and Graph-Coloring Scheduler Plan).

AppRAM task-aware code-page organization can provide candidate code-location and task metadata to the task scheduler. The instruction scheduler then optimizes the selected task's ready operations. When a task cannot make progress, the task scheduler may choose another eligible task; it must not invent execution capacity or violate the resource/port model.

Conceptual hierarchy:

1. **Global Task & Resource Manager:** tracks READY/BLOCKED/RUNNING state, wake conditions, affinity, residency, priority/fairness, and resource availability.
2. **Task Scheduler:** chooses or switches a task using readiness, stall classification, cost model, context residency, and compatible-resource estimates.
3. **Instruction Scheduler:** performs liveness/interference coloring, dependency-DAG analysis, ready-set construction, and resource-aware matching/grouping.
4. **Execution/Memory admission:** validates the candidate group against existing INT, FP, FMA, VEC, ME512, register-bank, AppRAM, and DataRAM constraints.

These layers should exchange metadata and scheduling outcomes, but task switching and instruction grouping remain separate decisions with separate correctness tests. The intended benefit is adaptive use of both task-level parallelism and within-task instruction parallelism, potentially reducing idle periods compared with a scheduler that only exploits one level. Any claim of superiority over Intel Hyper-Threading or another architecture requires simulator benchmarks and later implementation evidence; this document records a design hypothesis, not a measured result.

## 18. Validation additions for automatic switching and task-aware code pages

| Test | Required behavior |
|---|---|
| Stall with no other READY task | Do not switch to an ineligible task; safely wait/idle according to policy |
| Stall with READY resident task | Candidate can be selected when switch-cost policy allows |
| Stall with READY nonresident task | Residency load cost is included; fallback remains correct |
| Very short stall | Threshold/cost model prevents pathological switching |
| Repeated stall/switch pattern | No scheduler thrashing; fairness maintained |
| Task wake during switch | No lost wake-up; generation/sequence validation succeeds |
| Context save incomplete | Slot is not released/reused; candidate cannot resume prematurely |
| Live SPM2 | Save before reassignment and restore before user execution |
| Task-aware AppRAM page metadata | Task/PC/code-domain information is validated; incorrect metadata cannot dispatch code |
| P0 refill overlap | Context restore and P0 refill may overlap only when independent; resume waits for both required dependencies |
| TLP + ILP combined workload | Task switching and cross-bank grouping preserve correctness and resource limits |
| Fairness/starvation | Policy bounds starvation as specified; exact fairness policy remains OS-defined until chosen |
