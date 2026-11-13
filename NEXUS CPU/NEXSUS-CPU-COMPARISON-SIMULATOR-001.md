# NEXSUS CPU — Cross-Architecture Comparison Simulator

**Document ID:** NEXSUS-CPU-COMPARISON-SIMULATOR-001  
**Status:** Simulator v0.2; controlled 8-core dependency-component model (shared-memory contention still pending)  
**Purpose:** Compare one deterministic mixed workload across AMD Zen 5, Intel Arrow Lake P/E cores, and configurable NEXSUS CPU candidates.

## 1. Comparison targets

| Target | Processor | Core model | Physical organization |
|---|---|---|---|
| AMD | Ryzen 9 9950X | Zen 5 | Controlled comparison uses 8 Zen 5 cores; SMT disabled in this phase |
| Intel P | Core Ultra 9 285K | Lion Cove | 8 P-cores |
| Intel E | Core Ultra 9 285K | Skymont | Separate 8 E-core reference profile; not mixed with P-core profile |
| NEXSUS | NEXSUS candidate profile | Current proposed CPU blocks | Minimum comparison configuration: 8 cores |

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

The v0.2 script partitions independent dependency components across eight cores, simulates each core's pipeline, and uses the slowest participating core to determine kernel completion. The text report also provides a per-kernel breakdown (cycles, operations, IPC, active cores and DRAM access count) alongside the composite total. The suite now adds isolated integer, FP, generic vector and branch-throughput kernels to help identify which execution resource limits each profile. It includes dependency tracking, issue-resource limits, in-order retirement, branch stalls, deterministic LRU private-cache approximations and local bank serialization. Shared LLC contention, a globally shared memory controller/bank queue, inter-core coherence traffic and SMT are still pending; current multicore results are therefore an intermediate model, not final throughput predictions. The generic vector kernel does not yet represent ME512's 512-bit paired-register behavior, matrix dimensions or data movement.

## 4. Known public reference points and model assumptions

### AMD Ryzen 9 9950X / Zen 5

AMD's product specification lists 16 cores / 32 threads, up to 5.7 GHz boost, 48 KB L1 data cache per core, 1 MB L2 per core and 64 MB total L3. AMD's Hot Chips Zen 5 overview describes dual 4-wide decode pipes, 8-wide dispatch, a 448-entry retire queue, four load pipes and two store pipes. The simulator uses these as profile anchors; single-thread decode behavior and throughput must be interpreted carefully.

### Intel Core Ultra 9 285K / Arrow Lake

Intel's product specification lists 8 P-cores + 16 E-cores, 24 total cores/threads, up to 5.7 GHz max turbo, 36 MB L3 and 40 MB total L2. The P-core profile represents Lion Cove; the E-core profile represents Skymont. Public architectural analyses provide additional estimates for the front-end, execution window and cache latencies. Those estimates are marked as model inputs, not guaranteed behavior for every workload or firmware configuration.

### NEXSUS candidate

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

NEXSUS dispatch/retire width, scheduling model, branch predictor, ROB-equivalent capacity, cache/bank latency, clock and core count are not frozen. The script's current NEXSUS profile values are deliberately provisional knobs used to make the comparison model runnable. They must not be quoted as architecture decisions or predicted silicon performance.

## 5. Controlled clock and core-count experiment

The first architecture-isolation experiment uses:
- Exactly 8 active cores for AMD, Intel P-core, Intel E-core reference and NEXSUS.
- Exactly 3.0 GHz common reference clock for CPU pipeline and modeled memory timing.
- Identical DRAM latency (120 reference cycles) and aggregate modeled bandwidth (32 bytes/reference cycle) for every profile, including NEXSUS.
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

## 7. Roadmap

| Version | Scope | Acceptance condition |
|---|---|---|
| v0.1 | Deterministic kernels, dependency scheduling, basic cache and bank approximation | Initial scaffold |
| v0.2 | Controlled 8-core scheduling with equal reference clocks; dependency-component parallelism | Per-core partition and clock-normalization checks pass |
| v0.3 | Shared LLC/memory-controller contention, coherence, true P/E placement, SMT and NEXSUS P0/SPM/App RAM/L1–L4/8-bank/MEMXFER | Existing NEXSUS contracts represented without invented ISA |
| v0.4 | Interrupts, exceptions, context save/restore, atomic operations and memory ordering | Architectural conformance scenarios pass |
| v0.5 | Calibration against actual Ryzen 9 9950X and Core Ultra 9 285K measurements | Error bounds reported per kernel |
| v1.0 | Stable comparative simulator and repeatable benchmark suite | Reproducible reports and documented limitations |

## 8. Run

From the repository root:

```bash
python "NEXUS CPU/tools/cpu_comparison_sim.py"
python "NEXUS CPU/tools/cpu_comparison_sim.py" --scale 2 --json
```

The script is a research model, not a substitute for RTL simulation, gem5, vendor performance counters or physical silicon measurements.

## 9. Primary references

- AMD Ryzen 9 9950X specifications: https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x.html
- AMD Zen 5 Hot Chips overview: https://hc2024.hotchips.org/assets/program/conference/day2/24_HC2024.AMD.Cohen.Subramony.final.pdf
- Intel Core Ultra 9 285K specifications: https://www.intel.com/content/www/us/en/products/sku/241060/intel-core-ultra-9-processor-285k-36m-cache-up-to-5-70-ghz/specifications.html
- Intel Lion Cove architecture presentation: https://cdrdv2-public.intel.com/824430/2024_Intel_Tech%20Tour_TW_Next%20Gen%20P-core%20The%20Lion%20Cove%20Architecture-4.pdf
- Skymont analysis: https://chipsandcheese.com/p/skymont-intels-e-cores-reach-for-the-sky
- Arrow Lake Lion Cove memory analysis: https://chipsandcheese.com/p/analyzing-lion-coves-memory-subsystem
