SIM ?= icarus
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(PWD)/rtl/fir4.v
TOPLEVEL = fir4
MODULE = test_fir4
export PYTHONPATH := $(PWD)/dv:$(PYTHONPATH)
export COCOTB_REDUCED_LOG_FMT = 1
include $(shell cocotb-config --makefiles)/Makefile.sim
