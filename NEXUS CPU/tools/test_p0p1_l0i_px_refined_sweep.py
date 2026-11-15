#!/usr/bin/env python3
"""Regression tests for the refined frontend operating-point sweep."""
from p0p1_l0i_px_refined_sweep import build_cases, run_sweep


def main() -> None:
    cases = build_cases()
    assert len(cases) == 33
    assert len({name for name, _ in cases}) == len(cases)

    data = run_sweep(32)
    assert data["cases"] == 33
    assert data["pages"] == 32
    assert data["baseline_cycles"] == 8876
    assert data["baseline"]["pages_retired"] == 32
    assert len(data["results"]) == 33

    for row in data["results"]:
        assert row["pages_retired"] == 32, row["case"]
        depth = row["config"]["queue_depth"]
        assert all(peak <= depth for peak in row["queue_peaks"].values()), row["case"]

    rate_cases = {
        row["case"]: row for row in data["results"]
        if row["case"].startswith("rates_")
    }
    assert len(rate_cases) == 25
    assert rate_cases["rates_p0=16_eb=16"]["cycles"] < 5000
    assert rate_cases["rates_p0=16_eb=16"]["cycles"] < rate_cases["rates_p0=12_eb=12"]["cycles"]

    app_cases = {
        row["config"]["app_bytes_per_cycle"]: row
        for row in data["results"]
        if row["case"].startswith("app_bandwidth=")
    }
    assert set(app_cases) == {32, 48, 64, 128}
    assert app_cases[128]["app_refill_latency"] < app_cases[64]["app_refill_latency"]
    assert app_cases[128]["cycles"] < app_cases[64]["cycles"]

    queue_cases = {
        row["config"]["queue_depth"]: row
        for row in data["results"]
        if row["case"].startswith("balanced16_queue=")
    }
    assert set(queue_cases) == {1, 2, 4, 8}
    assert queue_cases[2]["cycles"] == queue_cases[4]["cycles"] == queue_cases[8]["cycles"]
    assert queue_cases[1]["cycles"] >= queue_cases[2]["cycles"]

    print("PASS: 33 refined frontend configurations preserve the same 32-page workload.")


if __name__ == "__main__":
    main()
