# NEXSUS CPU — Cross-Architecture Comparison Simulator

**Document ID:** NEXSUS-CPU-COMPARISON-SIMULATOR-001  
**Status:** Simulator v0.1 scaffold; single-stream kernel model only  
**Purpose:** Compare one deterministic mixed workload across AMD Zen 5, Intel Arrow Lake P/E cores, and configurable NEXSUS CPU candidates.

## 1. Comparison targets

| Target | Processor | Core model | Physical organization |
|---|---|---|---|
| AMD | Ryzen 9 9950X | Zen 5 | 16 homogeneous cores, 32 hardware threads |
| Intel P | Core Ultra 9 285K | Lion Cove | 8 Performance cores |
| Intel E | Core Ultra 9 285K | Skymont | 16 Efficient cores |
| NEXSUS | NEXSUS candidate profile | Current proposed CPU blocks | Configurable; default 8 cores is a simulation scenario, not an architecture decision |

AMD and Intel are represented by separate core profiles. The Intel P and E cores must never be averaged into one generic core. The first model uses one hardware thread per core; AMD SMT and OS scheduling are later milestones.

## 2. Shared workload algorithm

The simulator builds the same deterministic operation graph for every target. The algorithm is a composite workload rather than one artificial tight loop.

| Kernel | Algorithmic behavior | Main resources stressed |
|---|---|---|
| scalar_control | Integer recurrence, independent integer transforms, conditional branches | Integer ALUs, register dependencies, front-end and branch recovery |
| pointer_graph | Dependent pointer-chasing loads with decisions | AGU, load queue, cache hierarchy, DRAM latency, branch predictor |
| numeric_tile | Matrix-like tiles, independent input loads, FP accumulation and vector operation | FPU/vector datapaths, register files, load/store |
| streaming | Sequential read-transform-write over a large data range | Load/store throughput, cache lines, memory bandwidth and bank conflicts |
| parallel_tasks | Independent task inputs, scalar/FP work, output and context operations | Core scheduling, synchronization and context save/restore (later parallel model) |

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

The current v0.1 script implements a simplified single-stream pipeline, dependency tracking, issue-resource limits, in-order retirement, branch stalls, a deterministic LRU L1–L4 cache approximation and a simple local bank-serialization model. It deliberately does not claim to model multicore speedup yet.

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

NEXSUS dispatch/retire width, scheduling model, branch predictor, ROB-equivalent capacity, cache/bank latency, clock and core count are not frozen. The script's current NEXSUS profile values are deliberately provisional knobs used to make the first run possible. They must not be quoted as architecture decisions or predicted silicon performance.

## 5. Fairness and measurement rules

- All CPU profiles receive the same logical algorithm, input sizes, dependency graph and deterministic branch pattern.
- Compare single-thread performance separately from multicore throughput.
- Report cycles, elapsed time under a stated frequency assumption, IPC/operations per cycle, cache-level accesses, branch recoveries, resource utilization and memory stalls.
- Do not compare a peak boost clock as if it were sustained all-core frequency. Time conversion in v0.1 is only a configured-clock estimate.
- Do not convert the model's cycle counts into power or energy without a calibrated energy-per-operation and memory-energy model.
- Use measured machine benchmarks to calibrate real AMD/Intel profiles. A model that cannot reproduce reference measurements is not ready for NEXSUS design decisions.
- Keep known, estimated and unknown parameters separately labelled.

## 6. Roadmap

| Version | Scope | Acceptance condition |
|---|---|---|
| v0.1 | Deterministic kernels, dependency scheduling, basic cache and bank approximation | Script runs repeatably; unit tests pass |
| v0.2 | True multicore scheduling, AMD SMT, Intel P/E placement, task migration and shared LLC | Scaling and contention tests pass |
| v0.3 | NEXSUS P0/App RAM path, SPM roles, L1–L4 domain model, 8-bank controllers, MEMXFER | Existing NEXSUS contracts represented without invented ISA |
| v0.4 | Interrupts, exceptions, context save/restore, atomic operations and memory ordering | Architectural conformance scenarios pass |
| v0.5 | Calibration against actual Ryzen 9 9950X and Core Ultra 9 285K measurements | Error bounds reported per kernel |
| v1.0 | Stable comparative simulator and repeatable benchmark suite | Reproducible reports and documented limitations |

## 7. Run

From the repository root:

```bash
python "NEXUS CPU/tools/cpu_comparison_sim.py"
python "NEXUS CPU/tools/cpu_comparison_sim.py" --scale 2 --json
```

The script is a research model, not a substitute for RTL simulation, gem5, vendor performance counters or physical silicon measurements.

## 8. Primary references

- AMD Ryzen 9 9950X specifications: https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x.html
- AMD Zen 5 Hot Chips overview: https://hc2024.hotchips.org/assets/program/conference/day2/24_HC2024.AMD.Cohen.Subramony.final.pdf
- Intel Core Ultra 9 285K specifications: https://www.intel.com/content/www/us/en/products/sku/241060/intel-core-ultra-9-processor-285k-36m-cache-up-to-5-70-ghz/specifications.html
- Intel Lion Cove architecture presentation: https://cdrdv2-public.intel.com/824430/2024_Intel_Tech%20Tour_TW_Next%20Gen%20P-core%20The%20Lion%20Cove%20Architecture-4.pdf
- Skymont analysis: https://chipsandcheese.com/p/skymont-intels-e-cores-reach-for-the-sky
- Arrow Lake Lion Cove memory analysis: https://chipsandcheese.com/p/analyzing-lion-coves-memory-subsystem
