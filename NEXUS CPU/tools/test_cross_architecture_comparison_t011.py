#!/usr/bin/env python3
"""NEX-T011: compare architectures while normalizing only core count, CPU clock and CPU-memory bandwidth."""
from __future__ import annotations

import unittest

import generate_full_architecture_benchmark as benchmark


class CrossArchitectureComparisonT011(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workloads = benchmark.SIM.build_composite_workload(scale=1)
        cls.workloads = {"streaming": workloads["streaming"]}
        cls.common = benchmark.run_mode(
            cls.workloads, normalized=True, common_memory=True
        )
        cls.native = benchmark.run_mode(
            cls.workloads, normalized=True, common_memory=False
        )

    def test_controlled_mode_equalizes_only_cpu_memory_interface(self):
        for arch, result in self.common.items():
            self.assertEqual(result["cores_configured"], 8, arch)
            self.assertEqual(result["clock_ghz"], 3.0, arch)
            stream = result["kernels"]["streaming"]
            self.assertEqual(stream["ops"], len(self.workloads["streaming"]), arch)
            controller = stream["memory_controller"]
            if arch == "nexus_balanced_128":
                self.assertEqual(controller["model"], "per_core_fabric_ports")
                self.assertEqual(controller["per_core_bytes_per_cycle"], 64)
                self.assertEqual(
                    controller["aggregate_core_facing_capacity_bytes_per_cycle"], 512
                )
                self.assertEqual(
                    sum(controller["bytes_by_core"].values()),
                    controller["transferred_bytes"],
                )
                self.assertEqual(set(controller["bytes_by_core"]), set(range(8)))
            else:
                self.assertEqual(controller["model"], "legacy_shared_controller")
                self.assertEqual(controller["aggregate_dram_bytes_per_cycle"], 512)

    def test_memory_latency_is_not_normalized(self):
        for arch in benchmark.ARCHS:
            # The comparison changes only the interface bandwidth and CPU clock.
            # Keep each profile's own modeled memory latency.
            self.assertEqual(
                benchmark.SIM.PROFILES[arch]["dram_lat"],
                benchmark.SIM.PROFILES[arch]["dram_lat"],
            )

    def test_native_nexus_data_ram_contract_is_preserved(self):
        result = self.native["nexus_balanced_128"]
        self.assertEqual(result["cores_configured"], 8)
        controller = result["kernels"]["streaming"]["memory_controller"]
        self.assertEqual(controller["per_core_bytes_per_cycle"], 64)
        self.assertEqual(
            controller["aggregate_core_facing_capacity_bytes_per_cycle"], 512
        )

    def test_operation_counts_match_across_profiles(self):
        counts = {
            result["kernels"]["streaming"]["ops"]
            for result in self.common.values()
        }
        self.assertEqual(counts, {len(self.workloads["streaming"])})


if __name__ == "__main__":
    unittest.main()
