#!/usr/bin/env python3
"""Regression tests for task-aware L0I/PX/SPM0 pipeline."""
import unittest
import l0i_px_pipeline_sim as sim

class PipelineTests(unittest.TestCase):
    def test_all_pages_reach_spm0(self):
        pages=sim.make_pages(12,tasks=3)
        result=sim.Pipeline(sim.Config()).run(pages)
        self.assertEqual(result.pages_completed,12)
        self.assertEqual(result.app_bytes_read,12*2048)
        self.assertEqual(result.app_beats,12*256)

    def test_app_ram_uses_one_64_bit_beat_per_instruction_word(self):
        p=sim.Page("T0",0,0x1000,2048)
        r=sim.Pipeline(sim.Config()).run([p])
        self.assertEqual(r.app_beats,256)
        self.assertEqual(r.app_bytes_read,2048)

    def test_task_streams_have_noncontiguous_source_regions(self):
        p=sim.make_pages(8,tasks=2)
        t0=[x.source_address for x in p if x.task=="T0"]
        t1=[x.source_address for x in p if x.task=="T1"]
        self.assertNotEqual(t0[0],t1[0])
        self.assertGreater(abs(t0[0]-t1[0]),sim.PAGE)

    def test_slower_app_lane_interval_increases_completion_time(self):
        pages=sim.make_pages(16,tasks=2)
        fast=sim.Pipeline(sim.Config(app_beat_interval=1)).run(pages)
        slow=sim.Pipeline(sim.Config(app_beat_interval=4)).run(pages)
        self.assertGreater(slow.cycles,fast.cycles)

    def test_overlapped_stages_reduce_time_vs_serial_service_sum(self):
        pages=sim.make_pages(16,tasks=4)
        result=sim.Pipeline(sim.Config()).run(pages)
        serial_service_sum=(result.app_stage_busy_cycles+
            result.l0i_px_stage_busy_cycles+result.px_spm_stage_busy_cycles)
        self.assertEqual(result.pages_completed,16)
        self.assertLess(result.cycles,serial_service_sum)
        events={}
        for event in result.timeline:
            key=(event.get("task"),event.get("page"))
            events.setdefault(key,{})[event["event"]]=event["cycle"]
        app_start=events[("T1",0)]["APP_READ_START"]
        app_ready=events[("T1",0)]["C0_READY"]
        c0cs_start=events[("T0",0)]["C0_CS_START"]
        cs_ready=events[("T0",0)]["CS_READY"]
        self.assertLess(max(app_start,c0cs_start),min(app_ready,cs_ready))
        self.assertGreater(result.app_stage_busy_cycles,0)
        self.assertGreater(result.l0i_px_stage_busy_cycles,0)
        self.assertGreater(result.px_spm_stage_busy_cycles,0)

    def test_pipeline_queues_remain_bounded_and_report_backpressure(self):
        cfg=sim.Config(app_queue_depth=2,l0i_px_queue_depth=1,px_spm_queue_depth=1)
        result=sim.Pipeline(cfg).run(sim.make_pages(24,tasks=4))
        self.assertLessEqual(result.app_queue_peak,2)
        self.assertLessEqual(result.l0i_px_queue_peak,1)
        self.assertLessEqual(result.px_spm_queue_peak,1)
        self.assertGreaterEqual(result.app_backpressure_cycles,0)
        self.assertGreaterEqual(result.l0i_px_backpressure_cycles,0)
        self.assertGreaterEqual(result.px_spm_backpressure_cycles,0)

    def test_invalid_unaligned_page_rejected(self):
        with self.assertRaises(ValueError):
            sim.Pipeline(sim.Config()).run([sim.Page("T0",0,0,15)])

if __name__=="__main__":
    unittest.main()
