# NEXSUS CPU — Cross-Architecture Comparison Simulator

**Document ID:** NEXSUS-CPU-COMPARISON-SIMULATOR-001  
**Status:** Simulator v0.3.2-dev; canonical NEXSUS frontend is App RAM→C0→CS0–CS7→CST→EB; OS/WS semantics are specified but workspace timing/transfer simulation is pending  
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

Current architecture anchors (use the Architecture Decision Register as authority):
- 8 cores in the selected comparison profile.
- Arithmetic ALU=8, Logic Unit=8, Compare Unit=8, FP64=6, dedicated FMA=4, VEC=2, ME512=1, LOAD=8, STORE=4 per core.
- Scheduler entries=256 and ROB=512.
- L1=1 MiB private per core; L2=2 MiB shared per core pair; L3=8 MiB shared per four-core group; L4=64 MiB+ shared per eight-core block.
- App RAM and Data RAM are independent memory systems/controllers, each with a 64 B/cycle/core connection.
- Canonical instruction path: App RAM → Code Cache (C0) → Code Slots (CS0–CS7) → Code Stream Transfer (CST) → Execution Buffer (EB).
- Canonical workspaces: OS workspace (OS), Work Space (WS), Context Pool (CP0–CP3), and Exception Workspace (XW); EB is code-fetch-only.
- Architectural register banks: RA0–RA31, FA0–FA31, DA0–DA31 (32 × 64-bit each), MA0–MA31 (32 × 256-bit).
- Shared Register Access Controller budget: 32 logical reads + 32 logical writes per cycle across RA/FA/DA/MA.

The simulator's selected profile uses front-end 8, dispatch 8, issue 10, retire 8, scheduler entries 256 and ROB 512. The execution-resource profile mirrors the unit counts above. These are architecture/model parameters, not a claim of validated silicon timing or throughput.

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

## 7. CodeFlow frontend and OS/WS workspace model status

The canonical instruction-feed path is App RAM → C0 Code Cache → CS0–CS7 Code Slots → CST → EB. The active EB bank supplies instruction fetch while the inactive bank is eligible for refill. The selected stage rates and startup/steady-state accounting are defined in §15; old P0/P1 and SPM0/PX names are historical simulator terminology, not current architectural resource names.

The simulator's earlier generic SPM2 application working-access experiment is **not** the OS/WS architecture model and must not be used as its timing or permission contract. The current architectural workspace contract is:

- OS: 8 KiB, OS-owned, directly byte-addressable by authorized PL1/PL2 code.
- WS: 8 KiB, general-purpose per-core application workspace; PL0 accesses it during an authorized application execution epoch. It is not task-ID-owned or automatically saved as task context.
- WLOAD/WSTORE access OS/WS through DA staging. Workspace endpoints and RA/FA/DA/MA register operands share the core-wide RAC budget. The former 32R/32W limit is under evaluation; the next candidate is 48R/48W, with read-biased alternatives to be tested. Wide workspace operations reserve both endpoint footprints atomically. Physical workspace SRAM bank/port behavior remains separately modeled. See NEXSUS-CPU-RAC-48RW-EVALUATION-001.md.
- XFER.WS.MEM / XFER.WS.START export OS/WS→L1–L4 Data RAM only. The transfer engine may read a workspace source but can never write a workspace destination.
- Data RAM→WS/OS restore is CPU-mediated through Data RAM LOAD→DA→WSTORE. App RAM is not a workspace data source; it remains on the independent instruction-fetch path.
- An optional OS/application exchange window consists of paired OS and WS ranges copied by privileged CPU WLOAD/WSTORE operations at syscall handoff. It is not a shared alias or DMA window.

**Simulator implementation status:** OS/WS address decode, access permissions, shared RAC accounting, multi-port/bank arbitration, one-way export timing, CPU-mediated restore cost, and syscall shadow-window copies are not yet represented as executable simulator resources. Do not report the former generic workspace experiment's 2-cycle/one-port assumptions as OS/WS performance. The next workspace-model phase must add explicit OS/WS resource objects and tests for forbidden external writes, export source reservation, bounds/privilege faults, and CPU-mediated restore.


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
- Intel Lion Cove architecture presentation: https://cdrdv2-public.intel.com/824430/2024_Intel_Tech%20Tour_WS_Next%20Gen%20P-core%20The%20Lion%20Cove%20Architecture-4.pdf
- Skymont analysis: https://chipsandcheese.com/p/skymont-intels-e-cores-reach-for-the-sky
- Arrow Lake Lion Cove memory analysis: https://chipsandcheese.com/p/analyzing-lion-coves-memory-subsystem


## 10. v0.3.0-dev architecture update

The old AMD 9950X / Intel Arrow Lake P/E profile set is superseded for the current comparison run. The active reference profiles are:
- AMD Ryzen 9 9950X3D2 Dual Edition, Zen 5, 16 cores;
- Intel Xeon 698X, Redwood Cove+, 86 homogeneous P-cores;
- Apple M6, 12-core ARM SoC. Its published topology is heterogeneous (2 super, 4 performance, 6 efficiency cores); the current simulator uses a provisional weighted homogeneous approximation until heterogeneous scheduling is implemented;
- NEXSUS CPU, 8-core candidate.

The simulator runs native core counts and retains a normalized 8-core comparison as a separate experiment. These are architectural profiles, not silicon-certified replicas. Reference pipeline/cache latencies and bandwidths not explicitly published by vendors are model assumptions and must be included in result manifests.

### 10.1 Canonical CodeFlow resources

The current instruction path uses these architectural names:
- C0: 64 KiB per-core Code Cache.
- CS0–CS7: eight 2 KiB Code Slots (16 KiB total).
- CST: Code Stream Transfer path, which fills only the inactive EB bank.
- EB: 4 KiB Execution Buffer, split into two 2 KiB banks.
- CFM: CodeFlow Manager, responsible for page validation, ownership, generation, permissions and safe bank switching.

Earlier P0/P1, PX and SPM0 terminology is retained only in historical simulator notes and old result labels. It must not be used as the current ISA or resource map. The active/inactive bank and startup/steady-state invariants are defined in §15.

The fetch model reports bank switches, ready boundaries, boundary waits, useful bytes and code-slot page hit/miss counters. App-RAM source arbitration, concurrent refill timing and task-switch invalidation remain simulator validation items.


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


## Cross-architecture + CodeFlow suite (separate-layer report)

A combined runner is available at `tools/run_cross_arch_codeflow_suite.py`. It executes the same composite logical workload on AMD, Intel, Apple ARM and NEXSUS CPU profiles, then runs the NEXSUS code-feed model at App RAM beat intervals 1/2/4/8.

**Important:** CPU execution and CodeFlow pipeline results are currently separate layers in the report. The CodeFlow cycle count is not yet added to each CPU's total execution cycles; a shared instruction-fetch/scheduler integration is future work. This separation avoids presenting unintegrated front-end latency as an end-to-end result.

Run:

```bash
python run_cross_arch_codeflow_suite.py --scale 1 --pages 64 --tasks 4 --json
```

CI validates operation-count parity across the four CPU models and page completion parity across CodeFlow beat profiles. See the Turkish counterpart in `Türkçe/NEXSUS-CPU-CROSS-ARCH-CODEFLOS-001.md`.


## 15. CodeFlow startup vs steady-state accounting correction (2026-11-24)

**Required comparison correction:** do not treat the Execution Buffer (EB / legacy SPM0, two 2-KiB banks) as an empty buffer throughout execution. EB must be occupied by the active instruction stream during steady-state execution; the inactive bank is the refill destination. A cold start may have an initially empty EB, but that initial fill is a one-time startup condition, not a recurring execution penalty.

Canonical NEXSUS instruction-feed path and names:

`App RAM \u2192 C0 Code Cache (64 KiB; legacy L0I) \u2192 CS0\u2013CS7 Code Slots (8 \u00d7 2 KiB; legacy PX) \u2192 EB Execution Buffer (2 \u00d7 2 KiB banks; legacy SPM0) \u2192 fetch/execute`

### 15.1 Separate startup from steady-state results

Every future NEXSUS CodeFlow comparison must report at least two distinct measures:

- **Cold-start / first-use latency:** cost of initial code availability, including the initial App RAM source transfer into C0 (the full 64-KiB C0 fill when that is the configured startup policy), and the initial CS/EB prefill needed to begin execution. Report the stage assumptions and whether any startup stages overlap.
- **Steady-state execution:** after startup, EB is assumed to remain supplied by the pipeline under the selected rates/queue model. Do not repeatedly charge the cold-empty EB startup penalty to every page or instruction. Count only real refill boundary waits, backpressure, misses, or starvation that the model predicts after the EB banks have been primed.

For workloads of different lengths, report cold-start plus execution total as well as steady-state-only time. Startup cost must not be silently excluded, and must not be charged repeatedly.

### 15.2 Pipeline-stage overlap and occupancy

C0, CS and EB are a staged, overlapping feed path, not a series of independent per-page penalties added to every execution page. Initial pipeline fill can have a critical-path startup cost; once streaming, stage service rates, bounded queues, active/inactive EB bank occupancy, and overlap determine throughput and whether refill misses the consumption deadline.

The EB occupancy invariant for steady-state runs is:
- the active EB bank contains the instruction page/block currently consumed;
- the second bank is the refill/next-ready bank or is explicitly marked as a boundary-transition state;
- an empty EB is allowed only during modeled cold start, a real starvation event, or a defined transition—not as the default state during execution.

The model must track startup-fill cycles separately from steady-state EB-not-ready cycles. A page transfer that overlaps execution is not fully additive to execution time; only unhidden work affects the measured critical path.

### 15.3 Reference instruction-cache fairness

AMD/Intel/Apple reference profiles must also distinguish cold instruction-cache startup/refill from steady-state hits/prefetch. The same report format should show cold-start and steady-state separately, while using each reference profile's own disclosed I-cache assumptions. NEXSUS's explicit stages must not be charged repeatedly while a conventional reference's warmed cache is treated as free—or conversely NEXSUS's initial fill must not be omitted.

### 15.4 Parameter audit required before timing claims

The currently checked-in models contain differing App-RAM transfer abstractions (including an 8-byte beat model in the standalone pipeline and 64 B/cycle per-core App-RAM parameter in the CPU profile). Before producing corrected timing tables, audit and reconcile these against the current architecture decision register. Do not silently choose one value or treat 8 bytes/cycle as the finalized AppRAM bandwidth.

### 15.5 Required metrics

Each CodeFlow comparison row must include:
- startup transfer bytes and startup cycles by stage (App RAM→C0, C0→CS, CS→EB), with overlap assumptions stated;
- C0 hits/misses and occupancy;
- CS hits/misses, slot occupancy and eviction/refill count;
- EB active-bank occupancy, ready-bank occupancy, bank swaps and boundary wait/starvation cycles;
- steady-state instruction/page consumption rate and stage utilization/backpressure;
- cold-start + run total, steady-state-only cycles, and amortized cost over short/medium/long run lengths.

### 15.6 Revalidation status

Historical CodeFlow-integrated comparison totals that do not separate one-time startup from primed steady-state occupancy are **provisional and must be recalculated before being used for architecture ranking**. This correction does not change any hardware capacity or bandwidth decision; it changes benchmark accounting and model validation requirements.


### 15.7 Current selected frontend rates and startup-fill arithmetic

The current Architecture Decision Register (section 4.2) specifies the comparison-model operating point:
- App RAM instruction connection: 64 B/cycle/core (512 B/cycle across 8 cores);
- App RAM→C0 stage: 16 B/cycle;
- C0→CS: 20 B/cycle;
- CS→EB (CST): 20 B/cycle;
- EB consumption: 16 B/cycle;
- frontend queue depth: 2.

These rates are distinct. The 64 B/cycle core-facing App RAM capacity must not be substituted for the 16 B/cycle App RAM→C0 modeled refill-stage rate when calculating the stage's current startup transfer duration.

For a full 64-KiB C0 cold fill at the current modeled 16 B/cycle stage rate, the **payload transfer duration alone** is 4,096 cycles. Any configured first-beat/control overhead must be reported separately and only once per modeled startup/fill transaction. This arithmetic is a model-derived value, not a measured startup time. Initial CS prefill (up to 16 KiB at 20 B/cycle) and EB prefill (4 KiB at 20 B/cycle) are additional stage work, but they may overlap with upstream transfer once pages are available; therefore do not simply add all stage-duration totals to assert a startup critical path. The startup critical path must be calculated from the event-level pipeline timeline.

The standalone pipeline's 8-byte App-RAM beat setting is a different configurable abstraction. It is not the selected comparison operating point and must not be used to replace the rates in the decision register without an explicit architecture/model update.


## 16. Dedicated FP64/FMA resource model correction (2026-11-24)

The simulator and regression contracts now represent the selected NEXSUS execution topology as two independent physical resource pools:

- FP64: 6 execution lanes per core.
- FMA: 4 dedicated execution units per core.
- FMA opcodes map to the independent `FMA` availability array; they do not reserve FP64 lane slots.
- FP opcodes map to the `FP` availability array; they cannot consume FMA slots.
- The reference Intel/AMD/Apple profiles, which do not yet declare a dedicated FMA pool in this simulator, route FMA through their generic FP resource. This is a simulator comparison abstraction, not a claim about the vendors' physical FMA topology.

The old `FMA_LANES` subset model and the test asserting that FMA count must be no greater than FP lane count have been removed. The sweep now permits independent counts, including FMA count greater than FP count.

### 16.1 Constraints deliberately kept separate

- Global issue width remains a shared admission limit.
- FA register read/write ports, operand delivery, bypass and result writeback may constrain simultaneous FP64 + FMA execution.
- The shared RAC budget applies across RA/FA/DA/MA and workspace WLOAD/WSTORE endpoints. Its final R/W capacity is under evaluation; it is not a per-bank budget, and no fixed FA-only port allocation is assumed.
- No result such as “10 operations per cycle” is accepted until FA port topology and global issue limits are modeled and validated.

### 16.2 Required validation

1. Confirm FP-only throughput with FP6.
2. Confirm FMA-only throughput with FMA4.
3. Confirm independent FP and FMA streams can use separate execution pools, bounded by global issue.
4. Confirm mixed FP64 + FMA workload operation-count parity and report any remaining shared-resource stalls.
5. Sweep dependent FMA result latency at 3/4/5/6 cycles while keeping FP6/FMA4 fixed.
6. Re-run all architecture contract tests and regression tests.
7. Only after successful validation, rerun CodeFlow-integrated comparisons with cold-start fill and steady-state EB occupancy reported separately.

The resource-model correction has been committed, but the latest CI run is still in progress. Previous failing runs are not considered validation. No FMA throughput or latency result is accepted until the updated contract and regression suite pass.


## 17. Global issue width and RAC evaluation (2026-11-24)

Global dispatch/issue width remains OPEN. The current experiment candidates are 16, 24 and 32 instructions/cycle. Issue width must be swept independently from RAC logical read/write capacity; do not change both dimensions in one experiment. The known scalar/FP/FMA read-demand envelopes are 36R/52R/68R for issue widths 16/24/32, before VEC/ME512 and workspace operations. These are arithmetic upper envelopes, not simulator throughput results. Normalize all MA and workspace operand footprints before finalizing the RAC. See `NEXSUS-CPU-ISSUE-WIDTH-RAC-DEMAND-001.md` and `NEXSUS-CPU-RAC-48RW-EVALUATION-001.md`.
