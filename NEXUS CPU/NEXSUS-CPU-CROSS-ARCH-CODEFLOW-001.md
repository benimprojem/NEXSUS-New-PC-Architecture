# NEXSUS CPU — Cross-Architecture + CodeFlow Test (CROSS-001)

## Purpose

The combined runner executes one composite workload on four architecture models:
- AMD Ryzen 9 9950X3D2 / Zen 5,
- Intel Xeon 698X,
- Apple M6 ARM,
- 8-core NEXSUS CPU.

It also runs the standalone NEXSUS CodeFlow queue model across App RAM 64-bit beat intervals (1/2/4/8 cycles).

## Integration boundary

NEXSUS CPU dispatch is now gated by CodeFlow page readiness. App RAM→C0, C0→CS and CS→EB delays are included in NEXSUS CPU execution cycles. The supplementary standalone CodeFlow sweep examines queue/overlap behavior and is not added a second time to CPU total cycles.

This remains an architectural timing approximation, not RTL or physical measurements.

## Run

```bash
python run_cross_arch_codeflow_suite.py --scale 1 --pages 64 --tasks 4 --json
```

CI verifies:
- same logical operation count across four architecture models;
- all four CPU profiles appear in the report;
- all four App RAM beat-interval scenarios complete;
- standalone CodeFlow scenarios complete the same page count;
- integrated NEXSUS fetch tests expose App RAM beats, C0 misses, Code Slot/Code Stream transfer counters;
- dispatch cannot proceed before the requested code page is ready.

The JSON output is stored as a GitHub Actions artifact. Results are parameterized simulation outputs, not real CPU benchmarks.
