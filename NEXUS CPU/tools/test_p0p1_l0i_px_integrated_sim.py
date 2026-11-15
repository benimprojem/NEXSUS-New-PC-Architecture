#!/usr/bin/env python3
"""Regression tests for integrated P0/P1 -> L0I -> PX -> EB frontend."""
import unittest
import p0p1_l0i_px_integrated_sim as sim


class IntegratedFrontendTests(unittest.TestCase):
    def test_default_stream_refills_three_blocks_without_boundary_starvation(self):
        result = sim.IntegratedFrontend(sim.Config()).run(12)
        self.assertEqual(result.pages_requested, 12)
        self.assertEqual(result.pages_retired, 12)
        self.assertEqual(result.p0p1_refills, 3)
        self.assertEqual(result.app_bytes_read, 3 * 8192)
        self.assertEqual(result.app_refill_latency, 168)
        self.assertEqual(result.p0p1_cold_stall_cycles, 168)
        self.assertEqual(result.p0p1_boundary_stall_cycles, 0)

    def test_slow_app_ram_exposes_next_block_boundary_stall(self):
        cfg = sim.Config(app_bytes_per_cycle=8, app_setup_cycles=40)
        result = sim.IntegratedFrontend(cfg).run(8)
        self.assertEqual(result.pages_retired, 8)
        self.assertEqual(result.app_refill_latency, 1064)
        self.assertGreater(result.p0p1_boundary_stall_cycles, 0)

    def test_downstream_stages_overlap_p0p1_page_transfer(self):
        result = sim.IntegratedFrontend(sim.Config()).run(16)
        events = {}
        for event in result.timeline:
            if event["event"] in {"P0P1_C0_START", "C0_CS_START", "CS_EB_START"}:
                events.setdefault(event["page"], {})[event["event"]] = event["cycle"]
        page = events[2]
        self.assertIn("P0P1_C0_START", page)
        self.assertIn("C0_CS_START", page)
        self.assertLess(page["P0P1_C0_START"], page["C0_CS_START"])
        self.assertGreater(result.p0p1_to_c0_busy_cycles, 0)
        self.assertGreater(result.c0_to_cs_busy_cycles, 0)
        self.assertGreater(result.cs_to_eb_busy_cycles, 0)

    def test_queues_remain_bounded(self):
        cfg = sim.Config(queue_depth=1)
        result = sim.IntegratedFrontend(cfg).run(24)
        self.assertLessEqual(result.c0_queue_peak, 1)
        self.assertLessEqual(result.cs_queue_peak, 1)
        self.assertLessEqual(result.eb_queue_peak, 1)

    def test_invalid_page_count_and_configuration_rejected(self):
        with self.assertRaises(ValueError):
            sim.IntegratedFrontend().run(0)
        with self.assertRaises(ValueError):
            sim.IntegratedFrontend(sim.Config(block_bytes=8190))


if __name__ == "__main__":
    unittest.main()
