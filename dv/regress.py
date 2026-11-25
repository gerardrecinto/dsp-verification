"""Regression runner: N seeds on the clean design, then every planted bug. A bug that survives is a hole in the testbench."""
import argparse
import glob
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from coverage import merge  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
MUTANTS = {
    "BUG_WRAP": "no saturation, output wraps around",
    "BUG_SATNEG": "negative clamp one code too early",
    "BUG_SHIFT": "logical shift on a signed sum",
    "BUG_TAP": "off-by-one tap reads the wrong delay",
    "BUG_COEF": "coefficient 3 cannot be written",
    "BUG_RESET": "delay line survives reset",
    "BUG_VALID": "every fourth output valid is dropped",
}


def run(seed: int, build: str, out: pathlib.Path, defines: str = "") -> dict:
    results = out / f"results_{build}_{seed}.xml"
    env = dict(os.environ, RANDOM_SEED=str(seed), SIM_BUILD=str(out / f"sim_{build}"),
               COMPILE_ARGS=defines, COCOTB_RESULTS_FILE=str(results), DV_OUT=str(out / build))
    subprocess.run(["make", "-C", str(ROOT), "-s"], env=env, capture_output=True, text=True)
    cases = ET.parse(results).getroot().iter("testcase")
    tests = [(c.get("name"), c.find("failure") is None and c.find("error") is None) for c in cases]
    return {"seed": seed, "passed": sum(ok for _, ok in tests), "failed": [n for n, ok in tests if not ok]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--mutant-seeds", type=int, default=3)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    t0 = time.time()

    clean = [run(s, "clean", out) for s in range(1, a.seeds + 1)]
    cov = merge(glob.glob(str(out / "clean" / "coverage_*.json")))
    killed = {}
    for name, why in MUTANTS.items():
        runs = [run(s, name, out, f"-D{name}") for s in range(1, a.mutant_seeds + 1)]
        by = sorted({t for r in runs for t in r["failed"]})
        killed[name] = {"why": why, "killed": bool(by), "caught_by": by}

    summary = {
        "seeds": a.seeds,
        "clean_failures": sum(len(r["failed"]) for r in clean),
        "tests_per_seed": clean[0]["passed"] + len(clean[0]["failed"]),
        "coverage": cov,
        "mutants": killed,
        "mutation_score": round(100 * sum(m["killed"] for m in killed.values()) / len(killed), 1),
        "seconds": round(time.time() - t0, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "dv.prom").write_text(
        f"dv_regression_seeds {a.seeds}\ndv_regression_failures {summary['clean_failures']}\n"
        f"dv_coverage_percent {cov['percent']}\ndv_mutation_score_percent {summary['mutation_score']}\n"
        f"dv_regression_seconds {summary['seconds']}\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "mutants"}, indent=2))
    for n, m in killed.items():
        print(("KILLED  " if m["killed"] else "SURVIVED"), n, "|", m["why"], "|", ", ".join(m["caught_by"]))
    ok = summary["clean_failures"] == 0 and summary["mutation_score"] == 100 and cov["percent"] == 100
    return 0 if ok else 1


sys.exit(main())
