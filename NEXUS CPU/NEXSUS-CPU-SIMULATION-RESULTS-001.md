# NEXSUS CPU — First Full Architecture Simulation Results

**Document ID:** NEXSUS-CPU-SIMULATION-RESULTS-001  
**Run:** GitHub Actions #43514071837  
**Commit:** `7f06b97e5cc9a54251ac6d01bdc86604c561cb8b`  
**Status:** All CI stages passed; results are simulated, not measured silicon performance.

## 1. Test coverage and validation

The run completed:
- 47 regression tests;
- the same 18-kernel mixed workload on all four architecture profiles;
- native-core-count comparison;
- normalized 8-core comparison;
- four-way NEXSUS SPM2/PX ablation;
- branch-predictor sensitivity;
- PX pool capacity sensitivity;
- PX-to-SPM0 refill-latency sensitivity.

All four architectures completed the same **20,846 abstract operations** and passed the workflow's output/operation-count checks.

The 18 kernels cover scalar control, pointer dependencies, numeric tiles, streaming memory, parallel tasks, integer throughput, FP throughput, vector throughput, ME512 matrix tiles, atomic contention, IRQ/exception service proxy, branch stress, SPM hot working set, SPM capacity, PX sequential fetch, PX branch fetch, PX working set, and PX starvation/code-stream stress.

## 2. Architecture profiles

| Profile | Native core count | Modeled architecture |
|---|---:|---|
| AMD Ryzen 9 9950X3D2 Dual Edition | 16 | Zen 5, AVX-512 path |
| Intel Xeon 698X | 86 | Redwood Cove+ P-cores, AVX-512 and AMX |
| Apple M6 | 12 | ARM SoC; 2 super + 4 performance + 6 efficiency cores, represented by a weighted homogeneous approximation |
| NEXSUS CPU | 8 | Proposed architecture; 2 ALUs, 2 FPUs, 2 vector units, ME512, 4 KiB dual-bank SPM0 and 16 KiB PX pool |

Vendor-published core counts and instruction families are used where available. Unpublished pipeline, latency, cache and predictor parameters remain explicit model assumptions.

## 3. Native profile comparison

The following values are the simulator's aggregate cycle counts across the sequential benchmark suite. They are not wall-clock measurements or physical IPC.

| Architecture | Cores | Simulated cycles | Abstract ops | Abstract ops/cycle |
|---|---:|---:|---:|---:|
| AMD Ryzen 9 9950X3D2 | 16 | 55,120 | 20,846 | 0.378 |
| Intel Xeon 698X | 86 | 64,291 | 20,846 | 0.324 |
| Apple M6 | 12 | 45,421 | 20,846 | 0.459 |
| NEXSUS CPU | 8 | 31,532 | 20,846 | 0.661 |

Native package results have different core counts and should not be used as an equal-core comparison.

## 4. Normalized 8-core comparison

| Architecture | Active cores | Simulated cycles | Abstract ops | Abstract ops/cycle |
|---|---:|---:|---:|---:|
| AMD Ryzen 9 9950X3D2 | 8 | 55,774 | 20,846 | 0.374 |
| Intel Xeon 698X | 8 | 65,384 | 20,846 | 0.319 |
| Apple M6 | 8 | 45,782 | 20,846 | 0.455 |
| NEXSUS CPU | 8 | 31,532 | 20,846 | 0.661 |

In this model, NEXSUS completes the common operation graph in fewer simulated cycles. This is a design-space result, not a prediction of measured hardware speed. It is sensitive to the assumed NEXSUS pipeline widths, cache behavior, memory latencies and execution resources.

## 5. NEXSUS SPM2 / PX ablation

| Variant | Simulated cycles | Meaning |
|---|---:|---|
| N-FULL | 31,532 | SPM2 enabled + PX/SPM0 code feed enabled |
| N-NO-SPM | 53,804 | SPM2 local-store benefit disabled; PX remains enabled |
| N-NO-P0 | 30,812 | SPM2 enabled; PX code feed disabled |
| N-BASE | 53,084 | Both SPM2 and PX benefits disabled |

The modeled SPM2 local working set substantially reduces dependent hot-chain and capacity-test cycles. The PX path adds a 40-cycle per-kernel startup difference in this ablation because the modeled first PX-to-SPM0 fill is 48 cycles versus an 8-cycle conventional I-cache startup. The current task-launch model does not yet overlap this initial code fill with context restoration or pre-dispatch preparation.

This does **not** mean the double-bank design has page-boundary bubbles: the dedicated resident-page test below separates startup cost from steady-state bank switching.

## 6. SPM0 double-bank refill experiment

The transfer-latency sweep uses:
- one core;
- an 8,192-instruction / 64 KiB sequential code stream;
- a 64 KiB PX pool so every code page is resident;
- 2 KiB SPM0-A and 2 KiB SPM0-B;
- 31 bank switches across 32 logical pages.

| PX-to-SPM0 refill latency | Total cycles | Fetch wait cycles | Bank switches | PX pool misses |
|---:|---:|---:|---:|---:|
| 32 cycles | 4,129 | 32 | 31 | 0 |
| 34 cycles | 4,131 | 34 | 31 | 0 |
| 48 cycles | 4,145 | 48 | 31 | 0 |
| 64 cycles | 4,161 | 64 | 31 | 0 |
| 96 cycles | 4,193 | 127 | 31 | 0 |

For 32–64-cycle transfers, the wait count is the initial page-fill cost; no additional steady-state boundary wait appears in this workload. At 96 cycles, the model records approximately one additional wait cycle per page boundary.

**Result:** With pages already resident in PX, the 4 KiB / 2×2 KiB SPM0 ping-pong design hides the tested transfer latency through normal execution. The first page still has a startup cost, which can be targeted for overlap with task dispatch/context restoration.

## 7. PX pool capacity and source-miss experiment

This is a separate single-core 64 KiB sequential stream. The first pages up to the configured pool capacity are staged before dispatch. A page outside the pool pays a provisional 120-cycle App-RAM source-miss penalty in addition to the PX-to-SPM0 transfer.

| PX pool capacity | Simulated cycles | Pool hits | Pool misses | Source bytes | Fetch wait cycles |
|---:|---:|---:|---:|---:|---:|
| 4 KiB | 5,282 | 2 | 30 | 60 KiB | 3,052 |
| 8 KiB | 5,202 | 4 | 28 | 56 KiB | 2,846 |
| 16 KiB | 5,042 | 8 | 24 | 48 KiB | 2,434 |
| 32 KiB | 4,722 | 16 | 16 | 32 KiB | 1,610 |
| 64 KiB | 4,145 | 32 | 0 | 0 KiB | 48 |

The 64 KiB point is an experimental full-residency upper bound, not the current 16 KiB design.

**Result:** For resident pages, SPM0 bank switching is not the bottleneck. For code larger than the 16 KiB PX pool, the App-RAM-to-PX source path and its prefetch policy become the dominant concern in this conservative model. The 120-cycle source penalty is an assumption and is currently applied without a full asynchronous App-RAM→PX→SPM0 overlap engine.

## 8. Branch predictor sensitivity

| Kernel | Mispredicts: predictor off → compact | Cycles off → compact |
|---|---:|---:|
| Scalar control | 6 → 2 | 170 → 170 |
| Pointer graph | 5 → 2 | 8,689 → 8,689 |
| Random branch stress | 136 → 136 | 83 → 83 |

The compact predictor assumption reduces mispredictions in predictable control/pointer cases but does not reduce cycles in these workloads. Random branch stress shows no assumed benefit.

**Recommendation:** Keep a small local direction predictor and compact BTB as an optional design candidate, but do not freeze a large predictor yet. Short branch distance inside a 2 KiB page does not remove the need to predict branch direction; it only makes target locality more likely. The current sweep uses deterministic class-based miss rates, not a cycle-accurate 2-bit table/BTB implementation.

## 9. Important limitations

These results are useful for comparing architectural hypotheses, not for claiming physical silicon performance.

1. The reference CPU models are not cycle-accurate vendor replicas. Unpublished pipeline, cache, predictor and latency values are assumptions.
2. Apple M6's heterogeneous core groups are represented by a weighted homogeneous approximation; cluster-aware scheduling is not implemented yet.
3. The branch predictor uses deterministic miss-rate assumptions rather than an implemented predictor table and BTB.
4. IRQ/exception behavior is a deterministic service-latency proxy; asynchronous arrivals, nested exceptions, masking and priority preemption are not yet modeled.
5. Atomic operations use the memory path and shared controller, but full cache-coherence invalidation and atomic-lock protocol are not yet modeled.
6. FAPU, NPU and GPU are separate platform accelerators and are excluded from CPU IPC. They need a separate system-level DMA/offload/coherence benchmark.
7. The PX pool source-miss penalty is provisional. A real App-RAM→PX pool prefetch queue and overlap with PX→SPM0 transfer are still required.
8. “Abstract ops/cycle” is not hardware instructions per cycle. The workload graph is architecture-neutral and backend-mapped.

## 10. Next implementation priorities

1. Model App-RAM→PX pool and PX pool→SPM0 as two overlapped transfer stages with independent queues and arbitration.
2. Overlap first-page/second-page staging with OS context restore and task dispatch.
3. Implement task scheduler events, real CTX_SAVE/CTX_RESTORE residency and task-switch timing.
4. Replace the branch-rate approximation with an actual small predictor and BTB model.
5. Add Apple M6 heterogeneous cluster scheduling.
6. Add coherent atomics, producer/consumer visibility, and asynchronous IRQ/exception injection.
7. Add separate FAPU/NPU/GPU offload and shared-memory arbitration tests.

## 11. Reproduction

Run the simulator checks through the repository workflow:

https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43514071837

Primary benchmark specification:
[NEXSUS-CPU-FULL-ARCHITECTURE-BENCHMARK-001.md](NEXSUS-CPU-FULL-ARCHITECTURE-BENCHMARK-001.md)

Simulator source:
[tools/cpu_comparison_sim.py](tools/cpu_comparison_sim.py)
