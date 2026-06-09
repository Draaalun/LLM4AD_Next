#ifndef SORT_INTERFACE_H
#define SORT_INTERFACE_H

#include <vector>

/**
 * Result structure returned by the sort function.
 * Contains performance metrics (number of comparisons and swaps).
 */
struct SortResult {
    int comparisons;
    int swaps;
};

/**
 * Sort function interface that generated algorithms must implement.
 *
 * @param data Vector of integers to be sorted in-place.
 * @return SortResult containing performance metrics.
 */
SortResult sort(std::vector<int>& data);

#endif // SORT_INTERFACE_H
