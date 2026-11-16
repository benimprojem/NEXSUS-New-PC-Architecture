#!/usr/bin/env python3
"""Regression tests for the multi-core App RAM fairness sweep."""
from app_ram_multicore_fairness_sweep import POLICIES, run_sweep


def main() -> None:
    data = run_sweep()
    assert data["policies"] == list(POLICIES)
    assert data["workload"]["controller"]["per_core_bytes_per_cycle"] == 64
    assert data["workload"]["controller"]["core_count"] == 8
    assert data["workload"]["controller"]["aggregate_bytes_per_cycle"] == 512
    assert set(data["results"]) == set(POLICIES)
    for policy, row in data["results"].items():
        assert row["cores"] == 8, policy
        assert row["target_requests"] == 32, policy
        assert row["speculative_requests"] == 128, policy
        assert row["total_requests_admitted"] == 160, policy
        assert row["total_bytes_transferred"] == 160 * 2048, policy
        assert row["last_completion_cycle"] > 0, policy
        assert row["by_request_class"]["target"]["requests"] == 32, policy
        assert row["by_request_class"]["speculative"]["requests"] == 128, policy
        assert set(row["per_core"]) == {str(core) for core in range(8)}, policy
        for core, core_row in row["per_core"].items():
            assert core_row["requests"] == 20, (policy, core)
            assert core_row["target_requests"] == 4, (policy, core)
            assert core_row["speculative_requests"] == 16, (policy, core)
            assert core_row["bytes_transferred"] == 20 * 2048, (policy, core)
        fairness = row["core_fairness"]
        assert fairness["equal_bytes_across_cores"] is True, policy
        assert fairness["bytes_spread"] == 0, policy
        assert row["by_request_class"]["target"]["max_admission_wait_cycles"] >= 0, policy
        assert row["by_request_class"]["speculative"]["max_admission_wait_cycles"] >= 0, policy
    aging = data["results"]["target_first_aging"]
    assert aging["by_request_class"]["speculative"]["max_admission_wait_cycles"] < 30000
    print("PASS: three arbitration policies; 160 requests and 327680 bytes preserved in each eight-core run.")
    for policy, row in data["results"].items():
        target = row["by_request_class"]["target"]
        spec = row["by_request_class"]["speculative"]
        fairness = row["core_fairness"]
        print(
            f"{policy}: cycles={row['last_completion_cycle']} "
            f"core_bytes_spread={fairness['bytes_spread']} "
            f"core_mean_latency_spread={fairness['mean_latency_spread_cycles']} "
            f"target_wait_max={target['max_admission_wait_cycles']} "
            f"spec_wait_max={spec['max_admission_wait_cycles']} "
            f"queue_retries={row['queue_full_retries']}"
        )


if __name__ == "__main__":
    main()
