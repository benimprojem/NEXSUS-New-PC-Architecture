# NEXSUS CPU — Architecture Decision Register 001

**Document ID:** NEXSUS-CPU-ARCHITECTURE-DECISION-REGISTER-001  
**Date:** 2026-11-16  
**Purpose:** Single checkpoint for approved architecture decisions, preventing routine work from reopening settled topics.

## 1. Authority and status rules

This register consolidates current approved decisions. If an older draft conflicts with this register or a newer explicit user decision, the newer approved decision takes precedence; the older draft must be corrected when next touched.

- **FIXED:** Do not reconsider unless explicitly reopened.
- **BASELINE / PROVISIONAL:** Current selected architecture or simulator setting; tune only through a focused measurement.
- **OPEN:** Not yet decided or verified; may be worked on.

A specification is not proof of physical implementation. Simulator results are not RTL, FPGA, or silicon measurements.

### Anti-regression rules

1. Do not restart design discussions for FIXED items.
2. Use current canonical names, not legacy names from older documents.
3. Distinguish architectural definition from implementation and test completion.
4. A failed test does not silently revoke an approved architecture decision.
5. When a decision changes, update this register and its detailed specification.
6. Keep architecture decisions, simulator parameters, and model results separate.

---

## 2. Core execution resources

| Resource | Per-core configuration | State |
|---|---:|---|
| Arithmetic ALU | 8 | **FIXED** |
| Logic Unit | 8 | **FIXED** |
| Compare Unit | 8 | **FIXED** |
| FP64 execution lanes | 6 | **FIXED** |
| Dedicated FMA units | 4 | **FIXED** |
| Vector execution units (VEC) | 2 | **FIXED for current design** |
| ME512 execution unit | 1 | **FIXED** |
| LOAD execution/admission resources | 8 | **FIXED** |
| STORE execution/admission resources | 4 | **FIXED** |

**Scalar integer execution is split into three independent pools:** Arithmetic ALU=8, Logic=8, Compare=8. Arithmetic ALU handles arithmetic only; Logic handles scalar bitwise/boolean/shift/rotate/bit-mask operations; Compare handles scalar signed/unsigned comparisons. This supersedes the older combined INT=8 lane model; do not add these three pools together as a replacement count for a single shared ALU.

**FP64 + FMA is 6+4.** This is not an open 6/8 FP or 2/4 FMA selection. The latest explicit decision supersedes older generic ISA tables that describe only a minimum of two FP units.

**Issue queues:** independent class queues are required for Arithmetic ALU, Logic, Compare, FP64, FMA, VEC, ME512, LOAD and STORE. Queue depths remain OPEN pending scheduler/ROB and workload analysis. A global dispatch/issue selector arbitrates across the queues and respects total issue capacity, dependencies, register-port availability and writeback conflicts.

FMA issue throughput and FMA result/dependency latency are separate concepts and must be modeled separately. The latest latency regression attempt is not validated: workflow [43787870423](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43787870423) failed in regression tests before the latency sweep ran. This does not reopen 6+4.

---

## 3. Architectural register banks

The selected register organization is **32 entries per architectural bank**, with 5-bit selectors.

| Bank | Entries | Entry width | Total capacity | Role |
|---|---:|---:|---:|---|
| RA0–RA31 | 32 | 64 bit | 256 B | Integer, scalar, address |
| FA0–FA31 | 32 | 64 bit | 256 B | Floating point |
| DA0–DA31 | 32 | 64 bit | 256 B | Data staging / transfer |
| MA0–MA31 | 32 | 256 bit | 1 KiB | Vector / matrix operands |

**FIXED rules**
- RB, RC, RD are 32-, 16-, and 8-bit low-bit views of the same RA physical entries; they are not separate banks.
- FP128 uses an even-indexed FA pair.
- ME512 uses an even-indexed MA pair (two 256-bit entries).
- Total RA/FA/DA/MA register payload: 1,792 bytes (1.75 KiB).
- Context header: 64 bytes; complete context image: 1,856 bytes, fitting a 2 KiB resident context slot.
- Register selector width: 5 bits.

**Register connectivity and port-budget analysis (OPEN / verification)**

Initial worst-case logical operand demand, before broadcast/replication:
- RA: Arithmetic ALU 8×(2R+1W) + Logic 8×(2R+1W) + Compare 8×(2R+1W) = **48 read operands + 24 write results/cycle**.
- FA: FP64 6×(2R+1W) + FMA 4×(3R+1W) = **24 read operands + 10 write results/cycle**. FP128 pair operations consume two 64-bit entries.
- DA: up to **8 load-result writes + 4 store-source reads/cycle**, before transfer/XFER demand.
- MA: VEC=2 and ME512=1 are included in the port budget; exact MA-entry reads/writes remain OPEN until every vector/matrix opcode's operand footprint is normalized to 256-bit MA entries.

**FIXED shared access budget:** one core-wide pool of **32 logical register reads + 32 logical register writes per cycle**, shared across RA/FA/DA/MA (not 32+32 per bank). A centralized Register Access Controller (RAC) arbitrates dynamically using ready issue-queue demand, operand counts, bank availability and queue age. The allocator is work-conserving and starvation-resistant; it atomically reserves all source reads and destination writes for an instruction, otherwise that instruction does not issue. Idle capacity in one class is available to another. Pair operations count each physical register entry. Same-destination multiwrite remains prohibited.

These are logical access limits, not a commitment to one monolithic multiported array. Banking, replication, operand broadcast/collectors, bypass and distributed writeback remain implementation choices. Bank conflicts and the physical topology must be modeled separately; no class has a permanently reserved fixed share of the 32R/32W pool.

**Queue depths, physical read/write ports, bank/replica topology, cross-unit connectivity, same-cycle conflict policy, forwarding and writeback arbitration remain OPEN** until a full demand matrix and cycle-level contention tests are complete.

The older SPM/register note contains conflicting 64-entry figures. Those are superseded by the 2026-11-13 architecture revision and must not be copied forward.

---

### 3.1 Issue queue organization

One independently managed issue queue per execution class: Arithmetic ALU, Logic, Compare, FP64, FMA, VEC, ME512, LOAD and STORE. Each queue feeds the units in its class. Global dispatch/issue selection chooses ready instructions across these queues subject to the global issue limit, dependencies, operand availability, register-port budget and writeback constraints.

Queue depth is intentionally **OPEN**. Do not infer queue depth from unit count or conflate issue queue capacity with ROB capacity.

---

## 4. Application instruction path and workspaces

Use the canonical names from NEXSUS-CPU-MEMORY-PATH-AND-NAMING-001. PX, P0–P7, Ping-Pong, SPM0, and L0I are legacy terms, not current architecture vocabulary.

### 4.1 Canonical instruction path

~~~text
Application RAM (App RAM)
  → Code Cache (C0)
  → Code Slots (CS0–CS7)
  → Code Stream Transfer (CST)
  → Execution Buffer (EB)
       ├─ Bank A (2 KiB)
       └─ Bank B (2 KiB)
  → Active Execution Page (selected EB bank)
  → Instruction Fetch / Decode / Execute
~~~

| Resource | Capacity / organization | State |
|---|---:|---|
| Code Cache (C0) | 64 KiB | **BASELINE** |
| Code Slots (CS0–CS7) | 8 × 2 KiB = 16 KiB/core | **FIXED** |
| Execution Buffer (EB) | 2 × 2 KiB = 4 KiB/core | **FIXED** |
| Active Execution Page | One active 2 KiB EB bank | **FIXED role** |
| Operating-System Workspace (OW) | 8 KiB | **FIXED** |
| Task Workspace (TW) | 8 KiB | **FIXED** |
| Context Pool (CP0–CP3) | 4 × 8 KiB; 16 × 2 KiB context slots/core | **FIXED** |
| Exception Workspace (XW) | 8 KiB; 8 × 1 KiB slices | **FIXED** |

Code Slots are equal pool resources, not permanently assigned to tasks. CST fills only the inactive EB bank; switching occurs only when the destination bank is ready and validated. Code residency and task-context residency are independent.

### 4.2 Current frontend simulator operating point

| Stage / resource | Current model setting |
|---|---:|
| App RAM instruction path | 64 B/cycle/core; 512 B/cycle for 8 cores |
| App RAM→C0 refill stage | 16 B/cycle |
| C0→CS | 20 B/cycle |
| CS→EB | 20 B/cycle |
| EB consume | 16 B/cycle |
| Frontend queue depth | 2 |

These are simulator operating points, not fixed silicon timing or final RTL parameters. New documentation must use canonical names.

---

## 5. Memory architecture

### 5.1 Separate memory paths

**FIXED**
- Each CPU core has its own independent 64 B/cycle App RAM instruction-fetch connection.
- Eight cores can fetch concurrently: 8 × 64 B/cycle = 512 B/cycle aggregate App RAM connection capacity.
- System Fabric coordinates the eight core-facing App RAM paths; do not model them as one shared 64 B/cycle bus or one global per-core queue.
- App RAM bank scheduling and outstanding-request capacity are modeled per core connection; same-core requests may contend locally.
- **Model boundary:** the simulator's eight-bank/per-core scheduling is an abstraction for local contention tests, not a frozen physical App RAM bank count, bank layout, or port implementation. Physical App RAM organization and the detailed System Fabric arbitration/fairness policy remain **OPEN**.
- App RAM and Data RAM are separate memory systems with independent controllers and paths; they may progress concurrently.
- Each CPU core has its own independent 64 B/cycle Data RAM connection. Eight cores therefore provide 8 × 64 B/cycle = 512 B/cycle aggregate Data RAM connection capacity.
- Data RAM core-facing paths must not be modeled as one shared 64 B/cycle bus or one global per-core queue. System Fabric coordinates the independent paths.
- App RAM is the instruction source. Data RAM stores mutable data, task state, and protected OS/context backing.
- Data RAM is not an instruction-fetch source.
- App RAM and Data RAM must not be collapsed into one global controller or queue.
- App RAM and Data RAM are attached to the shared System Fabric memory architecture; memory is a fabric resource, not a private memory island owned by one CPU. The Fabric may serve multiple CPU/system clients, with arbitration and QoS across requesters.
- The minimum bank-group organization for both App RAM and Data RAM is **8 banks × 64 bit per bank = 512 bit (64 B) aggregate group width**. This is eight 64-bit banks, not 64 banks. A 512-bit aligned stripe spans all eight banks.
- The eight-core CPU block retains eight independent 64 B/cycle core-facing connections per memory system (512 B/cycle aggregate connection capacity). The physical number of bank groups and how the Fabric provisions enough aggregate service across multiple CPU/system clients remain OPEN; do not infer one group per core or a total of only eight banks.
- Bank mapping/hash, physical port implementation, group replication/placement, and Fabric arbitration/fairness/QoS remain OPEN for measurement and design.

### 5.2 Data RAM bandwidth and bank group

| Parameter | Current architecture baseline | State |
|---|---:|---|
| Per-core Data RAM connection | 64 B/cycle/core | **FIXED** |
| Eight-core aggregate connection capacity | 512 B/cycle | **FIXED** |
| Banks per bank group (App RAM and Data RAM) | 8 | **BASELINE** |
| Local bank slice | 64 bit (8 B) | **BASELINE** |
| Aggregate group width | 512 bit (64 B) = 64 B/cycle per group | **BASELINE** |
| Interleave granule | 8 B | **BASELINE** |
| 512-bit aligned transfer | One 64-byte stripe across 8 banks | **BASELINE** |

Eight banks × 64 bit is the minimum bank-group baseline for both App RAM and Data RAM. It is not a claim that the whole fabric-connected memory system contains only eight banks. The motherboard concept diagram (`Anakart_temsili_tasarim.jpg`) shows Data MOSRAM resources distributed around the System Fabric, consistent with fabric-attached shared memory rather than a CPU-private bank island. The total number and placement of bank groups across the fabric remain OPEN; do not assume 8 groups per core. Folded bank selection is only a simulator candidate; final physical address mapping remains open to validation.

### 5.3 Already specified memory behavior

These are existing specifications, not new design tasks:
- LOAD/STORE and indexed/update forms.
- Effective-address calculation, bounds, natural alignment, ownership and permission validation.
- All-checks-before-commit behavior for protected memory operations.
- ATOM access rights and atomic-operation validation.
- Multi-bank wide-access tracking and all-or-none request admission.
- Per-bank queues, local arbitration, read/write turnaround, and wide-access completion.
- Independent App RAM and Data RAM controller progress.
- Private task data, explicit shared ranges, protected OS/context memory, and PL0/PL1/PL2 access policy.

Implementation-specific tests remain required; these behaviors must not be redesigned from scratch.

### 5.4 Cache hierarchy

The following capacities are **FIXED by the latest explicit architecture decision**:

| Cache level | Capacity | Sharing scope | State |
|---|---:|---|---|
| L1 | 1 MiB | Private to each core | **FIXED** |
| L2 | 2 MiB | Shared by each pair of cores | **FIXED** |
| L3 | 8 MiB | Shared by each group of four cores | **FIXED** |
| L4 | 64 MiB or more | Shared by each group of eight cores; not shared with the next group | **FIXED** |

The simulator contains and tests this grouping: L1 private, L2 per 2-core group, L3 per 4-core group, and L4 per 8-core group. These sharing scopes and capacities are both fixed decisions; do not reopen them during routine work.

**FIXED working-set placement rule — select the home level by the number of collaborating cores:**

| Collaborating cores | Working-set home | Role |
|---|---|---|
| 1 | L1 | Private execution working set |
| 2 | L2 | Pair-shared working set |
| 3–4 | L3 | Four-core shared working set |
| 5–8 | L4 | Eight-core shared working set |
| More than 8 | One L4 home per eight-core group | Cross-group sharing is not implied; it requires explicit inter-group transfer/visibility rules |

The selected level is the natural preparation/residency point for that collaboration scope. All participating cores read and share data from that common cache object. Lower levels may be populated naturally by demand accesses and the eventual fill policy; the simulator must not fake a group-shared working set by copying it into every private L1. Untimed prefill is a measurement setup operation, not a claim that real hardware loads data at zero cost.

**Within one eight-core block, both four-core L3 groups access the same L4.** An L4-resident line can therefore be served to cores on either side of the L3-group boundary; separate L3/L2 groups do not imply separate L4 homes. The isolation boundary is between eight-core L4 blocks, not between their internal L3 groups. The canonical instance count per eight-core block is **8×L1 / 4×L2 / 2×L3 / 1×L4**.

**FIXED cache instance topology per eight-core block:**

```text
Core 0–7: 8 × private L1 (1 MiB each)
Core pairs: 4 × shared L2 (2 MiB each)
Four-core groups: 2 × shared L3 (8 MiB each)
Eight-core block: 1 × shared L4 (64 MiB+)
```

Every core can address its own L1, its pair's L2, its four-core group's L3, and the common eight-core L4 according to access/visibility rules. Both L3 groups inside one eight-core block can access the same L4; an L3-group boundary is **not** an L4 isolation boundary. Only the boundary between distinct eight-core L4 blocks separates L4 homes; cross-block visibility/transfer requires an explicit mechanism.

This topology describes cache **instances and sharing**, not request ports or bandwidth. The numbers 8/4/2/1 must not be interpreted as port counts. Port count, per-level service bandwidth, arbitration, and contention remain configurable/open; the simulator's earlier one-request-per-cycle shared-port setting is only a provisional experiment, not an approved architectural decision.

**FIXED multi-block data distribution principle:** For workloads spanning more than eight cores, data may be staged directly from Data RAM/main memory into the L4 homes of the participating eight-core blocks. Shared-data distribution is sourced from memory directly to the selected L4 homes; it does not require one L4 block to forward data through another L4 block. Each block then serves its own cores through its local L3/L2/L1 hierarchy.

Supported architectural distribution choices:
- **Partitioned:** disjoint data chunks are assigned to individual L4 blocks; each block receives its chunk directly from memory.
- **Replicated/shared read-mostly:** the same read-only or explicitly shared data range is delivered directly from memory to each selected L4 home.
- **Selective multicast:** only the chosen subset of L4 homes receives a shared range directly from memory.

This establishes the data-source and route principle, not yet the transfer protocol. Address-range ownership, destination selection, chunk size/alignment, scheduling, bandwidth reservation, write/update visibility, and completion/fault handling remain OPEN. Writable replicas must not be assumed coherent; an explicit ownership/update protocol is required before concurrent writes are permitted.

**OPEN:** cache-line size, associativity, replacement, hit/miss latency, bandwidth/ports, write policy, inclusion/exclusion, coherence/visibility protocol, cross-group transfer, and interaction with the L1–L4 logical memory-domain/zone model. A logical access domain is not automatically the same thing as a physical cache instance.

---

## 6. Protection, task state, and exceptions

**FIXED / specified baseline**
- Privilege levels: PL0 user task, PL1 supervisor/OS, PL2 machine/firmware.
- App RAM contains executable command streams; Data RAM contains mutable data and protected task/OS context backing.
- Task-private memory is isolated by default; sharing requires explicit grants.
- User code follows write/execute separation by default.
- Context payload uses existing RA/FA/DA/MA banks; no additional architectural register bank is introduced for context save.
- ECS holds hardware exception/return metadata.
- XW provides depth-selected exception-entry workspace.
- Persistent privileged exception frames and full task contexts reside in protected Data RAM.
- CP0–CP3 provide the current per-core resident context pool: 16 × 2 KiB slots/core, with spill to protected Data RAM.
- Workspaces are not automatically coherent or migrated between cores; live task workspace is preserved/restored through the defined context/migration path.

Detailed numeric CSR encodings, optional counters, exact permission-cache/translation implementation, and some IRQ controller encodings remain open where the detailed specifications say so.

---

## 7. Instruction encoding and data representation

| Rule | Decision | State |
|---|---|---|
| Base instruction word | 64 bit | **BASELINE** |
| Memory byte order | Little-endian | **FIXED** |
| Register selector | 5 bit | **FIXED** |
| Address width | 64 bit | **FIXED baseline** |
| Maximum CPU data operation | 512 bit | **BASELINE** |
| Supported memory access widths | 8/16/32/64/128/256/512 bit | **BASELINE** |

The instruction encoding document remains a draft wherever it explicitly marks format details, reserved encodings, or opcode assignments as unfrozen. Do not describe the entire ISA encoding as frozen.

---

## 8. System Fabric relationship

**FIXED architectural direction**
- System Fabric is the system-level communication and transfer infrastructure; CPU is not the mandatory transit point for all node-to-node transfers.
- CPU, GPU, FAPU, NPU, MOSRAM, M-SSD, and I/O are independent nodes connected through the Fabric.
- Node clocks, Fabric clock, and memory clocks are independent domains.
- Dynamic routing, arbitration, traffic scheduling, flow control, QoS, and direct node-to-node transfer are part of the Fabric design direction.

**FIXED clock relationship:** System Fabric runs at **2× the CPU core clock** for the current NEXSUS CPU baseline. One CPU cycle therefore contains two Fabric scheduling ticks. The Fabric uses these faster ticks to time-interleave requests, independently schedule destination queues, and keep eligible output paths continuously occupied. Different destinations may receive transfers in the same CPU-cycle window, creating an effectively simultaneous view without requiring every physical write to occur at the exact same instant.\n\n**OPEN:** final physical lane count, lane allocation granularity, routing topology, protocol/packet details, destination queue depths, arbitration/QoS policy, and silicon-level latency/throughput. The 2× clock ratio improves scheduling opportunity; it does not by itself double a link's byte bandwidth. Link width, port count, destination service rate, and contention still bound throughput.

---

## 9. Simulator and comparison rules

1. Use the same logical workload and operation counts for every compared architecture/topology.
2. Keep architecture configuration separate from simulator tuning parameters.
3. Report throughput, dependency latency, memory stalls, and total cycles separately.
4. A model result validates only the modeled behavior and assumptions.
5. Never describe simulator results as measured CPU performance.
6. Do not change INT=8 / FP64=6 / FMA=4 / VEC=2 / ME512=1 merely to improve one benchmark result.

The 8-core comparison configuration is an established test configuration. It does not, by itself, freeze every future product to exactly eight cores.

---

## 10. Remaining work — only unfinished work

Items already specified in architecture documents are not to be redesigned; they are to be verified or completed.

### A. Immediate
- [ ] Diagnose and fix regression failure in workflow [43787870423](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43787870423).
- [ ] Rerun FMA result-latency sweep (3/4/5/6 cycles) with FP64=6 and FMA=4 held fixed.
- [ ] Record dependency-chain latency separately from independent FMA issue throughput.
- [ ] Re-run App RAM target/wrong-path contention and eight-core fairness sweeps after fixing the test syntax and stale workflow expectation; keep physical bank topology marked OPEN.

### B. Register and execution connectivity
- [ ] Confirm physical register read/write port counts.
- [ ] Verify simultaneous operand reads for INT/FP64/FMA/VEC/ME512.
- [ ] Verify writeback arbitration, forwarding, and structural hazards.
- [ ] Verify MA pair access and ME512 result writeback.

### C. Data RAM implementation verification
- [ ] Complete cycle-level tests for per-bank queues and arbitration.
- [ ] Test simultaneous requests to distinct banks and conflicts to the same bank.
- [ ] Test 128/256/512-bit split accesses, stripe crossings, and all-or-none admission.
- [ ] Complete Data RAM MSHR/queue-capacity sensitivity tests.
- [ ] Verify independent App RAM and Data RAM progress under concurrent load.

### D. Cache hierarchy specification and model
- [x] Define physical scope/sharing and collaboration-scope working-set home: L1=1 MiB/core, L2=2 MiB/pair, L3=8 MiB/four-core group, L4=64 MiB+/eight-core group.
- [ ] Define cache line, associativity, replacement, hit/miss timing, bandwidth, and ports.
- [ ] Define write policy and coherence/visibility rules.
- [ ] Integrate cache behavior with existing memory-domain ownership and access validation.

### E. Full-system validation
- [ ] Integrate execution, register ports, Data RAM, cache, and Fabric in the cycle-level model.
- [ ] Run isolated and mixed INT/FP64/FMA/VEC/ME512 workloads.
- [ ] Run memory-bound, cache-bound, and multi-core contention workloads.
- [ ] Publish a consolidated result report with model limitations.

---

## 11. Conflict resolution and change log

- The 2026-11-17 explicit clarification establishes independent Data RAM connections of 64 B/cycle per core (512 B/cycle aggregate for eight cores); the older 64 B/cycle aggregate wording is superseded. The 2026-11-13 revision also confirms 32-entry RA/FA/DA/MA banks.
- The 2026-11-16 App RAM connection correction establishes 64 B/cycle per core and 512 B/cycle aggregate for the eight-core block; System Fabric coordinates independent core-facing paths. Older 64-entry register tables are superseded.
- The 2026-11-16 memory-path naming decision establishes C0, CS, CST, EB, OW, TW, CP, and XW as current terms. PX, P0–P7, Ping-Pong, SPM0, and L0I are legacy terms.
- The latest explicit execution-resource decision fixes INT=8, FP64=6, FMA=4, VEC=2, ME512=1.
- Cache sharing is already defined and simulator-tested: private L1, L2 shared per 2 cores, L3 per 4 cores, and L4 per 8-core group. The latest explicit capacity decision fixes these to L1=1 MiB/core, L2=2 MiB/2-core group, L3=8 MiB/4-core group, and L4=64 MiB+/8-core group.

- 2026-11-24: replaced the former shared INT=8 execution pool with three independent fixed pools: Arithmetic ALU=8, Logic=8, Compare=8. Added class-specific issue queues; queue depths and physical register ports remain open pending aggregate demand analysis. Affected files: ISA-001 and this decision register.

When a decision changes, append the date, old value, new value, reason, approving instruction, and affected specification/test files. Never silently overwrite history.
