#!/usr/bin/env python3
"""Regression tests for the middle frontend-stage rate sweep."""
from p0p1_l0i_px_middle_sweep import build_cases, run_sweep


def main():
    cases = build_cases()
    assert len(cases) == 25
    assert len({name for name, _ in cases}) == 25
    data = run_sweep(32)
    assert data["cases"] == 25
    assert data["pages"] == 32
    assert data["baseline_cycles"] == 4652
    assert data["baseline"]["pages_retired"] == 32
    assert len(data["results"]) == 25
    for row in data["results"]:
        assert row["pages_retired"] == 32, row["case"]
        depth = row["config"]["queue_depth"]
        assert all(peak <= depth for peak in row["queue_peaks"].values()), row["case"]
    baseline = next(r for r in data["results"] if r["case"] == "c0_cs=16_cs_eb=16")
    assert baseline["cycles"] == 4652
    print("PASS: 25 middle-stage configurations preserve the same 32-page workload.")


if __name__ == "__main__":
    main()
