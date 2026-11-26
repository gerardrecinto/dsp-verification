SIM ?= icarus
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(PWD)/rtl/fir4.v
TOPLEVEL = fir4
MODULE = test_fir4
export PYTHONPATH := $(PWD)/dv:$(PYTHONPATH)
export COCOTB_REDUCED_LOG_FMT = 1
ifneq ($(MAKECMDGOALS),microcpu-demo)
include $(shell cocotb-config --makefiles)/Makefile.sim
endif

.PHONY: microcpu-demo
microcpu-demo:
	iverilog -g2012 -Wall -s tb_microcpu -o /tmp/dsp-microcpu microcpu/rtl/microcpu.v microcpu/tb/tb_microcpu.v
	vvp /tmp/dsp-microcpu
