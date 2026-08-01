# Research Report 02: Hardware Memory Compression & PIM Prior Art Taxonomy

## Executive Summary
This document presents a comprehensive taxonomy and deep technical breakdown of existing hardware memory compression algorithms, Processing-in-Memory (PIM) designs, and memory expansion technologies. 

By analyzing the mechanics, latency budgets, compression ratios, and failure modes of prior art, we identify the exact architectural gaps that **Project Ouroboros** must exploit to achieve universal (gaming + local AI) scaling.

---

## 1. Hardware Memory Compression Algorithms Taxonomy

```
                              Hardware Memory Compression
                                           |
         +---------------------------------+---------------------------------+
         |                                                                   |
   Pattern-Based                                                       Delta-Based
 (Frequent Pattern Compression - FPC)                               (Base-Delta-Immediate - BDI)
  - Bit-mask pattern encoding                                        - Explores spatial locality in data values
  - 1-cycle latency                                                  - 1-2 cycle latency
  - Compression Ratio: 1.5x - 2.2x                                  - Compression Ratio: 1.8x - 3.2x
```

### A. Base-Delta-Immediate (BDI) (Pekhimenko et al., MICRO)
* **Core Principle**: Data values in a 64-byte cache line often share high-order bits (e.g. pointers in an array, 32-bit floats with small differences, integer arrays).
* **Mechanics**:
  1. Selects a **Base Value** (e.g., the first 32-bit integer in the line).
  2. Represents all subsequent numbers in the 64-byte line as small **Deltas** relative to the Base.
  3. If all deltas fit into 8-bit or 16-bit signed integers, the line is compressed from 64 bytes down to $B + N \times D$ bytes (e.g., $4 + 15 \times 1 = 19$ bytes).
* **Hardware Latency**: **1 to 2 clock cycles (~0.5 – 1.0 ns)**.
* **Compression Ratio**:
  * Integer Arrays / Pointers: **$2.0\times – 3.2\times$**.
  * Floating-Point Tensors (AI weights): **$1.4\times – 2.1\times$**.
* **Failure Mode**: High-entropy data or unaligned FP64 floats with random high bits.

### B. Frequent Pattern Compression (FPC) (Alameldeen & Wood, ISCA)
* **Core Principle**: Cache lines contain repeated common byte patterns (e.g., zero words, 4-bit sign-extended integers, byte-repeated values).
* **Mechanics**:
  1. Divides a 64-byte cache line into 16 32-bit words.
  2. Assigns a 3-bit prefix code to each word indicating its pattern (e.g., `000` = Zero word, `001` = 4-bit sign-extended int, `010` = 8-bit sign-extended int).
  3. Stores only the prefix codes and non-zero payload bits.
* **Hardware Latency**: **1 clock cycle (~0.4 – 0.8 ns)**.
* **Compression Ratio**: **$1.5\times – 2.2\times$** on general OS/Application memory.

---

## 2. Commercial Hardware Implementations

### A. IBM Memory eXpansion Technology (MXT)
* **Architecture**: Integrated hardware compression engine inside the IBM eServer memory controller chip.
* **Cache Line / Sector**: 128-byte uncompressed line compressed down to 32-byte sectors using a parallel LZ77 variant.
* **Sector Translation Table (STT)**: A dedicated region of DRAM used as a translation layer mapping logical cache lines to variable 32B physical sectors.
* **Lessons Learned**: STT lookup added a ~15% latency overhead, but doubled physical server RAM capacity.

### B. Apple Silicon Unified Memory Subsystem (M1 – M4)
* **Architecture**: Dedicated hardware compression/decompression blocks built into the Apple SOC memory fabric.
* **Operation**: Real-time compression of macOS/iOS RAM pages. Allows iPhones and Macs to run heavy applications and local Apple Intelligence models in memory footprints that would crash competitor devices with equivalent physical RAM.

---

## 3. Processing-in-Memory (PIM) Prior Art Taxonomy

| Architecture | Fabrication Location | Execution Units | Primary Workload | Limitation |
| :--- | :--- | :--- | :--- | :--- |
| **Samsung Aquabolt-XL (HBM-PIM)** | Inside DRAM Banks | 16-wide SIMD FP16 units (Bank-level) | AI Matrix Multiplication / Reductions | Fixed FP16 logic; cannot handle compression or complex OS tasks. |
| **SK Hynix AiM (Accelerator-in-Memory)** | Near DRAM Bank Array | FP16 / INT8 Vector MACs | LLM Inference Acceleration | Requires custom API; non-standard DRAM interface. |
| **UPMEM DPU** | Standard DDR4 DRAM Die | 32-bit RISC cores @ 400MHz inside DRAM | Graph Processing & Database Search | Low clock frequency; complex programming model. |
| **CXL 3.1 Memory Pooling** | PCIe Gen 5/6 Bus Controller | Cache-Coherent Memory Expander | Cloud Datacenter RAM Sharing | Sub-200ns PCIe latency boundary. |

---

## 4. Architectural Gaps & Ouroboros Opportunity

| Existing Prior Art | Identified Limitation | Project Ouroboros Innovation |
| :--- | :--- | :--- |
| **BDI / FPC** | Fixed single-algorithm engines plateau at ~$2\times$ compression ratio. | **3-Tier Adaptive Hierarchy**: Sub-ns BDI for hot data + ASIC LZ4 for warm pages + Page Deduplication for cold memory. |
| **Samsung/SK Hynix PIM** | Only perform FP16 math; ignore memory compression & indirection. | **Combined PIM + Compression Engine**: PIM operates directly on compressed data structures to maximize effective memory bandwidth. |
| **IBM MXT** | High STT lookup latency in 2001. | **Fast On-Chip Hardware Indirection Cache (HIT)** embedded in the memory controller with zero DRAM lookup penalties. |
