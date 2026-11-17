#!/usr/bin/env python3
"""NEX-T013: revalidate continuous CodeFlow page delivery and EB ping-pong.

The test uses the approved per-core stage rates. It deliberately keeps the
64-B/cycle AppRAM-facing link separate from the 16-B/cycle AppRAM->C0 stage.
System Fabric is assumed operational; this is a CPU frontend pipeline test.
"""
import unittest

import p0p1_l0i_px_integrated_sim as sim


class InstructionPipelineOverlapT013(unittest.TestCase):
    def test_registered_rates_overlap_and_steady_stream_does_not_starve(self):
        config = sim.Config(
            block_bytes=2048,
            page_bytes=2048,
            app_bytes_per_cycle=64,
            app_setup_cycles=40,
            p0p1_to_c0_bytes_per_cycle=16,
            c0_to_cs_bytes_per_cycle=20,
            cs_to_eb_bytes_per_cycle=20,
            eb_consume_bytes_per_cycle=16,
            queue_depth=4,
        )
        result = sim.IntegratedFrontend(config).run(12)

        self.assertEqual(result.pages_requested, 12)
        self.assertEqual(result.pages_retired, 12)
        self.assertEqual(result.app_bytes_read, 12 * 2048)
        self.assertEqual(result.p0p1_refills, 12)
        self.assertEqual(result.p0p1_cold_stall_cycles, 72)
        self.assertEqual(
            result.p0p1_boundary_stall_cycles, 0,
            "steady sequential pages must be ready before the active EB page drains",
        )
        self.assertEqual(result.eb_consume_busy_cycles, 12 * 128)
        self.assertEqual(result.p0p1_to_c0_busy_cycles, 12 * 128)
        self.assertEqual(result.c0_to_cs_busy_cycles, 12 * 103)
        self.assertEqual(result.cs_to_eb_busy_cycles, 12 * 103)

        serial_sum = (
            result.p0p1_cold_stall_cycles
            + result.p0p1_to_c0_busy_cycles
            + result.c0_to_cs_busy_cycles
            + result.cs_to_eb_busy_cycles
            + result.eb_consume_busy_cycles
        )
        self.assertLess(
            result.cycles, serial_sum,
            "independent pipeline stages must overlap rather than serialize page totals",
        )

    def test_slow_eb_consumer_is_not_silently_ignored(self):
        fast = sim.IntegratedFrontend(sim.Config(
            block_bytes=2048, page_bytes=2048, app_bytes_per_cycle=64,
            app_setup_cycles=40, p0p1_to_c0_bytes_per_cycle=16,
            c0_to_cs_bytes_per_cycle=20, cs_to_eb_bytes_per_cycle=20,
            eb_consume_bytes_per_cycle=16,
        )).run(8)
        slower = sim.IntegratedFrontend(sim.Config(
            block_bytes=2048, page_bytes=2048, app_bytes_per_cycle=64,
            app_setup_cycles=40, p0p1_to_c0_bytes_per_cycle=16,
            c0_to_cs_bytes_per_cycle=20, cs_to_eb_bytes_per_cycle=20,
            eb_consume_bytes_per_cycle=8,
        )).run(8)
        self.assertGreater(slower.eb_consume_busy_cycles, fast.eb_consume_busy_cycles)
        self.assertGreater(slower.cycles, fast.cycles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
