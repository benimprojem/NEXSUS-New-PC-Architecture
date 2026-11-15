import unittest
from p0p1_command_buffer_sim import P0P1


class P0P1Tests(unittest.TestCase):
    def test_8k_refill_is_128_data_cycles_plus_setup(self):
        model = P0P1()
        self.assertEqual(model.transfer_cycles, 128)
        self.assertEqual(model.refill_latency, 168)
        self.assertEqual(model.consume_cycles, 1024)

    def test_ping_pong_overlaps_refill_and_avoids_boundary_stalls(self):
        result = P0P1().run(16)
        self.assertEqual(result.blocks_consumed, 16)
        self.assertEqual(result.refill_count, 16)
        self.assertEqual(result.refill_bytes, 16 * 8192)
        self.assertEqual(result.boundary_stalls, 168)  # initial P0 cold fill only
        self.assertGreater(result.overlap_cycles, 0)

    def test_slow_refill_causes_boundary_waits(self):
        result = P0P1(app_bytes_per_cycle=8, setup_latency=40).run(4)
        self.assertGreater(result.boundary_stalls, 40)
        self.assertEqual(result.blocks_consumed, 4)

    def test_invalid_configuration_rejected(self):
        with self.assertRaises(ValueError):
            P0P1(block_bytes=8190)


if __name__ == "__main__":
    unittest.main()
