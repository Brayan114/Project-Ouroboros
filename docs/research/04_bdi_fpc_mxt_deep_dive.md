# Research Report 04: Hardware Compression Mechanics & PIM Deep Dive (BDI, FPC, MXT, HBM-PIM, AiM)

## Executive Summary
This report incorporates deep technical research into the mathematical mechanics, gate-level latencies, indirection table overheads, and hardware control signals of five foundational prior art systems: **Base-Delta-Immediate (BDI)**, **Frequent Pattern Compression (FPC)**, **IBM Memory eXpansion Technology (MXT)**, **Samsung Aquabolt-XL HBM-PIM**, and **SK Hynix AiM**.

These insights directly inform the design of **Project Ouroboros**'s Hardware Indirection Cache (HIT) and Compressed PIM Execution Engine.

---

## 1. Base-Delta-Immediate (BDI) Algorithm Deep-Dive

**Reference**: Pekhimenko et al. (*MICRO 2012*)

### Mathematical Formulation & Vector Patterns
BDI exploits **low dynamic range** across 64-byte cache lines. A 64-byte block partitioned into $k$ words $V_0, V_1, \dots, V_{k-1}$ is represented as:
$$V_i = B_0 + \Delta_i$$

BDI evaluates **8 candidate encoding states** in parallel:

| Encoding State | Base Size ($S_{\text{elem}}$) | Delta Size ($S_{\text{delta}}$) | Payload Size (64B Cache Line) | Compression Ratio |
| :--- | :--- | :--- | :--- | :--- |
| **Zero (Zer)** | N/A | 0 Bytes | 0 Bytes (+ 1B Metadata) | **64.00×** |
| **Repeated (Rep)** | 8 Bytes | 0 Bytes | 8 Bytes | **8.00×** |
| **B8D1** | 8 Bytes | 1 Byte | $8\text{B} + (8 \times 1\text{B}) = 16\text{ Bytes}$ | **4.00×** |
| **B8D2** | 8 Bytes | 2 Bytes | $8\text{B} + (8 \times 2\text{B}) = 24\text{ Bytes}$ | **2.67×** |
| **B8D4** | 8 Bytes | 4 Bytes | $8\text{B} + (8 \times 4\text{B}) = 40\text{ Bytes}$ | **1.60×** |
| **B4D1** | 4 Bytes | 1 Byte | $4\text{B} + (16 \times 1\text{B}) = 20\text{ Bytes}$ | **3.20×** |
| **B4D2** | 4 Bytes | 2 Bytes | $4\text{B} + (16 \times 2\text{B}) = 36\text{ Bytes}$ | **1.78×** |
| **Uncompressed** | N/A | N/A | 64 Bytes | **1.00×** |

### Latency Budget & Gate Mechanics
* **Decompression Latency**: **1 Clock Cycle (~0.5 ns)**.
  Decompression runs off the critical cache hit path using an array of parallel 8/16-bit vector adders:
  $$V_i = B_0 + \text{SignExtend}(\Delta_i)$$
* **Compression Latency**: **2 to 3 Clock Cycles**.
  Calculates $V_i - B_0$ across 7 parallel logic paths; a priority encoder selects the smallest valid payload.
* **IEEE-754 Float Failure Mode**: IEEE-754 floats vary non-linearly in exponent and mantissa fields, causing BDI compression ratio to drop to $\sim 1.00\times - 1.15\times$. Ouroboros solves this via Block-Floating-Point (BFP) quantization for FP tensors.

---

## 2. Frequent Pattern Compression (FPC) Deep-Dive

**Reference**: Alameldeen & Wood (*ISCA 2004*)

### Bit-Level Encodings & Pipeline Latency
FPC operates on 32-bit words using 3-bit prefix codes:

| Prefix | Pattern Description | Encoded Representation | Payload Size |
| :---: | :--- | :--- | :---: |
| `000` | Zero Word | `000` | **3 bits** |
| `001` | 4-bit Sign-Extended Int | `001` + `data[3:0]` | **7 bits** |
| `010` | 8-bit Sign-Extended Int | `010` + `data[7:0]` | **11 bits** |
| `011` | 16-bit Sign-Extended Int | `011` + `data[15:0]` | **19 bits** |
| `110` | Repeated Bytes (`0xAA_AA_AA_AA`) | `110` + `data[7:0]` | **11 bits** |
| `111` | Uncompressed Word | `111` + `data[31:0]` | **35 bits** |

* **Decompression Latency**: **5 Clock Cycles** (variable-length decoding requires a prefix sum scan + multi-stage funnel-shifter array to realign un-aligned 32-bit word boundaries).
* **Expansion Mitigation**: High-entropy data generates `111` prefixes across all 16 words, expanding a 64B line to 70B (+9.375%). FPC uses a 512-bit in-flight size checker to abort compression and flag the line as raw.

---

## 3. IBM MXT: Direct STT Entry Payload Embedding

**Reference**: Franaszek et al. (*IBM J. Res. & Dev. 2001*)

* **Sector Translation Table (STT)**: Maps 1KB logical blocks to variable 256-byte physical DRAM sectors.
* **Direct Embedded Payload Innovation**:
  If a 1KB block compresses down to $\le 120$ bits (15 bytes), **the compressed payload is embedded directly inside the 16-byte STT entry itself**!
  * **Benefit**: Eliminates physical sector allocation entirely and saves 1 DRAM read access.
  * **Application to Ouroboros**: Ouroboros's Hardware Indirection Cache (HIT) adopts direct entry embedding for sub-16B compressed lines.

---

## 4. Commercial PIM Architectures: Samsung HBM-PIM vs. SK Hynix AiM

| Technical Metric | Samsung Aquabolt-XL (HBM2-PIM) | SK Hynix AiM (GDDR6-AiM) |
| :--- | :--- | :--- |
| **PIM Location** | Bank-Pair (Shared Even/Odd Banks) | Bank Level (1 PU per DRAM Bank) |
| **Execution Units** | 16-lane SIMD FP16 ALU | 16-lane FP16/BF16 MAC Array |
| **Activation Support** | Software Offload (Host CPU/GPU) | On-chip Hardware LUT (GELU, Sigmoid, ReLU) |
| **Control Model** | Standard JEDEC `READ`/`WRITE` Intercept | Extended C/A Command Set (`WR_ABK`, `RD_MAC`) |

### Control Signal Insights for Ouroboros
* **Samsung JEDEC Intercept**: Proves PIM mode can be triggered via standard `MRS` commands and column reads without changing motherboard memory controller physical pins.
* **SK Hynix All-Bank Parallelism**: Demonstrates that broadcasting input vectors across all 16 DRAM banks simultaneously maximizes internal DRAM array bandwidth ($>1\text{ TFLOPS}$ per die).
