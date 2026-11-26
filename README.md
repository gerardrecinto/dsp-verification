# dsp-verification

[![CI](https://github.com/gerardrecinto/dsp-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/gerardrecinto/dsp-verification/actions/workflows/ci.yml)

Design verification for a 4-tap fixed-point FIR filter in Verilog: constrained-random stimulus, a cycle-accurate scoreboard, assertions, functional coverage, and seven planted bugs the tests must catch.

**Site, with a bug hunt you can run in the browser: https://gerardrecinto.github.io/dsp-verification/**

## Run it

```bash
git clone https://github.com/gerardrecinto/dsp-verification && cd dsp-verification
docker build -t dsp-verification .
docker run --rm dsp-verification          # about 3 minutes; exits 1 if anything is missed
```

Without Docker: install Icarus Verilog and `pip install cocotb==1.9.2`, then `make RANDOM_SEED=1` for one seed or `python dv/regress.py` for everything.

## What is in it

| Piece | What it does |
|---|---|
| `rtl/fir4.v` | Filter: Q1.15 coefficients, 4 taps, saturating 16-bit output, 2-clock latency. `BUG_*` macros plant one error each. |
| `dv/model.py` | Cycle-accurate reference model that mirrors the RTL registers. |
| `dv/test_fir4.py` | 9 cocotb tests: reset, impulse, every coefficient slot, saturation corners, boundary values, reset mid-stream, coefficient writes while streaming, constrained random. Scoreboard compares every clock; assertions check for unknown values and sat flag. |
| `dv/coverage.py` | 21 functional coverage bins, including crosses (saturation during back-to-back input) and exact boundaries. |
| `dv/regress.py` | N seeds on the clean design, then each planted bug. Exits 1 on a failure, a surviving bug, or coverage under 100%. Writes `summary.json` and Prometheus metrics. |
| `charts/dv-regression` | Helm chart: the regression as a nightly Kubernetes CronJob. |
| `monitoring/` | Alert rules (clean design failing, surviving bug, low coverage) with promtool tests, and a Grafana dashboard. |
| `.github/workflows`, `.gitlab-ci.yml` | CI on GitHub Actions; the same pipeline for GitLab. |

## Design choices

- **Cycle-accurate scoreboard, not an end-of-test check.** A mismatch is reported on the clock it happens, with expected and actual. Cost: the model must mirror the pipeline registers, so a change to the RTL's timing changes the model too.
- **Mutation testing on top of coverage.** Coverage says what the stimulus touched; planted bugs say whether the checks would notice. The first full run caught 6 of 7. `BUG_SATNEG` survived because no test produced an output of exactly -32768 (the directed case landed on -32767). The boundary test was added and all 7 are caught. Cost: each bug is another compile and run.
- **cocotb and Icarus.** Python tests and an open-source simulator keep the flow runnable by anyone. Cost: it is not UVM and has no SystemVerilog assertions or formal proof.

## What is verified

- **Run here and in CI:** the clean design passes 9 tests on 20 random seeds; all 7 planted bugs are caught; coverage 100% of 21 bins; promtool tests pass; the Helm chart renders and runs as a Job on a kind cluster.
- **Not done:** no UVM, no SystemVerilog assertions, no formal verification, no gate-level or timing simulation, no real silicon. The block is small. The GitLab pipeline has not run on a GitLab runner. The site runs a JavaScript port of the filter, checked against the Python model (131 cycles, 0 mismatches); the Verilog itself runs only in the CI regression.

MIT licensed.

## Educational microprocessor and EDA flow demo

`microcpu/` contains a deliberately small, single-issue, in-order 8-bit CPU with ADD-immediate, XOR-immediate, NOP, and HALT instructions. It demonstrates RTL simulation and a self-checking testbench, not high-performance processor design or silicon implementation.

Run with Icarus Verilog:

```bash
make microcpu-demo
```

The demo checks reset, instruction behavior, and HALT state. It has no pipeline, cache, timing closure, synthesis results, or PPA measurements. The source uses standard Verilog constructs and can be explored in a Cadence simulator, but Cadence tools were not used to validate it; no Cadence scripts or tool-specific flow are included.
