"""
Ouroboros Simulator Benchmark Runner.

Executes `ouroboros-sim` against realistic memory traces (OS Pointers, LLM KV-Caches,
Game Geometry Buffers, and Encrypted Streams), verifies 100% losslessness, and generates
an empirical Markdown performance report.
"""

from __future__ import annotations

import time
from typing import Dict, Any

from simulator.benchmarks.dataset_generator import WorkloadGenerator
from simulator.core.memory_controller import OuroborosMemoryController


def run_workload_benchmark(name: str, lines: list[bytes]) -> Dict[str, Any]:
    controller = OuroborosMemoryController(dram_capacity_bytes=256 * 1024 * 1024)
    start_time = time.perf_counter()

    # 1. Write phase
    for i, line in enumerate(lines):
        controller.write_line(virtual_address=i * 64, data=line)

    write_duration = time.perf_counter() - start_time

    # 2. Read back & Losslessness verification phase
    start_read = time.perf_counter()
    mismatches = 0
    for i, original_line in enumerate(lines):
        read_line = controller.read_line(virtual_address=i * 64)
        if read_line != original_line:
            mismatches += 1

    read_duration = time.perf_counter() - start_read

    stats = controller.stats
    virtual_mb = stats.virtual_bytes_written / (1024 * 1024)
    physical_mb = stats.physical_bytes_allocated / (1024 * 1024)
    multiplier = stats.effective_compression_ratio
    direct_embed_pct = (stats.direct_embedded_writes / stats.total_writes) * 100.0
    bypass_pct = (stats.bypassed_writes / stats.total_writes) * 100.0
    energy_joules = (stats.energy_saved_pj) / 1e12  # convert pJ to Joules

    return {
        "name": name,
        "total_lines": stats.total_writes,
        "virtual_mb": virtual_mb,
        "physical_mb": physical_mb,
        "capacity_multiplier": multiplier,
        "saved_capacity_pct": stats.capacity_saved_percent,
        "direct_embed_pct": direct_embed_pct,
        "bypass_pct": bypass_pct,
        "energy_saved_joules": energy_joules,
        "mismatches": mismatches,
        "write_throughput_mb_s": virtual_mb / write_duration if write_duration > 0 else 0,
    }


def run_benchmarks(count_per_workload: int = 2000) -> str:
    workloads = WorkloadGenerator.get_all_workloads(count_per_workload)
    results = []

    for name, trace in workloads.items():
        res = run_workload_benchmark(name, trace)
        results.append(res)

    # Build ASCII Markdown Benchmark Report
    report = []
    report.append("=========================================================================================")
    report.append("                      PROJECT OUROBOROS SIMULATOR BENCHMARK REPORT                       ")
    report.append("=========================================================================================")
    report.append("")
    report.append(f"Workload Trace Size: {count_per_workload} lines per category ({count_per_workload * 64 / 1024:.1f} KB virtual memory each)")
    report.append("")
    report.append("| Workload Category | Virtual MB | Physical MB | Effective Multiplier | Direct Embed % | Bypass % | Lossless? |")
    report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    total_virt = 0.0
    total_phys = 0.0
    total_energy_j = 0.0

    for r in results:
        total_virt += r["virtual_mb"]
        total_phys += r["physical_mb"]
        total_energy_j += r["energy_saved_joules"]
        lossless_str = "YES (0 errors)" if r["mismatches"] == 0 else f"FAIL ({r['mismatches']} errors)"
        report.append(
            f"| {r['name']:<32} | {r['virtual_mb']:>8.3f} | {r['physical_mb']:>9.3f} | "
            f"**{r['capacity_multiplier']:>5.2f}x** | {r['direct_embed_pct']:>12.1f}% | "
            f"{r['bypass_pct']:>6.1f}% | {lossless_str} |"
        )

    overall_multiplier = total_virt / total_phys if total_phys > 0 else 1.0
    overall_saved_pct = ((total_virt - total_phys) / total_virt) * 100.0 if total_virt > 0 else 0.0

    report.append("")
    report.append("-----------------------------------------------------------------------------------------")
    report.append(f"OVERALL SUMMARY ACROSS ALL WORKLOADS:")
    report.append(f"  * Total Virtual Memory Processed:  {total_virt:.3f} MB")
    report.append(f"  * Total Physical DRAM Allocated:  {total_phys:.3f} MB")
    report.append(f"  * Overall Capacity Multiplier:      {overall_multiplier:.2f}x (Saved {overall_saved_pct:.1f}% physical DRAM)")
    report.append(f"  * Estimated Bus Energy Saved:      {total_energy_j * 1000:.3f} mJ")
    report.append("-----------------------------------------------------------------------------------------")

    full_report = "\n".join(report)
    return full_report


if __name__ == '__main__':
    report_text = run_benchmarks(count_per_workload=5000)
    print(report_text)
