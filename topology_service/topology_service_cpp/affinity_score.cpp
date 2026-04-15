#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

// Minimal C++ scoring helper for future acceleration work. The input file is a
// CSV adjacency matrix of positive link costs. The output is a normalized
// affinity matrix where lower route cost yields higher affinity.

static std::vector<std::vector<double>> read_csv(const std::string& path) {
  std::ifstream file(path);
  std::vector<std::vector<double>> matrix;
  std::string line;
  while (std::getline(file, line)) {
    std::stringstream ss(line);
    std::string item;
    std::vector<double> row;
    while (std::getline(ss, item, ',')) {
      row.push_back(std::stod(item));
    }
    if (!row.empty()) {
      matrix.push_back(row);
    }
  }
  return matrix;
}

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "usage: affinity_score <adjacency.csv>\n";
    return 1;
  }
  auto matrix = read_csv(argv[1]);
  if (matrix.empty()) {
    std::cerr << "empty matrix\n";
    return 1;
  }
  double max_cost = 0.0;
  for (const auto& row : matrix) {
    for (double value : row) {
      max_cost = std::max(max_cost, value);
    }
  }
  for (const auto& row : matrix) {
    for (size_t index = 0; index < row.size(); ++index) {
      double affinity = 1.0 - (row[index] / std::max(max_cost, 1.0));
      std::cout << std::fixed << std::setprecision(4) << affinity;
      if (index + 1 < row.size()) {
        std::cout << ",";
      }
    }
    std::cout << "\n";
  }
  return 0;
}

