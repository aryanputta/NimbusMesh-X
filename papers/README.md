# Papers and Industry Context

## Ecosystem Context

- Microsoft and NVIDIA GTC announcements around Azure AI infrastructure, Foundry, and inference-first AI factories
- NVIDIA Run:ai on Azure
- Microsoft Maia 200 inference accelerator direction

## Systems Papers to Anchor the Project

- SortingHat: topology-aware scheduling for multi-GPU inference
- Online Scheduling for LLM Inference with KV Cache Constraints
- Characterizing and Optimizing KVCache at Large-Scale Model Serving Systems
- HarMoEny: efficient multi-GPU inference for MoE models
- vLLM technical material
- TensorRT-LLM and Triton technical material
- GPU communication and interconnect surveys

## Takeaways To Apply

- topology quality changes latency and throughput materially
- KV cache is a first-class scheduling signal, not a runtime afterthought
- long-context and agentic workloads amplify cache and memory pressure
- heterogeneous inference economics matter
- communication bottlenecks can dominate compute bottlenecks

The repository is structured so these ideas map to code, not just literature review bullets.

