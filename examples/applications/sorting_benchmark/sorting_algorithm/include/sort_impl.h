#include <vector>
#include "sort_interface.h"

// EVOLVE_START
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
// EVOLVE_END