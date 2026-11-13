# NEXSUS CPU — SPM and P0 Ablation Experiment Plan

**Document ID:** NEXSUS-CPU-SPM-P0-ABLATION-PLAN-001  
**Status:** Experimental specification; first-stage P0 and SPM2 models implemented; remaining SPM roles pending  
**Purpose:** Quantify the independent and combined contribution of NEXSUS SPM and P0 against controlled conventional CPU reference profiles.

## 1. Why a separate experiment is required

The NEXSUS design includes two architectural mechanisms that are not represented by a simple increase in execution width:

- **SPM:** directly addressed, software-/OS-managed local working memory with explicitly assigned roles.
- **P0:** a dedicated command store/refill path holding fixed-width 64-bit command records, separate from application data memory.

A comparison that models only ALUs, FPUs, caches and DRAM would omit these mechanisms and could materially misrepresent the design. Conversely, assigning ideal zero-latency behavior to SPM/P0 would unfairly favor NEXSUS. Their capacity, access latency, port/bank conflicts, refill cost, occupancy and management overhead must be explicit model parameters.

This plan uses controlled ablation: keep the same NEXSUS core profile and workload, then disable one feature at a time while preserving a defined fallback path.

## 2. Four NEXSUS ablation profiles

| Profile | SPM | P0 | Purpose |
|---|---|---|---|
| N-FULL | Enabled | Enabled | Complete proposed NEXSUS path |
| N-NO-SPM | Disabled | Enabled | Isolate SPM contribution |
| N-NO-P0 | Enabled | Disabled | Isolate P0 contribution |
| N-BASE | Disabled | Disabled | Combined-feature baseline |

The four profiles must keep core count, clock, execution units, pipeline widths, ROB, memory workload, cache assumptions and DRAM controller configuration identical. Only the selected feature and its explicitly documented fallback behavior may change. The simulator API accepts independent `spm` and `p0` booleans. A four-way runner now executes N-FULL, N-NO-SPM, N-NO-P0 and N-BASE on identical operation graphs, checks operation-count preservation, and reports isolated gains, combined gain and interaction per kernel.

The interaction effect must also be reported. SPM and P0 gains are not assumed to be additive.

## 3. Fair fallback behavior

### 3.1 SPM enabled

Use the architectural SPM roles and capacities already defined by the CPU design:

| SPM | Capacity | Simulated role |
|---|---:|---|
| SPM0 | 2 KiB | CPU-exclusive execution workspace |
| SPM1 | 8 KiB | OS workspace and defined syscall/I/O exchange |
| SPM2 | 8 KiB | Current task's user/program workspace |
| SPM3–SPM6 | 4 × 8 KiB | OS-managed resident task-context slots |
| SPM7 | 8 KiB | Exception-entry workspace, eight 1 KiB depth slices |

Do not treat every SPM bank as a generic cache. Model each role according to its ownership and lifetime. SPM0 and SPM7 are hardware-only; SPM1 is OS-owned; SPM2 is task-owned; SPM3–SPM6 hold resident context slots.

Access latency, port count, bank conflicts and arbitration are currently unspecified physical parameters. They must be configurable and swept across conservative, nominal and optimistic scenarios rather than silently assumed to be one cycle.

### 3.2 SPM disabled

Do not delete the work performed by SPM. Redirect it through a conventional, explicit backing path:

- SPM2 task working-set accesses use the normal Data RAM/cache path.
- SPM3–SPM6 context payloads use protected Data RAM context backing.
- SPM1 OS workspace and exchange data use the defined OS memory region in Data RAM.
- SPM7 exception workspace uses the protected exception-entry memory path.
- SPM0 CPU-internal workspace operations use the model's ordinary internal temporary/register scheduling path; do not charge them as user memory traffic unless the modeled implementation actually spills them.

The fallback must preserve data values, operation counts and architectural behavior. It may change latency, bandwidth contention and memory traffic, which are precisely what the experiment measures.

## 4. P0 enabled and disabled behavior

### 4.1 P0 enabled

Model P0 as a dedicated command store, not as an ordinary data cache:

- 64-bit command records.
- Configurable capacity, with the current standard target of 16 KiB total as P0+P1 (two 8-KiB buffers, 1,024 records each); 4/8/32 KiB totals are sensitivity alternatives.
- Up to 512-bit peak refill width (eight 64-bit records per refill beat), not a promise of eight decoded or issued commands per cycle.
- Explicit refill request, refill latency, refill bandwidth, refill occupancy and branch/refill behavior.
- Separate App RAM instruction source and Data RAM payload path.

The simulator must distinguish command availability in P0 from downstream decode, dispatch, issue and execution capacity.

### 4.2 P0 disabled

Use a conventional instruction-fetch path with an explicitly parameterized instruction cache/front-end buffer. Do not model P0-off as an unbuffered App RAM fetch on every instruction; that would create an intentionally weak straw-man baseline.

The conventional path must expose instruction-cache capacity, hit latency, miss/refill latency, refill bandwidth, fetch width and branch redirect penalty. Use the same App RAM source and normalized memory-controller assumptions where applicable.

P0's measured benefit is the difference between the dedicated P0 organization and this conventional instruction-fetch baseline, not the difference between P0 and an unrealistic no-cache design.

## 5. Workload extensions required

The existing nine kernels remain useful for broad CPU behavior, but they do not sufficiently isolate SPM/P0. Add targeted kernels:

| Kernel | Behavior | Primary measurement |
|---|---|---|
| spm_hot_workset | Repeatedly accesses a bounded task-local working set | Local access latency, avoided cache/DRAM traffic |
| spm_capacity_sweep | Working set grows across SPM2 capacity and backing-cache capacity | Capacity cliff and spill/fallback cost |
| spm_task_switch | Switches among tasks whose register contexts fit or do not fit resident SPM3–SPM6 slots | Save/restore cycles, backing-memory traffic, residency hit rate |
| spm_exception_entry | Repeated nested exception/IRQ entry and exit using SPM7 slices | Entry latency, protected Data RAM traffic, depth behavior |
| spm_os_exchange | Repeated OS/user syscall exchange through SPM1-defined area | Copy volume, access latency, OS path contention |
| p0_sequential | Sequential command stream with predictable refill | Sustained command supply and refill overhead |
| p0_branch | Branch-heavy stream with redirect/refill pressure | Redirect penalty, P0 hit/refill behavior |
| p0_working_set | Command working set grows beyond P0 capacity | Refill rate and capacity sensitivity |
| p0_starvation | Execution units are ready while command supply is deliberately stressed | Front-end-limited cycles and unit starvation |

All variants must execute the same logical work and produce a checked result/signature. No feature may gain credit by skipping work.

## 6. Metrics

Report per kernel and per profile:

- Total cycles and normalized completion time.
- Operations completed and aggregate throughput.
- Front-end-limited cycles and command-fetch stall cycles.
- P0 hit/refill counts, refill bytes and refill wait cycles.
- SPM accesses and bytes by SPM role.
- SPM bank/port conflict cycles and capacity overflow/spill events.
- Data RAM/cache/DRAM bytes attributable to SPM fallback.
- Task-context resident hits, evictions, save/restore cycles and bytes.
- Exception-entry/exit cycles and protected-frame traffic.
- Energy estimate only when validated per-access/per-transfer energy parameters exist; otherwise report traffic and activity counts, not fabricated joules.

For a lower-is-better metric such as cycles, calculate:

- SPM contribution with P0 held enabled: N-NO-SPM versus N-FULL.
- P0 contribution with SPM held enabled: N-NO-P0 versus N-FULL.
- Combined contribution: N-BASE versus N-FULL.
- Interaction: compare the combined gain with the sum of isolated gains; report the difference rather than assuming additivity.

Use both absolute deltas and percentage deltas. Include per-kernel results; a single geometric/composite score must not hide regressions.

## 7. Reference CPU comparison

AMD Zen 5, Intel Lion Cove P-core and Intel Skymont E-core remain separate reference profiles, each using exactly eight active cores in the controlled phase.

These CPUs are not assigned fictional SPM/P0 hardware. Their existing cache and front-end paths are modeled using documented or explicitly labeled assumed parameters. The NEXSUS ablation set answers “what did SPM/P0 contribute inside NEXSUS?” The cross-architecture comparison answers “how does the complete NEXSUS design compare with these reference profiles?”

Keep those two questions distinct.

## 8. Parameter discipline and uncertainty

The following are not yet physically validated and must remain configurable:

- SPM read/write latency, bank count, port count and arbitration.
- SPM0 internal access behavior and issue constraints.
- SPM2 access concurrency with normal Data RAM.
- SPM3–SPM6 context transfer bandwidth and simultaneous save/restore behavior.
- SPM7 exception-entry access latency.
- P0 refill latency, refill width utilization, refill arbitration and redirect penalty.
- Conventional instruction-cache parameters used by P0-off mode.

Publish sensitivity ranges. Do not present a single best-case setting as a proven hardware result. Any eventual timing/energy claim requires circuit/layout-level validation and a simulator model calibrated to it.

## 9. Implementation sequence

1. Implement the lockstep multicore shared bank/DRAM controller first: global eight-bank state, work-conserving chip-wide bus, rotating core arbitration and bounded fairness.
2. Add regression tests for cross-core bank conflicts, independent-bank parallelism, bus saturation and dynamic bandwidth borrowing.
3. Add SPM/P0 feature configuration and per-role/per-refill counters without changing architectural operation counts. **First stage now implemented:** P0 toggle, conventional I-cache fallback, SPM2 toggle and overflow fallback.
4. Extend the P0 model with redirect/refill overlap, command-path arbitration and more realistic loop/working-set traces. Initial P0 sequential/branch/working-set/starvation kernels and a conventional I-cache fallback are implemented.
5. Extend SPM2 model with bank/port configuration, true capacity spills and task migration semantics. Initial hot-working-set and capacity kernels are implemented.
6. Add SPM3–SPM6 task-context residency, SPM1 OS exchange and SPM7 exception-entry models with their targeted kernels.
7. Add four-profile ablation regression tests proving that feature toggles preserve operation counts. **Implemented:** 23 regression tests pass; the four-way run preserves 44,654 operations across all variants.
8. Publish parameter sweeps and uncertainty ranges before drawing architecture conclusions.

## 10. Interpretation rules

- SPM is expected to help only when software/OS places useful data or context in it and the working set fits the available capacity. Poor placement or overflow can erase the benefit.
- P0 is expected to help when command-fetch supply, refill predictability or instruction/data path separation is limiting. It cannot make a dependency-bound algorithm execute faster by itself.
- P0's 512-bit peak refill width must never be reported as eight instructions retired per cycle.
- SPM capacity is not automatically additional cache capacity; its benefit comes from explicit placement, predictable access and reduced contention/traffic.
- The existing general-purpose comparison suite is not sufficient by itself to prove either feature. Targeted workloads and ablation are mandatory.

## 11. Current status

This document defines the experiment and fair fallback rules. The simulator now has a first-stage NEXSUS-only P0/conventional-fetch model, SPM2 direct-access/fallback model, and four-way ablation report generator. Initial scale-1 results are recorded in `NEXSUS-CPU-SPM-P0-ABLATION-RESULTS-001.md`. P0 is represented by an 16 KiB P0/P1 ping-pong command store (two 8-KiB buffers), 8-KiB block refill and 128-cycle provisional transfer at 512-bit/cycle; P0-off uses a 32 KiB conventional instruction cache and a 32-cycle provisional refill. Per-core command streams are rebased after workload partitioning; loop kernels retain their local loop address pattern. Both use one outstanding refill per core. SPM2 uses an 8 KiB addressable task workspace, a provisional 2-cycle access and one modeled port per core; out-of-range accesses fall back to the ordinary cache/Data RAM path. These are explicit sensitivity parameters, not validated physical timings. SPM0, SPM1, SPM3–SPM7 context/exception/OS behavior, calibrated command-path arbitration and richer branch redirect behavior remain pending. The initial model run shows SPM2 and P0 cycle reductions in their targeted kernels; these are simulator results only, not physical performance claims. Remaining SPM roles and parameter calibration are required before architecture-level performance conclusions.
