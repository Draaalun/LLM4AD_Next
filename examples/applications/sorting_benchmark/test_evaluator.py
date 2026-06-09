#!/usr/bin/env python3
"""Test script to verify the SortingEvaluator works correctly."""

import asyncio

from llm4ad.config.schema import EvalContext
from sorting_benchmark.sorting_evaluator import SortingEvaluator

# Test implementation: Bubble Sort
BUBBLE_SORT_CODE = """#include <vector>
#include "sort_interface.h"

SortResult sort(std::vector<int>& data) {
    SortResult result = {0, 0};
    int n = data.size();
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            result.comparisons++;
            if (data[j] > data[j + 1]) {
                std::swap(data[j], data[j + 1]);
                result.swaps++;
            }
        }
    }
    return result;
}
"""


async def test_evaluator():
    """Test the SortingEvaluator with a known good implementation."""
    print("Testing SortingEvaluator with bubble sort...")


    evaluator = SortingEvaluator()
    cfg = EvalContext(data_path="/Users/zhufangzhou/Workspace/OpenSource/LLM4AD/examples/applications/sorting_benchmark/data/small/1000.txt", project_root="/Users/zhufangzhou/Workspace/OpenSource/LLM4AD/examples/applications/sorting_benchmark/sorting_algorithm")
    result = await evaluator.evaluate(cfg=cfg)

    print("\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Score: {result.score}")
    print(f"  Duration: {result.duration_ms:.2f}ms")
    if result.metrics:
        print("  Metrics:")
        for name, value in result.metrics.items():
            print(f"    {name}: {value}")

    if result.success and result.metrics.get("correct", 0) == 1.0:
        print("\n✓ Test PASSED! The evaluator is working correctly.")
        return True
    else:
        print(f"\n✗ Test FAILED! Error: {result.error_message}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_evaluator())
    exit(0 if success else 1)
