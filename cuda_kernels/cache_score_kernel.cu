extern "C" __global__ void cache_score_kernel(
    const float* base_hits,
    const float* saved_tokens,
    float* out_scores,
    int count) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= count) {
    return;
  }
  float normalized_saved = saved_tokens[idx] / 8192.0f;
  out_scores[idx] = base_hits[idx] * (1.0f + normalized_saved);
}

