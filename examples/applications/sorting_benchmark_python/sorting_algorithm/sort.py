#!/usr/bin/env python3
"""Simple sorting algorithm with EVOLVE markers for LLM4AD optimization.

This is the baseline Bubble Sort implementation that will be evolved
by the LLM4AD system to improve performance.
"""

import json
import sys


# EVOLVE_START
def _insertion_sort(data, left, right):
    """Insertion sort for small subarrays - low constant overhead.

    Args:
        data: List of integers to sort in-place
        left: Starting index of subarray
        right: Ending index of subarray (inclusive)

    Returns:
        tuple: (comparisons, swaps) - Count of operations performed
    """
    comparisons = 0
    swaps = 0

    for i in range(left + 1, right + 1):
        key = data[i]
        j = i - 1

        # Move elements that are greater than key one position ahead
        while j >= left:
            comparisons += 1
            if data[j] <= key:
                break
            data[j + 1] = data[j]
            swaps += 1
            j -= 1

        data[j + 1] = key

    return comparisons, swaps


def _merge(data, left, mid, right, temp):
    """Merge two sorted subarrays into a single sorted subarray.

    Args:
        data: List containing the subarrays to merge
        left: Starting index of first subarray
        mid: Ending index of first subarray (mid+1 starts second)
        right: Ending index of second subarray
        temp: Temporary buffer for merging (reused across calls)

    Returns:
        tuple: (comparisons, swaps) - Count of operations performed
    """
    comparisons = 0
    swaps = 0

    i = left      # Index for left subarray
    j = mid + 1   # Index for right subarray
    k = left      # Index for temp array

    # Merge the two subarrays into temp
    while i <= mid and j <= right:
        comparisons += 1
        if data[i] <= data[j]:
            temp[k] = data[i]
            i += 1
        else:
            temp[k] = data[j]
            j += 1
        k += 1
        swaps += 1

    # Copy remaining elements from left subarray
    while i <= mid:
        temp[k] = data[i]
        i += 1
        k += 1
        swaps += 1

    # Copy remaining elements from right subarray
    while j <= right:
        temp[k] = data[j]
        j += 1
        k += 1
        swaps += 1

    # Copy merged result back to original array
    for k in range(left, right + 1):
        data[k] = temp[k]

    return comparisons, swaps


def _merge_sort_helper(data, left, right, temp, insertion_threshold=32):
    """Recursive merge sort with insertion sort for small subarrays.

    Args:
        data: List of integers to sort in-place
        left: Starting index of subarray to sort
        right: Ending index of subarray to sort (inclusive)
        temp: Temporary buffer for merging (reused across calls)
        insertion_threshold: Size below which insertion sort is used

    Returns:
        tuple: (comparisons, swaps) - Count of operations performed
    """
    # Base case: empty or single element
    if left >= right:
        return 0, 0

    total_comparisons = 0
    total_swaps = 0

    # Use insertion sort for small subarrays
    if right - left + 1 <= insertion_threshold:
        return _insertion_sort(data, left, right)

    # Divide: find the middle point
    mid = left + (right - left) // 2

    # Conquer: recursively sort both halves
    comp_left, swaps_left = _merge_sort_helper(data, left, mid, temp, insertion_threshold)
    comp_right, swaps_right = _merge_sort_helper(data, mid + 1, right, temp, insertion_threshold)

    # Combine: merge the sorted halves
    comp_merge, swaps_merge = _merge(data, left, mid, right, temp)

    total_comparisons = comp_left + comp_right + comp_merge
    total_swaps = swaps_left + swaps_right + swaps_merge

    return total_comparisons, total_swaps


def hybrid_merge_insertion_sort(data):
    """Hybrid Merge Sort + Insertion Sort algorithm - O(n log n) complexity.

    This adaptive sorting algorithm uses merge sort's divide-and-conquer
    strategy for large inputs while switching to insertion sort for small
    subarrays where its low constant overhead is faster in practice.

    Args:
        data: List of integers to sort in-place

    Returns:
        tuple: (comparisons, swaps) - Count of operations performed
    """
    n = len(data)

    # Trivial cases: empty or single element
    if n <= 1:
        return 0, 0

    # Allocate temporary buffer once and reuse across all merges
    temp = [0] * n

    # Perform the hybrid sort
    return _merge_sort_helper(data, 0, n - 1, temp)
# EVOLVE_END


def sort(data):
    """Main sorting function that delegates to the evolved algorithm.

    Args:
        data: List of integers to sort

    Returns:
        SortResult: Dictionary with sorted data and metrics
    """
    # Make a copy to avoid modifying original
    data = list(data)

    # Call the hybrid merge insertion sort algorithm
    comparisons, swaps = hybrid_merge_insertion_sort(data)

    return {
        "result": data,
        "comparisons": comparisons,
        "swaps": swaps,
    }


def main():
    """Main entry point for the sorting algorithm."""
    if len(sys.argv) < 2:
        print("Usage: python sort.py '<input_json>'")
        sys.exit(1)

    # Parse input
    input_json = sys.argv[1]
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input")
        sys.exit(1)

    # Sort the data
    result = sort(input_data)

    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()
