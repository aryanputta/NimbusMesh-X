extern "C" __global__ void topology_cost_kernel(
    const float* topology_affinity,
    const float* network_cost,
    float* out_penalty,
    int count) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= count) {
    return;
  }
  float penalty = network_cost[idx] - topology_affinity[idx];
  out_penalty[idx] = penalty > 0.0f ? penalty : 0.0f;
}

