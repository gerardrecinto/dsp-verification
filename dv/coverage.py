"""Functional coverage: named bins that a stimulus must hit, tracked across every seed."""
from __future__ import annotations

import json
import pathlib

BINS = [
    "input.zero", "input.small", "input.mid", "input.full_pos", "input.full_neg",
    "valid.back_to_back", "valid.gap_1", "valid.gap_long",
    "sat.none", "sat.pos", "sat.neg",
    "coef_write.0", "coef_write.1", "coef_write.2", "coef_write.3",
    "reset.mid_stream", "coef_write.while_streaming",
    "cross.sat_pos_back_to_back", "cross.sat_neg_back_to_back",
    "boundary.exact_min", "boundary.exact_max",
]


class Coverage:
    def __init__(self) -> None:
        self.hits = {b: 0 for b in BINS}

    def hit(self, name: str) -> None:
        self.hits[name] += 1

    def sample_input(self, v: int) -> None:
        a = abs(v)
        if v == 0: self.hit("input.zero")
        elif a < 256: self.hit("input.small")
        elif v >= 0x7000: self.hit("input.full_pos")
        elif v <= -0x7000: self.hit("input.full_neg")
        else: self.hit("input.mid")

    def percent(self) -> float:
        return round(100 * sum(1 for n in self.hits.values() if n) / len(self.hits), 1)

    def write(self, path: pathlib.Path) -> None:
        path.write_text(json.dumps({"percent": self.percent(), "hits": self.hits}, indent=2))


def merge(files: list) -> dict:
    total = {b: 0 for b in BINS}
    for f in files:
        for k, v in json.loads(pathlib.Path(f).read_text())["hits"].items():
            total[k] += v
    return {"percent": round(100 * sum(1 for n in total.values() if n) / len(total), 1), "hits": total}
