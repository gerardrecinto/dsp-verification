"""cocotb testbench for fir4: directed tests, constrained-random streams, a cycle-accurate scoreboard, assertions and coverage."""
import json
import os
import pathlib
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from coverage import Coverage
from model import MAX, MIN, Fir4Model

OUT = pathlib.Path(os.environ.get("DV_OUT", "dv_out"))
COV = Coverage()


class Env:
    def __init__(self, dut):
        self.dut = dut
        self.model = Fir4Model()
        self.cycles = 0
        self.gap = 0          # idle cycles since the last valid input
        self.last_valid = False

    async def start(self):
        cocotb.start_soon(Clock(self.dut.clk, 10, units="ns").start())
        self.drive(rst_n=0)
        for _ in range(3):
            await self.cycle(rst_n=0)

    def drive(self, rst_n=1, in_valid=0, in_data=0, coef_we=0, coef_idx=0, coef_data=0):
        d = self.dut
        d.rst_n.value, d.in_valid.value, d.in_data.value = rst_n, in_valid, in_data
        d.coef_we.value, d.coef_idx.value, d.coef_data.value = coef_we, coef_idx, coef_data

    async def cycle(self, rst_n=1, in_valid=0, in_data=0, coef_we=0, coef_idx=0, coef_data=0):
        """Drive one clock, then compare the DUT with the model. This is the scoreboard."""
        self.drive(rst_n, in_valid, in_data, coef_we, coef_idx, coef_data)
        await RisingEdge(self.dut.clk)
        await Timer(1, units="ns")
        exp = self.model.step(rst_n, in_valid, in_data, coef_we, coef_idx, coef_data)
        self.sample(rst_n, in_valid, in_data, coef_we, coef_idx, exp)
        d = self.dut
        for sig in (d.out_valid, d.out_data, d.sat):
            assert sig.value.is_resolvable, f"cycle {self.cycles}: {sig._name} is X or Z"   # assertion: no unknowns
        got = (int(d.out_valid.value), d.out_data.value.signed_integer, int(d.sat.value))
        assert got == exp, f"cycle {self.cycles}: expected {exp}, DUT gave {got}"
        if got[2]:
            assert got[1] in (MAX, MIN), f"cycle {self.cycles}: sat flag set but data is {got[1]}"   # assertion
        self.cycles += 1

    def sample(self, rst_n, in_valid, in_data, coef_we, coef_idx, exp):
        if not rst_n:
            return
        if in_valid:
            COV.sample_input(in_data)
            if self.last_valid: COV.hit("valid.back_to_back")
            elif self.gap == 1: COV.hit("valid.gap_1")
            elif self.gap > 1: COV.hit("valid.gap_long")
            self.gap = 0
        else:
            self.gap += 1
        if coef_we:
            COV.hit(f"coef_write.{coef_idx}")
            if self.last_valid or in_valid: COV.hit("coef_write.while_streaming")
        if exp[0]:
            COV.hit("sat.pos" if exp[2] and exp[1] == MAX else "sat.neg" if exp[2] else "sat.none")
            if not exp[2] and exp[1] == MIN: COV.hit("boundary.exact_min")
            if not exp[2] and exp[1] == MAX: COV.hit("boundary.exact_max")
            if exp[2] and self.last_valid:
                COV.hit("cross.sat_pos_back_to_back" if exp[1] == MAX else "cross.sat_neg_back_to_back")
        self.last_valid = bool(in_valid)

    async def load(self, coefs):
        for i, c in enumerate(coefs):
            await self.cycle(coef_we=1, coef_idx=i, coef_data=c)

    async def stream(self, samples, idle=0):
        for s in samples:
            await self.cycle(in_valid=1, in_data=s)
            for _ in range(idle):
                await self.cycle()

    async def flush(self):
        for _ in range(4):
            await self.cycle()


@cocotb.test()
async def test_reset_and_idle(dut):
    env = Env(dut)
    await env.start()
    for _ in range(5):
        await env.cycle()
    assert int(dut.out_valid.value) == 0


@cocotb.test()
async def test_impulse_response(dut):
    env = Env(dut)
    await env.start()
    await env.load([0x4000, 0x2000, 0x1000, 0x0800])
    await env.stream([0x4000, 0, 0, 0, 0, 0])
    await env.flush()


@cocotb.test()
async def test_every_coefficient_slot(dut):
    env = Env(dut)
    await env.start()
    for slot in range(4):
        await env.cycle(rst_n=0)
        coefs = [0, 0, 0, 0]
        coefs[slot] = 0x3000 + slot
        await env.load(coefs)
        await env.stream([0x1000, 0x0100, -0x0200, 0x0040, 0x0007])
        await env.flush()


@cocotb.test()
async def test_saturation_corners(dut):
    env = Env(dut)
    await env.start()
    await env.load([0x7FFF, 0x7FFF, 0x7FFF, 0x7FFF])
    await env.stream([MAX] * 6)                 # positive overflow
    await env.stream([MIN] * 6)                 # negative overflow
    await env.load([0x7FFF, 0, 0, 0])
    await env.stream([MIN, MIN, MAX, 0])        # exact -32768 and +32767 outputs
    await env.load([-0x8000, 0, 0, 0])
    await env.stream([MIN, MAX, 1, -1])         # most negative coefficient
    await env.flush()


@cocotb.test()
async def test_boundary_values(dut):
    """Outputs of exactly -32768 and +32767 must NOT set sat; one code beyond must. Boundaries are where clamps go wrong."""
    env = Env(dut)
    await env.start()
    await env.load([-0x8000, -1, 0, 0])         # second sample: -32768*32767 + -1*32767 = -2**30 + 1, scaled exactly -32768
    await env.stream([MAX, MAX, MAX])
    await env.load([0x7FFF, 0x7FFF, 0, 0])      # 0x4000 twice: scaled exactly +32767
    await env.stream([0x4000, 0x4000, 0x4000])
    await env.load([0x7FFF, 0x7FFF, 0x7FFF, 0])
    await env.stream([0x4000, 0x4000, 0x4000, 0x4000])   # one tap more: clamps to +32767 with sat set
    await env.flush()


@cocotb.test()
async def test_reset_mid_stream(dut):
    env = Env(dut)
    await env.start()
    await env.load([0x4000, 0x4000, 0x4000, 0x4000])
    await env.stream([0x2000, 0x2000, 0x2000, 0x2000])
    COV.hit("reset.mid_stream")
    await env.cycle(rst_n=0)
    await env.load([0x4000, 0x4000, 0x4000, 0x4000])
    await env.stream([0x1000, 0, 0, 0, 0])      # old samples must not leak into these outputs
    await env.flush()


@cocotb.test()
async def test_coefficient_update_while_streaming(dut):
    env = Env(dut)
    await env.start()
    await env.load([0x2000, 0x2000, 0x2000, 0x2000])
    for i in range(40):
        await env.cycle(in_valid=1, in_data=(i * 733) % 20000 - 10000,
                        coef_we=1 if i % 5 == 0 else 0, coef_idx=i % 4, coef_data=(i * 911) % 30000 - 15000)
    await env.flush()


def rand_sample(rng, mode):
    if mode == "small":
        return rng.randint(-200, 200)
    if mode == "edge":
        return rng.choice([MAX, MIN, 0, 1, -1, MAX - 1, MIN + 1])
    return rng.randint(MIN, MAX)


@cocotb.test()
async def test_constrained_random(dut):
    """Phases switch the constraints; valid gaps, coefficient writes and rare resets are mixed in."""
    rng = random.Random(cocotb.RANDOM_SEED)
    env = Env(dut)
    await env.start()
    await env.load([rng.randint(-0x8000, 0x7FFF) for _ in range(4)])
    for phase in range(12):
        mode = rng.choice(["small", "edge", "full"])
        p_valid = rng.choice([1.0, 0.7, 0.3])
        for _ in range(250):
            if rng.random() < 0.004:
                await env.cycle(rst_n=0)
                COV.hit("reset.mid_stream")
                continue
            we = 1 if rng.random() < 0.03 else 0
            await env.cycle(in_valid=1 if rng.random() < p_valid else 0,
                            in_data=rand_sample(rng, mode),
                            coef_we=we, coef_idx=rng.randint(0, 3), coef_data=rng.randint(-0x8000, 0x7FFF))
    await env.flush()


@cocotb.test()
async def test_write_coverage(dut):
    OUT.mkdir(exist_ok=True)
    COV.write(OUT / f"coverage_{cocotb.RANDOM_SEED}.json")
