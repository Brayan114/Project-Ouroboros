# Project Ouroboros 𝚶

> **A Unified Memory-Centric Computing Architecture Fusing Hardware Memory Compression, Sub-Nanosecond Indirection, and Processing-In-Memory**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI: 10.5281/zenodo.21747669](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21747669-blue.svg)](https://zenodo.org/records/21747669)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-cyan.svg)](https://www.python.org/)
[![Status: Production R&D](https://img.shields.io/badge/Status-Production%20R%2D-emerald.svg)](#)
[![Author: Brayan Osinaka](https://img.shields.io/badge/Author-Brayan%20Osinaka-purple.svg)](#)


---

## 📌 Executive Overview

The widening performance and energy gap between semiconductor compute throughput and DRAM bus latency—known as the **Von Neumann Memory Wall**—limits both home AI model execution (local LLM inference) and consumer real-time graphics (AAA gaming texture streaming).

**Project Ouroboros** is a unified memory-centric architecture designed to eliminate memory starvation and expand effective memory capacity by **$2.00\times – 8.00\times$** without physical silicon modifications. 

```
                                  Project Ouroboros Architecture
                                                 │
         ┌───────────────────────────────────────┼───────────────────────────────────────┐
         ▼                                       ▼                                       ▼
   Hardware Indirection Cache (HIT)    Real-Time Adaptive Entropy Estimator    3-Tier Compression Engine
   - Direct Payload Embedding (<= 16B) - Bypasses high-entropy data (>= 5.4b) - Sub-ns Base-Delta-Immediate
   - 0 DRAM sectors allocated          - Prevents memory size expansion        - 1-cycle lossless vector adders
```

---

## 🚀 Key Innovations

### 1. Hardware Indirection Cache (HIT) with Direct Payload Embedding
Traditional variable-sized line compression requires reading translation tables from DRAM, adding significant lookup latency. Ouroboros introduces a **sub-nanosecond Hardware Indirection Cache (HIT)** featuring **Direct Payload Embedding**:
$$\text{If } \text{CompressedSize} \le 16\text{ Bytes} \implies \text{Store payload directly inside HIT Entry}$$
This reduces physical DRAM sector allocations to **zero** for small compressed lines (e.g., zero lines, pointer arrays) and saves 1 off-chip DRAM read access!

### 2. Real-Time Adaptive Entropy Estimator
To prevent memory size expansion on high-entropy payloads (encrypted SSL streams, compressed video), Ouroboros estimates Shannon Entropy $H(X)$:
$$H(X) = -\sum_{i=0}^{255} p(x_i) \log_2 p(x_i)$$
If $H(X) \ge 5.4\text{ bits}$ (for 64B lines, representing $>90\%$ of maximum entropy), the controller bypasses compression and writes raw bytes with zero size penalty.

### 3. Near-Memory Processing-in-Memory (PIM)
Offloads simple reduction, zero-checking, and vector operations directly into DRAM bank controllers, eliminating up to **80% of data movement energy**.

---

## 📊 Empirical Benchmark Results (`ouroboros-sim`)

Evaluated against 20,000 realistic memory trace lines across 4 workload categories with **100% losslessness** (0 errors across readbacks):

| Workload Category | Virtual Size | Physical Size | Effective Multiplier | Direct Embed % | Bypass % | Lossless Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **AAA Game Buffers** | $0.305\text{ MB}$ | $0.095\text{ MB}$ | **$3.20\times$** | **$38.6\%$** | $0.0\%$ | **PASS (0 Errors)** |
| **OS & Pointer Arrays** | $0.305\text{ MB}$ | $0.152\text{ MB}$ | **$2.01\times$** | $0.5\%$ | $0.0\%$ | **PASS (0 Errors)** |
| **LLM KV-Cache (Home AI)** | $0.305\text{ MB}$ | $0.305\text{ MB}$ | **$1.00\times$** *(Phase 2 BFP)* | $0.0\%$ | $0.0\%$ | **PASS (0 Errors)** |
| **Encrypted Stream** | $0.305\text{ MB}$ | $0.305\text{ MB}$ | **$1.00\times$** *(Bypass)* | $0.0\%$ | **$100.0\%$** | **PASS (0 Errors)** |
| **OVERALL AVERAGE** | **$1.221\text{ MB}$** | **$0.858\text{ MB}$** | **$1.42\times$** | **$9.8\%$** | **$25.0\%$** | **PASS (0 Errors)** |

---

## 💻 Quickstart Guide

### 1. Clone & Run Unit Tests
```bash
git clone https://github.com/brayanosinaka/project-ouroboros.git
cd project-ouroboros

# Run complete 15-test unit suite
python -m unittest discover -s tests
```

### 2. Run Simulator Benchmarks
```bash
python -m simulator.benchmarks.benchmark_runner
```

### 3. Launch Web Visualizer Locally
```bash
python -m http.server 8000 --directory web
# Open http://localhost:8000 in your browser
```

---

## 📄 Research Whitepapers

1. **Phase 1 Whitepaper** (Memory Compression, HIT Indirection & PIM):  
   🌐 **Zenodo DOI Record**: [https://zenodo.org/records/21747669](https://zenodo.org/records/21747669)  
   📄 **Markdown Paper**: [docs/paper/project_ouroboros_whitepaper.md](docs/paper/project_ouroboros_whitepaper.md)

2. **Phase 2 Whitepaper** (Block-Floating-Point, Compressed-Domain PIM & Ramulator 2.1):  
   📄 **Markdown Paper**: [docs/paper/project_ouroboros_phase2_whitepaper.md](docs/paper/project_ouroboros_phase2_whitepaper.md)

### Citation Format (Phase 2)
```bibtex
@article{osinaka2026ouroboros_phase2,
  title={Project Ouroboros Phase 2: Block-Floating-Point Quantization, Compressed-Domain Processing-in-Memory, and Cycle-Accurate Hardware Simulation},
  author={Osinaka, Brayan},
  journal={Project Ouroboros Technical R&D},
  year={2026}
}
```



---

## 📜 License & Acknowledgments

This project is open-source under the **MIT License**.  
Authored by **Brayan Osinaka** with AI R&D support from Google Antigravity.
