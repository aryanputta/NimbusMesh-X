#include <cmath>
#include <limits>

extern "C" int choose_candidate(
    const double* estimated_latency,
    const double* queue_delay,
    const double* cache_hit,
    const double* topology_affinity,
    const double* network_cost,
    const double* accel_cost,
    const double* fairness_penalty,
    const int* available,
    int count,
    int sla_priority) {
  if (count <= 0) {
    return -1;
  }
  const double latency_weight = (sla_priority == 3) ? 1.5 : ((sla_priority == 2) ? 1.1 : 0.8);
  const double cost_weight = (sla_priority == 3) ? 0.2 : 0.6;
  int best_index = -1;
  double best_score = std::numeric_limits<double>::infinity();
  for (int i = 0; i < count; ++i) {
    if (available[i] == 0) {
      continue;
    }
    const double score = (estimated_latency[i] * latency_weight) + (queue_delay[i] * 0.1) +
                         (network_cost[i] * 18.0) + (accel_cost[i] * cost_weight) +
                         (fairness_penalty[i] * 120.0) - (cache_hit[i] * 450.0) -
                         (topology_affinity[i] * 90.0);
    if (score < best_score) {
      best_score = score;
      best_index = i;
    }
  }
  if (best_index >= 0) {
    return best_index;
  }
  // Fallback: if all candidates were marked unavailable, return least estimated latency.
  best_index = 0;
  best_score = estimated_latency[0];
  for (int i = 1; i < count; ++i) {
    if (estimated_latency[i] < best_score) {
      best_score = estimated_latency[i];
      best_index = i;
    }
  }
  return best_index;
}

