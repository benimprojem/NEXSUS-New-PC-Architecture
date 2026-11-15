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

## Next development step

Use the selected operating point for the next comparison: branch redirect with and without target prefetch/overlap. Keep the current serialized 630-cycle target delivery as the reference case. Avoid another broad bandwidth sweep unless the redirect comparison identifies a specific bottleneck.
