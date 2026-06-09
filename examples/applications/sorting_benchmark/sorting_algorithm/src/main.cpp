/**
 * Main entry point for the sorting benchmark.
 * Reads input data, runs the sort algorithm, verifies correctness,
 * and outputs performance metrics.
 */

#include <iostream>
#include <fstream>
#include <vector>
#include <algorithm>
#include <chrono>
#include "sort_interface.h"

// The sort implementation will be inserted here by the evaluator
#include "sort_impl.h"

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <dataset_file>" << std::endl;
        return 1;
    }

    // Read input data
    std::ifstream file(argv[1]);
    if (!file.is_open()) {
        std::cerr << "Failed to open file: " << argv[1] << std::endl;
        return 1;
    }

    std::vector<int> data;
    int num;
    while (file >> num) {
        data.push_back(num);
    }
    file.close();

    if (data.empty()) {
        std::cerr << "No data read from file: " << argv[1] << std::endl;
        return 1;
    }

    // Create a copy for verification with standard sort
    std::vector<int> expected = data;
    std::sort(expected.begin(), expected.end());

    // Run sorting and measure time
    auto start = std::chrono::high_resolution_clock::now();
    SortResult result = sort(data);
    auto end = std::chrono::high_resolution_clock::now();

    auto duration_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

    // Verify correctness
    bool is_correct = (data == expected);

    // Output metrics in format expected by default parse_output
    std::cout << "execution_time_ms: " << duration_ms << std::endl;
    std::cout << "comparisons: " << result.comparisons << std::endl;
    std::cout << "swaps: " << result.swaps << std::endl;
    std::cout << "correct: " << (is_correct ? 1 : 0) << std::endl;

    return 0;
}
