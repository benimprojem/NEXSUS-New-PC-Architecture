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

## Provisional recommendation (not a hardware freeze)

- App RAM: 64 B/cycle baseline candidate; retain 48 B/cycle as a cost/area comparison point.
- P0/P1→C0: 16 B/cycle candidate.
- EB consume: 16 B/cycle candidate.
- Queue depth: 2 candidate for these modeled frontend queues.
- Keep all of these as simulator-backed provisional choices until other workloads (branch redirects, short bursts, multi-stream instruction demand, and contention) are tested.

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

## Provisional recommendation (updated; not a hardware freeze)

- App RAM: 64 B/cycle baseline candidate; retain 48 B/cycle as a lower-bandwidth comparison point.
- P0/P1→C0: 16 B/cycle candidate.
- C0→CS: 16 B/cycle candidate.
- CS→EB: 16 B/cycle candidate.
- EB consume: 16 B/cycle candidate.
- Queue depth: 2 candidate for these modeled frontend queues.
- Keep all of these as simulator-backed provisional choices until short bursts, larger streams, branch redirects, multi-stream instruction demand, and contention are tested.

## Next experiment

Run a workload-length sweep (1, 2, 4, 8, 16, 32, and 64 pages) at balanced 16/16, 20/20, and 32/32 middle-stage rates. Keep App RAM at 64 and P0/P1→C0 / EB consume at 16, queue depth 2. This will show whether the apparent 16 B/cycle operating point survives cold-start-dominated short bursts and longer sustained streams.
