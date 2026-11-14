#!/usr/bin/env python3
"""Cycle/event model for NEXSUS App RAM -> C0 -> CS -> EB code streaming.

This is a configurable architecture model, not RTL or measured silicon.
The default App RAM beat interval is 1 cycle ONLY as a baseline assumption;
it is not a claim that the physical lane must sustain one beat/cycle.
"""
from __future__ import annotations
import argparse
import json
from collections import deque
from dataclasses import dataclass, asdict
from typing import Deque, Dict, List, Optional, Tuple

PAGE = 2048
C0_BYTES = 64 * 1024
CS_SLOTS = 8
SPM_BANKS = 2

@dataclass
class Page:
    task: str
    logical_id: int
    source_address: int
    valid_bytes: int = PAGE
    marker: Optional[str] = None
    next_logical_id: Optional[int] = None

@dataclass
class Config:
    app_lane_bytes: int = 8
    app_beat_interval: int = 1
    app_first_beat_latency: int = 40
    app_queue_depth: int = 4
    l0i_to_px_bytes_per_cycle: int = 16
    px_to_spm_bytes_per_cycle: int = 16
    l0i_capacity_bytes: int = C0_BYTES
    px_slot_count: int = CS_SLOTS
    page_bytes: int = PAGE
    spm_bank_bytes: int = PAGE
    l0i_hit_latency: int = 1
    px_hit_latency: int = 1
    l0i_px_queue_depth: int = 4
    px_spm_queue_depth: int = 4

@dataclass
class Result:
    cycles: int
    pages_completed: int
    app_bytes_read: int
    app_beats: int
    l0i_hits: int
    l0i_misses: int
    px_hits: int
    px_misses: int
    app_queue_peak: int
    l0i_px_queue_peak: int
    px_spm_queue_peak: int
    spm_bank_swaps: int
    stalls_spm_not_ready: int
    slot_evictions: int
    app_stage_busy_cycles: int
    l0i_px_stage_busy_cycles: int
    px_spm_stage_busy_cycles: int
    app_backpressure_cycles: int
    l0i_px_backpressure_cycles: int
    px_spm_backpressure_cycles: int
    timeline: List[dict]

class Pipeline:
    """Three independently scheduled queues and a two-bank EB consumer."""
    def __init__(self, config: Config):
        self.c = config
        self.app_q: Deque[Page] = deque()
        self.l0px_q: Deque[Page] = deque()
        self.pxspm_q: Deque[Page] = deque()
        self.l0i: Dict[Tuple[str,int], Page] = {}
        self.l0i_order: Deque[Tuple[str,int]] = deque()
        self.px: Dict[Tuple[str,int], Page] = {}
        self.px_order: Deque[Tuple[str,int]] = deque()
        self.spm = [None, None]
        self.active_bank = 0
        self.spm_remaining = 0
        self.page_index = 0
        self.app_active = None
        self.app_done_cycle = 0
        self.l0px_active = None
        self.l0px_done_cycle = 0
        self.pxspm_active = None
        self.pxspm_done_cycle = 0
        self.pages: List[Page] = []
        self.timeline=[]
        self.counters = dict(app_bytes_read=0, app_beats=0, l0i_hits=0,
            l0i_misses=0, px_hits=0, px_misses=0, app_queue_peak=0,
            l0i_px_queue_peak=0, px_spm_queue_peak=0, spm_bank_swaps=0,
            stalls_spm_not_ready=0, slot_evictions=0, pages_completed=0,
            app_stage_busy_cycles=0, l0i_px_stage_busy_cycles=0,
            px_spm_stage_busy_cycles=0, app_backpressure_cycles=0,
            l0i_px_backpressure_cycles=0, px_spm_backpressure_cycles=0)

    def _cache_insert(self, cache, order, key, page, cap):
        if key in cache:
            cache[key] = page
            return
        cache[key] = page
        order.append(key)
        while len(cache) > cap:
            old = order.popleft()
            if old in cache:
                del cache[old]
                if cache is self.px:
                    self.counters["slot_evictions"] += 1

    def _app_duration(self, page):
        beats=(page.valid_bytes+self.c.app_lane_bytes-1)//self.c.app_lane_bytes
        return self.c.app_first_beat_latency + max(0,beats-1)*self.c.app_beat_interval + 1

    def _transfer_duration(self, nbytes, rate):
        return max(1, (nbytes+rate-1)//rate)

    def run(self, pages: List[Page], max_cycles: int = 10_000_000) -> Result:
        if not pages: raise ValueError("at least one code page is required")
        if any(p.valid_bytes<=0 or p.valid_bytes>self.c.page_bytes or p.valid_bytes%8 for p in pages):
            raise ValueError("page valid_bytes must be 8-byte aligned and within page size")
        if min(self.c.app_queue_depth,self.c.l0i_px_queue_depth,self.c.px_spm_queue_depth)<=0:
            raise ValueError("pipeline queue depths must be positive")
        if self.c.app_lane_bytes != 8:
            raise ValueError("baseline App RAM instruction lane is exactly 64-bit (8 bytes)")
        self.pages=pages
        total=len(pages)
        # Demand-driven: enqueue page requests; bounded App RAM request queue.
        for cycle in range(max_cycles):
            # EB CPU consumer: consume current bank's valid instruction bytes.
            if self.spm_remaining>0:
                self.spm_remaining-=8
            if self.spm_remaining<=0:
                if self.spm[self.active_bank] is not None:
                    self.spm[self.active_bank]=None
                other=1-self.active_bank
                if self.spm[other] is not None:
                    self.active_bank=other
                    self.spm_remaining=self.spm[self.active_bank].valid_bytes
                    self.counters["spm_bank_swaps"]+=1
            # Start/complete CS -> inactive EB refill.
            if self.pxspm_active is not None and cycle>=self.pxspm_done_cycle:
                p=self.pxspm_active
                bank=1-self.active_bank
                self.spm[bank]=p
                self.timeline.append({"cycle":cycle,"event":"EB_READY","task":p.task,"page":p.logical_id,"bank":bank})
                self.pxspm_active=None
                self.counters["pages_completed"]+=1
            px_bank=1-self.active_bank
            px_bank_available=self.spm[px_bank] is None
            if self.pxspm_q and not px_bank_available:
                self.counters["px_spm_backpressure_cycles"]+=1
            if (self.pxspm_active is None and self.pxspm_q and px_bank_available
                    and self.l0px_active is None and self.app_active is None):
                p=self.pxspm_q.popleft()
                self.pxspm_active=p
                self.pxspm_done_cycle=cycle+self._transfer_duration(p.valid_bytes,self.c.px_to_spm_bytes_per_cycle)
                self.counters["px_spm_stage_busy_cycles"]+=self._transfer_duration(p.valid_bytes,self.c.px_to_spm_bytes_per_cycle)
                self.timeline.append({"cycle":cycle,"event":"CS_EB_START","task":p.task,"page":p.logical_id})
            # C0 -> CS independent queue; select page/task request.
            if (self.l0px_active is not None and cycle>=self.l0px_done_cycle
                    and len(self.pxspm_q)<self.c.px_spm_queue_depth):
                p=self.l0px_active; key=(p.task,p.logical_id)
                self._cache_insert(self.px,self.px_order,key,p,self.c.px_slot_count)
                self.pxspm_q.append(p)
                self.timeline.append({"cycle":cycle,"event":"CS_READY","task":p.task,"page":p.logical_id})
                self.l0px_active=None
            if self.l0px_active is not None and cycle>=self.l0px_done_cycle and len(self.pxspm_q)>=self.c.px_spm_queue_depth:
                self.counters["l0i_px_backpressure_cycles"]+=1
            if (self.l0px_active is None and self.l0px_q
                    and self.pxspm_active is None and self.app_active is None):
                p=self.l0px_q.popleft()
                self.l0px_active=p
                self.l0px_done_cycle=cycle+self._transfer_duration(p.valid_bytes,self.c.l0i_to_px_bytes_per_cycle)
                self.counters["l0i_px_stage_busy_cycles"]+=self._transfer_duration(p.valid_bytes,self.c.l0i_to_px_bytes_per_cycle)
                self.timeline.append({"cycle":cycle,"event":"C0_CS_START","task":p.task,"page":p.logical_id})
            # App RAM -> C0 chunks/page, bounded queue. Existing C0 hit bypasses App RAM.
            while self.page_index<total and len(self.app_q)<self.c.app_queue_depth:
                p=pages[self.page_index]; self.page_index+=1
                key=(p.task,p.logical_id)
                if key in self.l0i:
                    self.counters["l0i_hits"]+=1
                    self.l0px_q.append(self.l0i[key])
                    self.timeline.append({"cycle":cycle,"event":"C0_HIT","task":p.task,"page":p.logical_id})
                elif key in self.px:
                    self.counters["px_hits"]+=1
                    self.pxspm_q.append(self.px[key])
                    self.timeline.append({"cycle":cycle,"event":"CS_HIT","task":p.task,"page":p.logical_id})
                else:
                    self.counters["l0i_misses"]+=1
                    self.counters["px_misses"]+=1
                    self.app_q.append(p)
                    self.timeline.append({"cycle":cycle,"event":"APP_REQUEST","task":p.task,"page":p.logical_id,"source":p.source_address})
            if (self.app_active is not None and cycle>=self.app_done_cycle
                    and len(self.l0px_q)<self.c.l0i_px_queue_depth):
                p=self.app_active; key=(p.task,p.logical_id)
                self._cache_insert(self.l0i,self.l0i_order,key,p,max(1,self.c.l0i_capacity_bytes//self.c.page_bytes))
                self.l0px_q.append(p)
                self.timeline.append({"cycle":cycle,"event":"C0_READY","task":p.task,"page":p.logical_id})
                self.app_active=None
            if self.app_active is not None and cycle>=self.app_done_cycle and len(self.l0px_q)>=self.c.l0i_px_queue_depth:
                self.counters["app_backpressure_cycles"]+=1
            if (self.app_active is None and self.app_q
                    and self.l0px_active is None and self.pxspm_active is None):
                p=self.app_q.popleft(); self.app_active=p
                self.app_done_cycle=cycle+self._app_duration(p)
                self.counters["app_stage_busy_cycles"]+=self._app_duration(p)
                beats=(p.valid_bytes+self.c.app_lane_bytes-1)//self.c.app_lane_bytes
                self.counters["app_bytes_read"]+=p.valid_bytes
                self.counters["app_beats"]+=beats
                self.timeline.append({"cycle":cycle,"event":"APP_READ_START","task":p.task,"page":p.logical_id,"beats":beats})
            if self.page_index<total and len(self.app_q)>=self.c.app_queue_depth:
                self.counters["app_backpressure_cycles"]+=1
            self.counters["app_queue_peak"]=max(self.counters["app_queue_peak"],len(self.app_q))
            self.counters["l0i_px_queue_peak"]=max(self.counters["l0i_px_queue_peak"],len(self.l0px_q))
            self.counters["px_spm_queue_peak"]=max(self.counters["px_spm_queue_peak"],len(self.pxspm_q))
            # Keep CPU consumption visible: a page is ready only if current/next SPM bank exists.
            if self.spm_remaining<=0 and self.spm[self.active_bank] is None and self.spm[1-self.active_bank] is None:
                self.counters["stalls_spm_not_ready"]+=1
            if self.counters["pages_completed"]>=total:
                summary=dict(self.counters)
                summary["pages_completed"]=total
                return Result(cycle+1,**summary,timeline=self.timeline)
        raise TimeoutError(f"pipeline did not complete {total} pages within {max_cycles} cycles")

def make_pages(count:int, tasks:int=2, page_bytes:int=PAGE, stride:int=0x5000)->List[Page]:
    """Interleave task streams whose source App RAM regions are non-contiguous."""
    out=[]
    for i in range(count):
        task=f"T{i%tasks}"
        logical=i//tasks
        source=(0x10000000 if task=="T0" else 0x30000000)+logical*stride
        out.append(Page(task,logical,source,page_bytes))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pages",type=int,default=64)
    ap.add_argument("--tasks",type=int,default=2)
    ap.add_argument("--beat-interval",type=int,default=1)
    ap.add_argument("--app-first-latency",type=int,default=40)
    ap.add_argument("--l0px-rate",type=int,default=16)
    ap.add_argument("--pxspm-rate",type=int,default=16)
    ap.add_argument("--json",action="store_true")
    args=ap.parse_args()
    cfg=Config(app_beat_interval=args.beat_interval,app_first_beat_latency=args.app_first_latency,
        l0i_to_px_bytes_per_cycle=args.l0px_rate,px_to_spm_bytes_per_cycle=args.pxspm_rate)
    result=Pipeline(cfg).run(make_pages(args.pages,args.tasks))
    data=asdict(result)
    if args.json: print(json.dumps(data,indent=2))
    else:
        for k,v in data.items():
            if k!="timeline": print(f"{k}: {v}")
        print(f"timeline events: {len(result.timeline)}")
if __name__=="__main__": main()
