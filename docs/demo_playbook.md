# Demo Playbook

## Goal

Show that NimbusMesh-X is a control plane for AI inference factories, not a toy load balancer.

## Demo Flow

1. Run the benchmark suite on `configs/multi_cluster_long_context.json`.
2. Open the decision log JSONL and show routing changes over time.
3. Re-run with `configs/failure_congestion.json`.
4. Compare `least_queue` against `multi_objective` and `contextual_bandit`.
5. Call out:
   - cluster chosen
   - accelerator pool chosen
   - estimated latency
   - cache hit ratio
   - why the decision changed when congestion or failure windows appeared

## Commands

```bash
python scripts/run_simulation.py --config configs/multi_cluster_long_context.json --policy least_queue
python scripts/run_simulation.py --config configs/multi_cluster_long_context.json --policy multi_objective
python scripts/run_simulation.py --config configs/failure_congestion.json --policy contextual_bandit
python scripts/run_benchmarks.py --config configs/multi_cluster_long_context.json
```

## Talking Points

- Round robin ignores the system.
- Least queue ignores cache and topology.
- Cache-only policies can accidentally increase fabric pressure.
- Multi-objective routing is the first policy that reasons across latency, cache, topology, and cost at once.
- Contextual bandit shows how online adaptation can respond to degraded conditions without pretending full RL is already production-ready.

## Recruiter Framing

Say this plainly:

I built the control plane logic that decides where inference requests should run across heterogeneous accelerator pools, using topology locality, KV-cache reuse, queueing, congestion, fairness, and SLA pressure together.

That framing lands much better than “I wrote a scheduler.”

