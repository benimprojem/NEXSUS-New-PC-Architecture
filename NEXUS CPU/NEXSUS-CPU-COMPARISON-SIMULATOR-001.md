# NEXSUS CPU — Cross-Architecture Comparison Simulator

**Document ID:** NEXSUS-CPU-COMPARISON-SIMULATOR-001  
**Status:** Simulator v0.3.2-dev; current AMD/Intel/ARM profiles, PX-fed 4 KiB dual-bank SPM0 model, branch-prediction sensitivity model; regression validation in progress  
**Purpose:** Compare one deterministic mixed workload across current AMD Zen 5, Intel Xeon Redwood Cove+, Apple ARM M6, and the selected NEXSUS architecture.

## 1. Comparison targets

| Target | Processor | Core model | Physical organization |
|---|---|---|---|
| AMD | Ryzen 9 9950X | Zen 5 | Controlled comparison uses 8 Zen 5 cores; SMT disabled in this phase |
| Intel P | Core Ultra 9 285K | Lion Cove | 8 P-cores |
| Intel E | Core Ultra 9 285K | Skymont | Separate 8 E-core reference profile; not mixed with P-core profile |
| NEXSUS | Selected 128-window profile | Current proposed CPU blocks | 8 cores |

AMD and Intel are represented by separate core profiles. The Intel P and E cores must never be averaged into one generic core. Controlled phase uses exactly 8 active cores for every target, one hardware thread per core, with SMT disabled. AMD and Intel SKU maximum core counts are intentionally not used in this experiment; this isolates per-core architecture and avoids winning by core-count advantage. A later full-SKU phase can compare 16C/32T AMD and 8P+16E Intel.

## 2. Shared workload algorithm

The simulator builds the same deterministic operation graph for every target. The algorithm is a composite workload rather than one artificial tight loop.

| Kernel | Algorithmic behavior | Main resources stressed |
|---|---|---|
| scalar_control | Integer recurrence, independent integer transforms, conditional branches | Integer ALUs, register dependencies, front-end and branch recovery |
| pointer_graph | Dependent pointer-chasing loads with decisions | AGU, load queue, cache hierarchy, DRAM latency, branch predictor |
| numeric_tile | Matrix-like tiles, independent input loads, FP accumulation and vector operation | FPU/vector datapaths, register files, load/store |
| streaming | Sequential read-transform-write over a large data range | Load/store throughput, cache lines, memory bandwidth and bank conflicts |
| parallel_tasks | Independent task inputs, scalar/FP work, output and context operations | Core scheduling, synchronization and context save/restore (later parallel model) |
| integer_throughput | Independent integer operations | ALU issue and execution capacity |
| fp_throughput | Independent floating-point operations | FPU issue and execution capacity |
| vector_throughput | Independent vector operations | Generic vector-unit throughput; not yet a full ME512 instruction model |
| branch_stress | Independent branch operations | Branch issue and modeled recovery penalty |

The operation graph is deterministic. Each operation carries its dependencies, memory address, width and operation class. CPU profiles map the same logical operations to their own execution resources and latency assumptions.

## 3. Simulator pipeline

The target model is an event/cycle-driven CPU model with these components:

1. Instruction/operation front-end and bounded dispatch.
2. In-flight operation window (ROB-like for x86; provisional NEXSUS parameter).
3. Dependency-aware issue and execution-resource availability.
4. Out-of-order completion and in-order retirement.
5. Branch recovery stalls.
6. L1/L2/L3/L4/DRAM access classification and per-bank serialization.
7. Multicore task scheduling and shared-cache/memory contention (planned after v0.1).

The v0.2.4-dev simulator partitions independent dependency components across cores and advances all core pipelines on a shared global cycle. DRAM misses are collected across cores and arbitrated by one shared bank/bus controller; bandwidth is work-conserving rather than statically divided per core. NEXSUS now uses its proposed shared cache-group topology: private L1, L2 per two cores, L3 per four cores and L4 per eight-core group. The text report also provides a per-kernel breakdown (cycles, operations, IPC, active cores and DRAM access count) alongside the composite total. The suite now adds isolated integer, FP, generic vector and branch-throughput kernels to help identify which execution resource limits each profile. It includes dependency tracking, issue-resource limits, in-order retirement, branch stalls, deterministic LRU cache approximations, shared NEXSUS cache groups and a global DRAM bank/bus controller. Inter-core coherence traffic and SMT are still pending; current multicore results are therefore an intermediate model, not final throughput predictions. The generic vector kernel does not yet represent ME512's 512-bit paired-register behavior, matrix dimensions or data movement.

### 3.1 Lockstep multicore shared memory controller (v0.2.4-dev)

The simulator now advances all active core shards on one global cycle. Each core retains a private pipeline, ROB, execution-unit slots and private L1. NEXSUS L2/L3/L4 cache objects are shared across their configured 2/4/8-core groups. Per cycle, the simulator:
1. Completes ready operations and retires in order on every core.
2. Dispatches each core's next operations within its frontend/ROB limits.
3. Selects ready issue candidates independently on each core.
4. Collects all selected DRAM misses from every core into one same-cycle request batch.
5. Calls one shared controller to arbitrate bank beats and aggregate bus service, then assigns completion times.

The shared controller models one 64-bit beat per bank per cycle and a chip-wide aggregate DRAM bus ceiling. Same-bank requests serialize; different banks may overlap. Unaligned accesses reserve every touched 64-bit bank beat, including an additional beat when a wide access crosses a beat boundary. Bus service is work-conserving: there is no static per-core bandwidth quota, so an active core may use otherwise-idle bandwidth. Core arbitration rotates between batches.

Only actual DRAM misses consume the physical bank/bus model. L4 is still treated as a cache level in the current simulator, not as a physical DRAM bank. This distinction avoids conflating logical cache hierarchy with physical memory topology.

Regression coverage includes direct controller tests and lockstep integration tests for same-bank contention, independent-bank overlap, shared aggregate bandwidth, same-workload retirement across all four architectures, reference cache-sharing topology and conventional instruction-fetch refill. The latest corrected run passed **27 regression tests**, the 4-way SPM/P0 ablation and the 4/8/16/32 KiB P0 capacity sweep. See [Cross-Architecture Comparison Results](NEXSUS-CPU-CROSS-ARCHITECTURE-RESULTS-001.md) for the per-kernel result table and interpretation.

**Cache topology assumptions for the controlled 8-core comparison:** NEXSUS uses private L1, L2 per two cores, L3 per four cores and L4 per eight cores. AMD Zen 5 uses private L1/L2 and a shared package L3. Intel Lion Cove P uses private L1/L2 and a shared package L3. Intel Skymont E uses private L1, a modeled 4 MiB L2 shared per four-core cluster, and a shared package L3. These sharing relationships are represented in the model; they are not cycle-accurate replicas of the vendors' cache fabrics. Cache fills are committed when the modeled access completes, so simultaneous same-line misses are not silently merged; no MSHR/coalescing model is present. The group caches use a simplified LRU and demand-fill path. Inclusion, line ownership, coherence/visibility, cross-group transfer cost, physical App RAM vs Data RAM controllers, refresh, read/write turnaround, queue depth/backpressure, request aging and Fabric QoS are not yet implemented. The controller is a timing abstraction, not RTL or a calibrated DRAM model. The reference 32 B/cycle bus ceiling and 120-cycle DRAM latency remain normalized experimental assumptions.


## 3.2 Symmetric command-fetch modeling

The first cross-architecture run exposed an unfair assumption: NEXSUS had an explicit P0 refill gate, while reference CPUs had been allowed to dispatch without any modeled instruction-fetch miss delay. This has been corrected. Every AMD/Intel reference core now uses a conventional modeled instruction-cache path: 32 KiB capacity, 64-byte line and provisional 32-cycle refill, with one outstanding refill per core. NEXSUS uses two 8-KiB P0/P1 ping-pong buffers (16 KiB total); each 8-KiB command block is loaded through the 512-bit refill path (128-cycle provisional transfer) and can be compared against the same 32 KiB conventional fallback when P0 is disabled.

This is a symmetric baseline model, not an exact vendor L1I implementation: real AMD/Intel instruction-cache capacities, banking, predecode/uop-cache behavior, refill bandwidth, outstanding miss depth, branch-target delivery and frontend queues vary by architecture and remain to be calibrated. The important correction is that no reference target receives a zero-latency instruction source while NEXSUS pays explicit refill stalls.

## 4. Known public reference points and model assumptions

### AMD Ryzen 9 9950X / Zen 5

AMD's product specification lists 16 cores / 32 threads, up to 5.7 GHz boost, 48 KB L1 data cache per core, 1 MB L2 per core and 64 MB total L3. AMD's Hot Chips Zen 5 overview describes dual 4-wide decode pipes, 8-wide dispatch, a 448-entry retire queue, four load pipes and two store pipes. The simulator uses these as profile anchors; single-thread decode behavior and throughput must be interpreted carefully.

### Intel Core Ultra 9 285K / Arrow Lake

Intel's product specification lists 8 P-cores + 16 E-cores, 24 total cores/threads, up to 5.7 GHz max turbo, 36 MB L3 and 40 MB total L2. The P-core profile represents Lion Cove; the E-core profile represents Skymont. Public architectural analyses provide additional estimates for the front-end, execution window and cache latencies. Those estimates are marked as model inputs, not guaranteed behavior for every workload or firmware configuration.

### Selected NEXSUS 128-window architecture

Already specified architectural anchors:
- 2 integer ALUs, 2 FPUs and 1 ME512 per core.
- 128 KiB private L1 per core.
- 1 MiB L2 shared by two cores.
- 8 MiB L3 shared by four cores.
- 64 MiB L4 shared by eight or more cores. The v0.1 model includes this L4 capacity and a provisional 64-cycle latency assumption; this latency is not frozen.
- 8-bank × 64-bit bank-group candidate.
- Separate App RAM instruction path and Data RAM data path.
- P0 command cache; 64-bit command records and 512-bit peak refill interface.
- RA/FA/DA/MA register banks and SPM0–SPM7.

NEXSUS dispatch/retire width, scheduling model, branch predictor, ROB-equivalent capacity, cache/bank latency, clock and core count are not frozen. The simulator uses one selected NEXSUS profile: front-end 8, dispatch 8, issue 10, retire 8, and a 128-entry modeled window. The execution-resource profile is INT 4, FP 4, VEC 2, LOAD 8, STORE 4, BR 2, CTX 1 and ATOM 1. These are the chosen comparison configuration, but remain model parameters rather than a claim of validated silicon performance.

## 5. Controlled clock and core-count experiment

The first architecture-isolation experiment uses:
- Exactly 8 active cores for AMD, Intel P-core, Intel E-core reference and NEXSUS.
- Exactly 3.0 GHz common reference clock for CPU pipeline and modeled memory timing.
- Identical DRAM latency (120 reference cycles) and chip-wide aggregate modeled bandwidth (32 bytes/reference cycle) for every profile, including NEXSUS. The v0.2.4-dev shared controller enforces the aggregate ceiling without a fixed per-core quota.
- Identical workload graph, input sizes and branch-event pattern.
- One hardware thread per core; SMT is disabled in this phase.

This is a normalized synchronous reference-clock model. It does not claim that commercial desktop CPUs physically clock external DDR memory at the CPU core frequency. Real DRAM has its own clock and controller timing; those are intentionally normalized here so that the initial comparison isolates architecture. A later physical-calibration phase can restore real memory clock ratios and timings.

The Intel E-core profile is reported separately as an 8-core E-core reference, not mixed into an 8P+16E whole-chip result. NEXSUS is always configured with at least eight cores in this comparison.

## 6. Fairness and measurement rules

- All CPU profiles receive the same logical algorithm, input sizes, dependency graph and deterministic branch pattern.
- Compare single-thread performance separately from multicore throughput. Review each kernel independently; a composite score can hide opposing strengths and bottlenecks.
- Report cycles, elapsed time under a stated frequency assumption, IPC/operations per cycle, cache-level accesses, branch recoveries, resource utilization and memory stalls.
- Do not compare a peak boost clock as if it were sustained all-core frequency. Time conversion in v0.1 is only a configured-clock estimate.
- Do not convert the model's cycle counts into power or energy without a calibrated energy-per-operation and memory-energy model.
- Use measured machine benchmarks to calibrate real AMD/Intel profiles. A model that cannot reproduce reference measurements is not ready for NEXSUS design decisions.
- Keep known, estimated and unknown parameters separately labelled.


## 6.1 Selected NEXSUS profile

The comparison now exposes **one NEXSUS configuration only**: the 128-window balanced architecture. The earlier baseline, 8L4S, wide-balanced-192 and other exploratory variants have been removed from the selectable profile list so the comparison cannot silently switch between competing NEXSUS designs.

| Parameter | Selected NEXSUS |
|---|---:|
| Front-end | 8 |
| Dispatch | 8 |
| Issue | 10 |
| Retire | 8 |
| Modeled in-flight window | 128 |
| INT units | 4 |
| FP units | 4 |
| VEC units | 2 |
| LOAD units | 8 |
| STORE units | 4 |
| BR units | 2 |
| CTX / ATOM units | 1 / 1 |

The 8 LOAD + 4 STORE values are modeled concurrent issue slots, not guaranteed completed accesses per cycle. Dependencies, cache hits/misses, bank conflicts and shared-controller arbitration continue to constrain actual throughput. The selected profile retains the current provisional cache and memory parameters. The 128-window value is the selected simulator configuration; physical area, power, wiring, queue implementation and clock closure still require validation.

### Stall counters

The report now includes:
- dependency-blocked operation-cycle events;
- issue-width-blocked operation-cycle events, counted only after dependency readiness is established;
- execution-unit-unavailable operation-cycle events;
- front-end bandwidth-limited cycles;
- ROB-full cycles;
- branch-recovery cycles;
- cumulative modeled memory-latency exposure (`latency - 1` summed per issued LOAD/STORE); this is not measured stall time.

These are diagnostic counters, not mutually exclusive wall-clock durations. Some count per-operation events and others count cycles; they must not be added together as elapsed time. The v0.2.4-dev model replaces the static per-core split with lockstep global bank arbitration. The shared controller models same-cycle DRAM miss contention; NEXSUS shared cache groups now model capacity and hit paths, while coherence and physical controller details remain approximations. The memory-latency exposure counter is descriptive latency accounting, not a count of cycles during which the pipeline was actually stalled. Shared memory arbitration must be implemented before treating 8L4S throughput as a realistic whole-chip prediction.

## 7. P0 and SPM2 first-stage model\n\nThe simulator now accepts independent NEXSUS feature toggles (`spm`, `p0`) without changing the logical operation graph. P0-enabled mode defaults to a 16 KiB command store as two alternating 8 KiB buffers (P0 and P1). Each buffer holds 1,024 64-bit command words. While one buffer supplies execution, the other prefetches the next 8 KiB block; the buffers alternate continuously. The model assumes a 512-bit/cycle App-RAM refill path, hence 128 cycles per 8 KiB transfer, and one refill engine per core. Capacity and refill latency are configurable. Run `--p0-sweep` to compare 4/8/16/32 KiB while holding the logical workload and other parameters constant; use `--p0-capacity-kb` and `--p0-refill-cycles` for a selected configuration. Run `--fetch-sweep` to compare conventional I-cache refill assumptions (8/16/24/32 cycles) against P0/P1 8-KiB block-refill assumptions (64/96/128/160 cycles) on the same command-working-set trace. P0-disabled mode uses a 32 KiB conventional instruction cache (512 × 64-byte lines) and a provisional 32-cycle refill. The fetch gate limits dispatch until the command line is available; this does not equate refill width with decode/retire width. Command-path timings and capacities are explicit model assumptions, not measured silicon values.\n\nSPM2-enabled mode recognizes explicitly tagged task-local accesses and routes in-range accesses (within 8 KiB) to a modeled local workspace with provisional 2-cycle access latency and one port per core. Out-of-range accesses fall back to the normal cache/Data RAM path. SPM2-disabled mode sends all such accesses through the normal cache/Data RAM path. Per-core counters report SPM2 accesses, bytes, port conflicts, overflow events and fallback bytes; P0 counters report hits, refills, refill bytes and command-fetch wait cycles.\n\nThe initial targeted suite includes SPM2 hot-working-set/capacity kernels and P0 sequential/branch/working-set/starvation kernels. The command trace is a deterministic per-core stream after workload partitioning; loop kernels retain their working-set pattern so capacity effects are measurable. Detailed branch-target redirects, refill queue arbitration, SPM2 multi-bank organization and SPM0/1/3–7 behavior remain future work.\n\n

## 7.1 Cross-architecture comparison fairness

Every target receives the same deterministic logical operation graphs and operation counts. The controlled comparison uses exactly eight modeled cores, one thread per core, SMT disabled, a 3.0 GHz reference clock, 120-cycle DRAM latency and a 32 B/cycle reference chip-wide DRAM ceiling (NEXSUS 64 B/cycle). AMD, Intel P-core, Intel E-core and NEXSUS are reported separately; P/E results are never averaged. The model now represents the broad cache-sharing topology of each reference target (private vs cluster/package-shared levels) and applies an explicit conventional instruction-fetch refill path to AMD/Intel as well as P0 to NEXSUS. It still simplifies front-end decode, branch prediction, cache ports, MSHRs, coherence and physical DRAM behavior. Therefore this phase is an architecture-oriented comparative model, not a benchmark prediction or a vendor-core cycle-accurate emulator. In particular, generic operation classes are not yet translated into each vendor's exact x86 micro-ops or NEXSUS ISA encodings.

## 8. Roadmap

| Version | Scope | Acceptance condition |
|---|---|---|
| v0.1 | Deterministic kernels, dependency scheduling, basic cache and bank approximation | Initial scaffold |
| v0.2 | Controlled 8-core scheduling with equal reference clocks; dependency-component parallelism | Per-core partition and clock-normalization checks pass |
| v0.2.1 | Initial NEXSUS width experiments and stall diagnostics (historical) | Exploratory variants evaluated; no longer selectable |
| v0.2.2 | Select the 128-window NEXSUS profile; distinguish blocked-operation-cycle events from cycle counters and latency exposure | 128-window profile retained as the sole NEXSUS target |
| v0.2.3 | Enforce 32 B/cycle chip-wide DRAM cap through a static equal share; add regression tests | Verify bandwidth is not multiplied by core count |\n| v0.2.4-dev | Integrate lockstep core scheduling with one shared bank/bus controller; remove static per-core bandwidth split | Same-bank contention and independent-bank overlap covered; cache-group topology is implemented; coherence remains pending |
| v0.3 | Cache coherence, true P/E placement, SMT and NEXSUS P0/SPM/App RAM/L1–L4/8-bank/MEMXFER | Existing NEXSUS contracts represented without invented ISA |
| v0.4 | Interrupts, exceptions, context save/restore, atomic operations and memory ordering | Architectural conformance scenarios pass |
| v0.5 | Calibration against actual Ryzen 9 9950X and Core Ultra 9 285K measurements | Error bounds reported per kernel |
| v1.0 | Stable comparative simulator and repeatable benchmark suite | Reproducible reports and documented limitations |

## 9. Run

From the repository root:

```bash
python "NEXUS CPU/tools/test_cpu_comparison_sim.py"
python "NEXUS CPU/tools/cpu_comparison_sim.py"
python "NEXUS CPU/tools/cpu_comparison_sim.py" --scale 2 --json
python "NEXUS CPU/tools/cpu_comparison_sim.py" --ablation
python "NEXUS CPU/tools/cpu_comparison_sim.py" --ablation --json
python "NEXUS CPU/tools/cpu_comparison_sim.py" --p0-sweep
python "NEXUS CPU/tools/cpu_comparison_sim.py" --p0-capacity-kb 16 --p0-refill-cycles 8 --json
```

The script is a research model, not a substitute for RTL simulation, gem5, vendor performance counters or physical silicon measurements.

## 10. Primary references

- AMD Ryzen 9 9950X specifications: https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x.html
- AMD Zen 5 Hot Chips overview: https://hc2024.hotchips.org/assets/program/conference/day2/24_HC2024.AMD.Cohen.Subramony.final.pdf
- Intel Core Ultra 9 285K specifications: https://www.intel.com/content/www/us/en/products/sku/241060/intel-core-ultra-9-processor-285k-36m-cache-up-to-5-70-ghz/specifications.html
- Intel Lion Cove architecture presentation: https://cdrdv2-public.intel.com/824430/2024_Intel_Tech%20Tour_TW_Next%20Gen%20P-core%20The%20Lion%20Cove%20Architecture-4.pdf
- Skymont analysis: https://chipsandcheese.com/p/skymont-intels-e-cores-reach-for-the-sky
- Arrow Lake Lion Cove memory analysis: https://chipsandcheese.com/p/analyzing-lion-coves-memory-subsystem


## 10. v0.3.0-dev architecture update

The old AMD 9950X / Intel Arrow Lake P/E profile set is superseded for the current comparison run. The active reference profiles are:
- AMD Ryzen 9 9950X3D2 Dual Edition, Zen 5, 16 cores;
- Intel Xeon 698X, Redwood Cove+, 86 homogeneous P-cores;
- Apple M6, 12-core ARM SoC. Its published topology is heterogeneous (2 super, 4 performance, 6 efficiency cores); the current simulator uses a provisional weighted homogeneous approximation until heterogeneous scheduling is implemented;
- NEXSUS CPU, 8-core candidate.

The simulator runs native core counts and retains a normalized 8-core comparison as a separate experiment. These are architectural profiles, not silicon-certified replicas. Reference pipeline/cache latencies and bandwidths not explicitly published by vendors are model assumptions and must be included in result manifests.

### 10.1 PX and SPM0

The old 2×8 KiB P0/P1 command-buffer model is superseded:
- PX P0–P7: eight 2 KiB code-pool slots (16 KiB/core).
- SPM0: 4 KiB total, split into two 2 KiB banks.
- CPU fetch consumes one bank while PX Manager fills the inactive bank.
- Full 2 KiB logical pages continue automatically.
- PX_NEXT and PX_END are metadata read only by PX Manager; they are not instructions and are never copied into SPM0.
- Current simulator refill latency default is 48 cycles: 32 payload cycles at the proposed 64 B/cycle path plus 16 cycles of provisional source/control overhead. This is a sensitivity assumption, not a guaranteed hardware timing.

The fetch model now reports bank switches, ready boundaries, boundary waits, useful bytes, and PX-pool page hit/miss counters. The model still requires richer App-RAM source arbitration, true concurrent refill timing and task-switch invalidation tests before it can claim realistic zero-stall operation.

### 10.2 Branch prediction

A compact NEXSUS branch predictor is a candidate, not yet a frozen architectural commitment. A small direction predictor plus BTB should use logical PC tags, so bank swaps do not invalidate target identity. The simulator currently uses deterministic branch-class miss-rate assumptions for sensitivity only; it is not a cycle-accurate predictor implementation. Per-branch state, BTB aliasing/capacity, warm-up and actual outcome traces remain future work.

### 10.3 Validation status

The GitHub Actions workflow compiles the simulator, runs regression tests, runs the cross-architecture smoke test, executes NEXSUS ablations and runs PX refill sensitivity sweeps. Results are accepted only from the latest run after all steps pass. Historical test counts and old P0/P1 results in earlier sections must not be interpreted as validation of v0.3.0-dev.


## 11. v0.3.1-dev implementation notes

The current executable workload now includes a dedicated ME512 tile kernel. NEXSUS routes it to its modeled ME512 unit; AMD, Intel Xeon and Apple reference profiles map the same logical operation to their generic vector execution resource. This provides comparable algorithmic work without pretending the different instruction sets are identical.

PX metadata validation is now a separate function from the operation stream. It checks:
- full 2 KiB pages continue automatically without an in-band marker;
- partial intermediate pages require PX_NEXT and a valid next logical page;
- partial final pages require PX_END;
- marker placement, page length and 64-bit instruction alignment are valid;
- PX_NEXT/PX_END do not create CPU operations or consume instruction bytes.

The branch predictor experiment has two executable variants: predictor disabled and a compact-predictor assumption. The predictor-off/compact sweep uses the same operation graph for scalar control, pointer decisions and random branch stress. Current prediction rates are deterministic sensitivity inputs, not an RTL predictor.

The CLI also supports a normalized eight-core run, in addition to native package core-count runs. Native results answer whole-chip throughput questions; normalized results help separate core-count scale from per-core design effects.

FAPU and NPU are separate platform accelerators, not CPU execution units. Their DMA, queueing, synchronization and shared-memory arbitration need a separate system-level offload simulation; they are not included in CPU IPC or ME512 throughput.


## 12. Native vector/matrix execution mapping

The simulator now distinguishes 512-bit logical vector work from each backend's modeled native vector width. AMD Zen 5 and Intel Xeon 698X use 512-bit AVX-512 profile paths; Apple M6 uses a provisional 128-bit Advanced SIMD path; NEXSUS uses its proposed 512-bit vector path.

The ME512-equivalent matrix workload maps to:
- NEXSUS dedicated ME512 unit;
- Intel Xeon AMX tile unit;
- AMD vector/FMA path;
- Apple vector path (provisional mapping).

This mapping lets every architecture use its available modeled execution resources. It is still a design-space model: actual port counts, AMX tile setup, memory movement and sustained throughput require public data or independent measurement.


## 13. v0.3.2-dev PX metadata integration

The SPM0 fetch model now accepts logical-page descriptors. It validates the fetch offset against valid_bytes, resolves PX_NEXT to the declared next logical page, stops sequential prefetch on PX_END, and automatically advances full 2 KiB pages. Invalid padding fetches and sequential continuation after PX_END raise a modeled fault. Branch-target fetches can be marked non-sequential so logical PC mapping remains distinct from page-stream continuation.

Regression tests cover full-page automatic continuation, partial intermediate pages, partial final pages, marker-free full pages, invalid padding, wrong next-page IDs and 64-bit alignment. PX_NEXT/PX_END remain descriptor metadata and are not Op records.


An exactly full 2 KiB final page ends through the code-region descriptor (`stream_end=true`); it does not use PX_END. PX_END remains the metadata marker for a partial final page. The fetch model stops prefetching when `stream_end` is set.


## 14. Instruction-fetch model calibration update

The reference I-cache model now uses a bounded 16-line sequential prefetch window, up to 32 outstanding line fills and an 8-cycle default lower-level fill assumption. PX capacity sweeps now run a single 64-KiB code stream on one core rather than splitting the instruction stream across eight cores, with 4/8/16/32/64-KiB pool sizes. The 64-KiB point is a full-residency experimental upper bound.

The PX pool model stages the first pages up to the configured pool capacity at task dispatch. A page that is not resident incurs a configurable 120-cycle provisional App-RAM source-miss penalty plus the PX-to-SPM0 transfer. This makes 4/8/16/32-KiB pool capacity affect actual miss counts and modeled cycles. The 120-cycle source delay is an assumption for sensitivity, not a measured NEXSUS hardware latency.

The CI run checks that pool capacity changes both miss counts and cycles while preserving the same operation count. The separate PX-to-SPM0 refill sweep uses a 64-KiB pool to keep the entire code stream resident and isolates 32, 34 and 48-cycle bank-transfer cases from App-RAM source misses.
