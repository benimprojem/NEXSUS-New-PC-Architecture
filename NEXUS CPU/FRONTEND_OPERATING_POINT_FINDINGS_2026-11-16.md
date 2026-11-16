# NEXSUS CPU — Frontend Operating-Point Findings (2026-11-16)

## Scope

These results come from the discrete-cycle integrated frontend simulator. They are architectural model outputs, not RTL, FPGA, or silicon measurements. The model covers the App RAM instruction-fetch path only. App RAM and Data RAM remain independent paths/controllers; Data RAM is not part of these results.

Workload: 32 L0I pages, 2 KiB each. P0/P1 command slots: 8 KiB ping-pong buffers.

## Refined P0/P1 and EB rate matrix

CI run: [43773399757](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43773399757), commit `3d66cb973fdefda642028609bc6559226fa3f607`.

| P0/P1→C0 and EB consume (B/cycle) | Cycles | Change vs 8/8 baseline |
|---:|---:|---:|
| 12/12 | 6071 | -31.6% |
| 14/14 | 5279 | -40.5% |
| 16/16 | 4652 | -47.6% |
| 18/18 | 4624 | -47.9% |
| 20/20 | 4602 | -48.2% |

The 16→20 B/cycle increase saves only 50 cycles (~1.1% of the 16/16 result). The observed operating-point knee is around 16 B/cycle. Do not adopt 24 or 32 B/cycle based on this workload.

Asymmetric pairs show the slower of the two stages dominates: increasing only one side while the other remains at 12 B/cycle does not materially improve the total.

## App RAM bandwidth sensitivity at balanced 16/16

| App RAM (B/cycle) | Refill latency (cycles) | Total cycles |
|---:|---:|---:|
| 32 | 296 | 4780 |
| 48 | 211 | 4695 |
| 64 | 168 | 4652 |
| 128 | 104 | 4588 |

64→128 B/cycle saves 64 total cycles (~1.4%); 48→64 saves 43 cycles (~0.9%). Keep 64 B/cycle as the current baseline candidate; 48 B/cycle is a lower-bandwidth alternative. 128 B/cycle is not justified as a default by this test.

## Queue depth at balanced 16/16

| Queue depth | Cycles | Peak occupancy (C0/CS/EB) |
|---:|---:|---:|
| 1 | 4683 | 1/0/1 |
| 2 | 4652 | 1/0/1 |
| 4 | 4652 | 1/0/1 |
| 8 | 4652 | 1/0/1 |

Depth 2 is sufficient for this modeled workload; deeper queues do not improve throughput.

## Middle-stage rate sweep

CI run: [43774775756](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43774775756), commit `d4695d9a14b6286cd3f0fd442eb94368de1a8ecf`. All 25 configurations retired all 32 pages.

App RAM was fixed at 64 B/cycle, P0/P1→C0 and EB consume at 16 B/cycle, queue depth at 2. C0→CS and CS→EB were swept independently over 12, 16, 20, 24, and 32 B/cycle.

| C0→CS / CS→EB (B/cycle) | Cycles | Change vs 16/16 |
|---:|---:|---:|
| 12/12 | 6071 | +30.50% |
| 16/16 | 4652 | baseline |
| 20/20 | 4602 | -1.07% |
| 24/24 | 4568 | -1.81% |
| 32/32 | 4524 | -2.75% |
| 16/32 or 32/16 | 4588 | -1.38% |

The 12 B/cycle setting is a clear bottleneck. At 16 B/cycle the pipeline is substantially balanced; increasing both middle stages to 32 B/cycle saves only 128 cycles (2.75%). Raising only one stage to 32 while the other remains at 16 saves 64 cycles (1.38%). Therefore 16 B/cycle remains the provisional operating point for both middle stages. The 32 B/cycle option is not justified as the default by this sequential 32-page workload.

## Selected provisional operating point

CI run: [43775751904](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43775751904), commit `dde8eb8e563e5ba45ff56c7fc646a5ec14439dd4`. All 21 workload-length configurations completed successfully: 1, 2, 4, 8, 16, 32, and 64 pages, at balanced middle-stage rates of 16, 20, and 32 B/cycle.

| Pages | 16 B/cycle | 20 B/cycle | 32 B/cycle | 20 vs 16 | 32 vs 16 |
|---:|---:|---:|---:|---:|---:|
| 1 | 684 | 634 | 556 | -7.31% | -18.71% |
| 2 | 812 | 762 | 684 | -6.16% | -15.76% |
| 4 | 1068 | 1018 | 940 | -4.68% | -11.99% |
| 8 | 1580 | 1530 | 1452 | -3.16% | -8.10% |
| 16 | 2604 | 2554 | 2476 | -1.92% | -4.92% |
| 32 | 4652 | 4602 | 4524 | -1.07% | -2.75% |
| 64 | 8748 | 8698 | 8620 | -0.57% | -1.46% |

### Decision

Select **20 B/cycle for both C0→CS and CS→EB** as the balanced provisional operating point. It gives a useful short-burst improvement over 16 B/cycle while avoiding the doubled middle-stage transfer rate of 32 B/cycle, whose incremental benefit shrinks to 1.46% on the 64-page stream. This is an engineering compromise, not a measured area/power optimum; RTL and physical cost are not modeled.

| Stage/resource | Selected provisional setting |
|---|---:|
| App RAM instruction path | 64 B/cycle |
| P0/P1→C0 | 16 B/cycle |
| C0→CS | 20 B/cycle |
| CS→EB | 20 B/cycle |
| EB consume | 16 B/cycle |
| Frontend queue depth | 2 |

The 48 B/cycle App RAM option remains a lower-bandwidth alternative. App RAM and Data RAM remain separate controllers/paths. These are simulator-backed architecture candidates, not a hardware freeze.

## Integrated branch-redirect model

The legacy redirect estimate measured only the isolated App RAM refill. A new integrated estimate now includes the selected frontend stage rates and separately records the prefetched wrong-path P0/P1 block and explicitly parameterized queued wrong-path pages.

Selected-rate first-target-page delivery components:

| Component | Cycles |
|---|---:|
| App RAM refill | 168 |
| P0/P1→C0 | 128 |
| C0→CS | 103 |
| CS→EB | 103 |
| EB delivery | 128 |
| **Serialized target delivery** | **630** |

For the default modeled redirect, the branch resolves at cycle 680 and the target page is ready at cycle 1310. The model separately reports 8192 bytes discarded from the wrong-path P0/P1 block and two queued wrong-path pages (4096 bytes) flushed. The queued-page count is an explicit model input, not an observed queue occupancy.

This is a conservative serialized upper-bound estimate: it does not yet model speculative target fetch, partial refill cancellation, or overlap of target delivery with other stages. It is not RTL or silicon timing. CI coverage was added for the integrated redirect path; do not treat it as validated until the workflow is green.

## Branch recovery latency sweep

The branch-recovery penalty in the core execution model is distinct from the serialized 630-cycle frontend target-delivery upper bound above. The former is the time the modeled frontend is blocked after a misprediction; the latter is a conservative full target-page refill-and-delivery estimate. They must not be conflated or added blindly.

A focused sweep now varies only the NEXSUS frontend recovery penalty across **4, 6, 8, 10, 12, and 16 cycles**, with the compact 2-bit predictor assumption and identical scalar-control, pointer-graph, and branch-stress workloads. Predictor behavior, execution resources, memory parameters, and operation counts remain fixed. The NEXSUS profile was provisionally updated from 10 to **8 cycles** after the sweep. In the branch-stress workload, 8 cycles completes in 79 cycles versus 83 at 10 cycles (4.8% fewer cycles); the same 256 operations and 136 mispredictions are preserved. The scalar-control and pointer-graph totals are unchanged across this penalty sweep, indicating their runtime is dominated by other modeled constraints. The 4-cycle setting is faster in this model, but is not selected without a credible hardware timing basis.

CI run: [43777281592](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43777281592) succeeded, including the branch recovery sweep and all regression tests. The penalty is still a model assumption, not a measured NEXSUS hardware latency.

The target-prefetch overlap sweep completed successfully in CI run [43780989982](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43780989982). It remains an idealized upper-bound experiment: BTB accuracy, App RAM contention, partial refill cancellation, and wrong-path interference are not modeled together.


## App RAM target versus wrong-path arbitration

CI run: [43780989982](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43780989982), commit `6bdb756c3f0f1c2b19f64435ccb61beccc9ab40d`. The run passed all regression and architecture sweeps, including the 15-case two-request contention test and the eight-core fairness sweep. Both JSON reports are included in the CI artifact.

The isolated 2 KiB same-cycle conflict shows the value of admission priority: target-first makes the correct target ready at cycle **72**, versus **128** when the wrong-path request is admitted first. With disjoint banks, the short 16/32-byte requests complete at the same cycle; priority does not create a benefit when there is no bank conflict.

The eight-core stream contains 32 correct-target and 128 speculative 2 KiB page requests (327,680 bytes total), with eight banks, 32 B/cycle aggregate App RAM bandwidth, and eight outstanding slots.

| Admission policy | Target mean wait | Target max wait | Speculative mean wait | Speculative max wait | Final completion |
|---|---:|---:|---:|---:|---:|
| Equal | 6846 | 9248 | 3802.56 | 7968 | 10240 |
| Target first | **456** | **1376** | 5400.06 | 9440 | 10240 |
| Target first + global age promotion (128 cycles) | 5838 | 9248 | 4054.56 | 8096 | 10240 |

All 160 requests were admitted and all bytes were transferred under every policy. The total completion time, queue-full retry count, and bank-conflict count were identical across policies. The policy changes which class gets served first; it does not increase the modeled controller's total throughput.

### Decision

- Keep **correct-target-first admission** as the provisional App RAM arbitration rule when a request is known to be on the resolved execution path.
- Do not prioritize wrong-path speculative fetches ahead of a ready correct-target request when they compete for the same banks/bus.
- Do **not** adopt the tested global 128-cycle age promotion: it largely erases the target-latency benefit and does not provide a better overall trade-off in this workload.
- Preserve per-core round-robin ordering within equal-priority requests. A future continuous-stream hardware model should validate bounded service/fairness for speculative and background requests; the current finite synthetic stream cannot prove starvation freedom.
- Priority affects admission only; it does not preempt an already admitted transfer. App RAM remains fully independent of Data RAM.

The target-first policy cuts mean correct-target admission wait by about **93.3%** versus equal priority in this synthetic stream, while increasing the worst speculative wait by about **18.5%**. This is a deliberate latency trade-off for the instruction path, not a claim of higher aggregate bandwidth. All figures are discrete-cycle model estimates, not RTL or silicon measurements.
