# Runbook

## Regression failing
`results/summary.json` lists failing tests per seed. Re-run one seed: `make RANDOM_SEED=<n>`. The failing clock and expected versus actual values are in the assertion message. Decide first whether the RTL or the model is wrong; the spec is the comment at the top of `rtl/fir4.v`.

## Mutant survived
A planted bug passed every test, so the testbench cannot see that class of error. Find the stimulus that exposes it (print the cycle where the buggy and clean outputs first differ), add it as a directed test or a coverage bin, and re-run. Example: `BUG_SATNEG` needed an output of exactly -32768.

## Coverage below goal
`coverage.hits` in `summary.json` shows which bins are zero. Add a directed test or widen the random constraints; a bin that cannot be hit is a spec question, not a test to force.
