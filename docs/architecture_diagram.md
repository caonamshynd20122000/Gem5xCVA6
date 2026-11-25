# 4-Core CVA6 Cluster & Shared L2 Cache Way-Shutdown Architecture — Gem5 x CVA6

- High-resolution PNG diagram: [cva6_gem5_architecture.png](cva6_gem5_architecture.png)
- Vector SVG diagram: [cva6_gem5_architecture.svg](cva6_gem5_architecture.svg)

## Mermaid System Diagram (4x CVA6 Core Tiles + Shared L2 Cache Way-Shutdown)

```mermaid
flowchart TB
    subgraph CLUSTER["4-Core CVA6 Multicore Cluster (4x RV64GC Core Tiles)"]
        direction LR
        subgraph T0["CVA6 Core Tile 0"]
            C0["CVA6 Core 0 (6-stage In-Order)"]
            I0["L1 I$ (16KB, 4w)"]
            D0["L1 D$ (32KB, 8w, WT+Inval)"]
            C0 --> I0 & D0
        end
        subgraph T1["CVA6 Core Tile 1"]
            C1["CVA6 Core 1 (6-stage In-Order)"]
            I1["L1 I$ (16KB, 4w)"]
            D1["L1 D$ (32KB, 8w, WT+Inval)"]
            C1 --> I1 & D1
        end
        subgraph T2["CVA6 Core Tile 2"]
            C2["CVA6 Core 2 (6-stage In-Order)"]
            I2["L1 I$ (16KB, 4w)"]
            D2["L1 D$ (32KB, 8w, WT+Inval)"]
            C2 --> I2 & D2
        end
        subgraph T3["CVA6 Core Tile 3"]
            C3["CVA6 Core 3 (6-stage In-Order)"]
            I3["L1 I$ (16KB, 4w)"]
            D3["L1 D$ (32KB, 8w, WT+Inval)"]
            C3 --> I3 & D3
        end
    end

    L2XBAR["L1-to-L2 Coherent Interconnect (4-Port Coherent Crossbar — L2XBar)<br/>Aggregates L1I/L1D Misses + L1D Write-Through Stream & Broadcasts L2 -> L1 Invalidations"]

    subgraph L2["TARGET: SHARED L2 CACHE (512 KiB, 16-Way, Write-Back) + WAY-SHUTDOWN"]
        L2CTRL["L2 Bank Controller & Coherence Directory<br/>(Tracks core_id 0..3, Tag/Set Lookup, L1 Inval)"]
        L2VSEL["L2 Replacement & Victim Selector<br/>(TreePLRU / LRU — masked by way_en)"]
        L2WCTRL["L2 Way-Shutdown Controller (NEW)<br/>• Epoch & Hysteresis FSM<br/>• Sampled-Set ATD (16/512 sets) + Per-Way Utility<br/>• Dirty-Way Flush FSM & Wakeup Timer (T_wakeup)<br/>Out: way_en[15:0], way_sd[15:0]"]
        L2SRAM["Shared L2 Tag + Data SRAM Banks (16 Independent Ways)<br/>Active Ways (ON) | Shutdown Ways (Power-Gated)"]
        L2MSHR["L2 MSHR & Fill Handler<br/>(16 MSHRs -> DRAM Read)"]
        L2WB["L2 Writeback & Way-Flush Buffer<br/>(Evicts dirty lines on replacement or Way-Shutdown 1->0)"]

        L2CTRL <--> L2SRAM
        L2CTRL --> L2VSEL
        L2WCTRL -- "way_en mask" --> L2VSEL
        L2WCTRL -- "cs gate + sd power-gate + dirty flush" --> L2SRAM
        L2SRAM --> L2MSHR
        L2SRAM --> L2WB
    end

    SYSXBAR["SoC System Interconnect: axi_xbar_intf (AXI4 Memory Bus — SystemXBar)"]
    DRAM["Off-Chip Main Memory / DRAM (DDR3/DDR4)"]
    PERIPH["SoC Peripherals via axi2apb (UART, Timer, PLIC, 4-Hart CLINT)"]

    T0 & T1 & T2 & T3 <--> L2XBAR
    L2XBAR <--> L2CTRL
    L2MSHR & L2WB <--> SYSXBAR
    SYSXBAR <--> DRAM & PERIPH
```
