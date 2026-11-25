"""Cycle-accurate reference model of fir4. It mirrors the RTL's registers, so the scoreboard can compare every cycle."""
from __future__ import annotations

from dataclasses import dataclass, field

MAX, MIN = 32767, -32768


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


@dataclass
class Fir4Model:
    c: list = field(default_factory=lambda: [0, 0, 0, 0])
    x: list = field(default_factory=lambda: [0, 0, 0, 0])   # x[0] is the newest sample
    acc: int = 0
    v1: int = 0
    out_valid: int = 0
    out_data: int = 0
    sat: int = 0

    def step(self, rst_n: int, in_valid: int, in_data: int, coef_we: int, coef_idx: int, coef_data: int) -> tuple:
        """Advance one clock edge using the register values from before the edge, as the RTL does."""
        if not rst_n:
            self.__init__()
            return self.out_valid, self.out_data, self.sat
        old_c, old_x, old_acc, old_v1 = list(self.c), list(self.x), self.acc, self.v1
        if coef_we:
            self.c[coef_idx] = coef_data
        self.v1 = in_valid
        if in_valid:
            self.x = [in_data, old_x[0], old_x[1], old_x[2]]
            self.acc = in_data * old_c[0] + old_x[0] * old_c[1] + old_x[1] * old_c[2] + old_x[2] * old_c[3]
        self.out_valid = old_v1
        if old_v1:
            scaled = old_acc >> 15            # Python >> on a negative int is arithmetic, like >>> in Verilog
            if scaled > MAX:
                self.out_data, self.sat = MAX, 1
            elif scaled < MIN:
                self.out_data, self.sat = MIN, 1
            else:
                self.out_data, self.sat = scaled, 0
        return self.out_valid, self.out_data, self.sat
