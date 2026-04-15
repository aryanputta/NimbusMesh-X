# Failure Analysis Guide

NimbusMesh-X is meant to surface failure modes rather than hide them. The current repository includes failure-ready configs and explicit accounting for several important cases.

## Cache Metadata Goes Stale

Risk:

- router overestimates reuse
- cache-aware routing increases latency instead of reducing it

Current behavior:

- cache entries expire with TTL
- entries are only considered valid after completion time
- stale entries are evicted before scoring

Next hardening step:

- track confidence and downgrade reuse scores when hit history decays

## Cheapest Pool Overloads

Risk:

- best-effort traffic floods economy accelerators
- queue delay explodes and spills into premium tiers too late

Current behavior:

- queue limit and memory headroom can mark a pool unavailable
- multi-objective routing includes congestion and latency penalties
- contextual bandit can shift away from persistently bad placements

## Cache-Aware Routing Causes Fabric Hotspots

Risk:

- local cache reuse wins the score
- interconnect or ingress congestion turns that into a bad trade

Current behavior:

- cache-aware policy exists as an explicit baseline
- multi-objective policy balances cache benefit against network and congestion cost
- failure-and-congestion config stresses this case directly

## Learning Policy Overfits One Workload Mix

Risk:

- online learner becomes brittle
- tail latency improves in one trace and regresses badly in another

Current behavior:

- contextual bandit is intentionally lightweight and benchmarked against static heuristics
- the repo keeps heuristic baselines first-class so the learner always has a reference set

## Long-Context Jobs Starve Short Requests

Risk:

- queue-only policies become hostage to a few very large prompts

Current behavior:

- realtime traffic can prefer premium pools
- fairness penalty can dampen dominant tenants
- long-context workloads explicitly benefit from stronger topology tiers

Next hardening step:

- split prefill and decode stages into separate schedulable resources

## Topology Locality Conflicts With Fairness

Risk:

- the best-connected pool serves the same tenant too often

Current behavior:

- fairness penalty rises when completed share exceeds expected tenant share
- multi-objective routing can give up a little locality to preserve fairness

## Backend Parallel Strategy Changes

Risk:

- TensorRT-LLM or vLLM tuning changes effective throughput and queue behavior

Current behavior:

- backend adapters own latency estimation
- pool specs define throughput and memory assumptions per backend

This keeps the control-plane logic decoupled from a single serving runtime’s internals.

