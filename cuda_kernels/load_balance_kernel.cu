extern "C" __global__ void load_balance_kernel(
    const float* queue_delay_ms,
    const float* congestion_score,
    const float* memory_headroom_gb,
    float* out_penalty,
    int count) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= count) {
    return;
  }
  float queue_component = queue_delay_ms[idx] / 1000.0f;
  float congestion_component = congestion_score[idx];
  float memory_component = 1.0f - (memory_headroom_gb[idx] / 64.0f);
  if (memory_component < 0.0f) {
    memory_component = 0.0f;
  }
  out_penalty[idx] = queue_component + congestion_component + memory_component;
}

