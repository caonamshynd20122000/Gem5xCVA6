# Step 3: CVA6 Shared L2 Way-Shutdown RTL (SystemVerilog + Verilator)

This directory is reserved for Step 3 after selecting the optimal Way-Shutdown policy from Step 2 (`step2_gem5_model/`):

- `rtl/`: SystemVerilog RTL of the Way-Shutdown controller (16-set Sampled-Set ATD, Dirty-Way Flush FSM, `way_enable_mask[15:0]`) integrated into `cva6_shared_l2_16way.sv`.
- `tb/`: Verilator testbench verifying functional correctness (exact checksum match against Step 1 baseline).
- `scripts/`: Automation scripts for 3-way validation (Baseline RTL vs gem5 Model vs Custom Way-Shutdown RTL).
- `results/`: Final comparison CSV, Markdown report, and Pareto charts.
