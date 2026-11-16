# NEXSUS CPU — 1/2/4/8-Core Scaling Report

- CI run: [#417](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43878470464)
- Commit tested: `1880d69ad284986a564ac45257fbaaac38c91698`
- Status: **PASS** — compile, regression, all comparison/sweep stages, 1/2/4/8 scaling, full benchmark generation and artifact upload completed.
- Source data: CI artifact `nexus-cpu-comparison-results`, file `nexus-core-scaling/core-scaling-results.csv`.
- Scope: 10 representative kernels × 4 architectures × 4 core counts × 2 DRAM policies = **320 simulated rows**.
- These are simulator estimates, not measurements of physical CPUs.

## How to read the tables

- **Time (µs): lower is better.**
- **Speedup: higher is better.** 1.00× means no benefit from adding cores.
- **Parallel efficiency: higher is better.** It is speedup ÷ core count; 100% would be ideal linear scaling.
- **8-core delta vs best peer: negative means NEXSUS is faster; positive means NEXSUS is slower.**
- The four comparison models use the same 3.0 GHz clock and 120-cycle DRAM latency.
- `fixed_system_32`: aggregate DRAM capacity remains 32 B/cycle for 1, 2, 4 and 8 cores.
- `scaled_4_per_core`: aggregate DRAM capacity is 4/8/16/32 B/cycle at 1/2/4/8 cores.
- Both use a shared work-conserving DRAM bus; there are no static per-core DRAM quotas.
- NEXSUS AppRAM is a separate path: 64 B/cycle per active core. For 8 active cores, aggregate AppRAM is 512 B/cycle. It is not DRAM bandwidth.

## NEXSUS scaling — fixed 32 B/cycle system DRAM

| Kernel | 1 core µs | 2 cores µs | 4 cores µs | 8 cores µs | 8-core speedup | Efficiency | Assessment |
|---|---:|---:|---:|---:|---:|---:|---|
| scalar_control | 0.247 | 0.247 | 0.247 | 0.247 | 1.00× | 12.5% | Control: serial, expected |
| pointer_graph | 2.969 | 2.969 | 2.969 | 2.969 | 1.00× | 12.5% | Memory dependency bound |
| numeric_tile | 0.299 | 0.195 | 0.169 | 0.157 | 1.91× | 23.9% | Weak scaling |
| streaming | 0.677 | 0.537 | 0.457 | 0.376 | 1.80× | 22.5% | Weak scaling under fixed DRAM cap |
| parallel_tasks | 0.180 | 0.151 | 0.137 | 0.130 | 1.38× | 17.2% | Weak scaling |
| integer_throughput | 0.432 | 0.222 | 0.126 | 0.078 | 5.57× | 69.6% | Good scaling |
| fp_throughput | 0.437 | 0.226 | 0.128 | 0.079 | 5.50× | 68.8% | Good scaling |
| branch_stress | 0.306 | 0.167 | 0.097 | 0.062 | 4.91× | 61.4% | Good scaling |
| tw_hot_workset | 0.894 | 0.894 | 0.894 | 0.894 | 1.00× | 12.5% | Single-core hot-workset case |
| cs_sequential | 1.696 | 0.854 | 0.432 | 0.222 | 7.65× | 95.7% | Excellent scaling |

## NEXSUS scaling — DRAM budget scaled per core

| Kernel | 1 core µs | 2 cores µs | 4 cores µs | 8 cores µs | 8-core speedup | Efficiency | Assessment |
|---|---:|---:|---:|---:|---:|---:|---|
| scalar_control | 0.247 | 0.247 | 0.247 | 0.247 | 1.00× | 12.5% | Control: serial, expected |
| pointer_graph | 2.993 | 2.969 | 2.969 | 2.969 | 1.01× | 12.6% | Memory dependency bound |
| numeric_tile | 0.592 | 0.312 | 0.202 | 0.157 | 3.78× | 47.2% | Moderate scaling |
| streaming | 2.299 | 1.275 | 0.703 | 0.376 | 6.11× | 76.4% | Strong scaling when DRAM grows |
| parallel_tasks | 0.298 | 0.185 | 0.149 | 0.130 | 2.29× | 28.6% | Limited/moderate scaling |
| integer_throughput | 0.432 | 0.222 | 0.126 | 0.078 | 5.57× | 69.6% | Good scaling |
| fp_throughput | 0.437 | 0.226 | 0.128 | 0.079 | 5.50× | 68.8% | Good scaling |
| branch_stress | 0.306 | 0.167 | 0.097 | 0.062 | 4.91× | 61.4% | Good scaling |
| tw_hot_workset | 0.894 | 0.894 | 0.894 | 0.894 | 1.00× | 12.5% | Single-core hot-workset case |
| cs_sequential | 1.696 | 0.854 | 0.432 | 0.222 | 7.65× | 95.7% | Excellent scaling |

## Eight-core cross-architecture comparison

This compares the 8-core modeled time against the fastest of the three peer models for each kernel. Both DRAM policies have the same 8-core aggregate DRAM budget (32 B/cycle), so their 8-core results match.

| Kernel | NEXSUS µs | Fastest peer | Peer µs | NEXSUS delta | Result |
|---|---:|---|---:|---:|---|
| scalar_control | 0.247 | AMD 9950X3D2 | 0.051 | +381.8% | Poor |
| pointer_graph | 2.969 | AMD 9950X3D2 | 2.891 | +2.7% | Near peer |
| numeric_tile | 0.157 | AMD 9950X3D2 | 0.125 | +25.3% | Behind |
| streaming | 0.376 | AMD 9950X3D2 | 0.307 | +22.7% | Behind |
| parallel_tasks | 0.130 | Apple M6 | 0.105 | +24.1% | Behind |
| integer_throughput | 0.078 | Intel Xeon 698X | 0.015 | +429.5% | Major weakness |
| fp_throughput | 0.079 | AMD 9950X3D2 | 0.017 | +366.7% | Major weakness |
| branch_stress | 0.062 | AMD 9950X3D2 | 0.039 | +58.5% | Behind |
| tw_hot_workset | 0.894 | AMD 9950X3D2 | 3.190 | -72.0% | **NEXSUS win** |
| cs_sequential | 0.222 | Intel Xeon 698X | 0.029 | +664.4% | Major weakness |

## What is good

1. **CS sequential scaling:** 7.65× at 8 cores and 95.7% efficiency is the strongest scaling result.
2. **Integer/FP scaling:** both reach about 5.5× speedup and ~69% efficiency from the modeled 1-core baseline.
3. **Branch stress:** reaches 4.91× and 61.4% efficiency.
4. **Task Workspace hot workset:** NEXSUS is 72% lower modeled time than the best peer in this test. This is a strong workload-specific result, not a general CPU victory.
5. **Streaming:** scaling improves from 1.80× under a fixed aggregate DRAM cap to 6.11× when DRAM bandwidth scales with core count. This demonstrates that the fixed 32 B/cycle DRAM bus is a major limiter for this workload.

## What is weak / needs investigation

1. **Single-core baseline:** scalar control is about 4.8× slower than peers; integer and FP throughput are also far behind in absolute modeled time. Adding cores improves throughput but does not erase the weak one-core baseline.
2. **CS sequential absolute performance:** despite excellent scaling efficiency, its 8-core time is still about 7.6× slower than the best peer. Scaling efficiency alone is not performance leadership.
3. **Numeric tile / parallel tasks:** 8-core times remain 24–25% behind the fastest peer.
4. **Branch stress:** 8-core time is about 59% higher than the best peer.
5. **Pointer graph:** almost no multicore scaling, consistent with a serial dependency chain; it is only 2.7% behind the fastest peer.

## Interpretation and next engineering priorities

- Do not treat this as evidence that the architecture is faster overall. It shows a mixed profile: excellent scaling in selected kernels, one clear hot-workset win, and substantial absolute-throughput gaps in scalar, integer, FP and CS sequential workloads.
- First inspect the simulator's per-core execution-resource assumptions and instruction/command issue limits behind scalar, INT, FP and CS results. Do not change architecture decisions based on this report alone.
- Next investigate why `parallel_tasks` scales poorly despite 8 configured cores, and separate scheduler/task-dispatch overhead from actual execution throughput.
- Keep fixed-system and per-core-scaled DRAM results separate in future reports; they answer different questions.
- AppRAM bandwidth assertions passed in CI. Per-core 64 B/cycle and aggregate 64 × active cores remain the modeled contract, separate from DRAM.
