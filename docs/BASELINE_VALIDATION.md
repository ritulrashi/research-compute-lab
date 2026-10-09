# Baseline validation

Validated in Ubuntu WSL on 2026-10-08.

- Five unittest tests passed: worker-count invariance, full shard accounting, repeatability, invalid inputs and CLI manifest generation.
- One million samples, eight shards, seed 42; one-worker and two-worker results matched.
- Result SHA-256: `f3d55a77ed011477c4ffe1209b901321a1f655d75419b1b8b6d6737021bb728e`
- Single-worker elapsed: 0.1334 seconds.
- Two-worker elapsed: 0.1615 seconds.
- Python: 3.12.3.
- These are single-run functional checks, not a statistically supported speedup benchmark.
- No Slurm, cluster, Terraform, Ansible or cloud deployment is claimed.
