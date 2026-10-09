# Portfolio and interview notes

A defensible project bullet after the recorded acceptance run:

> Built a local Slurm lab with one controller and two worker containers, automated node configuration with Ansible, and validated deterministic job arrays against a serial reference; added Prometheus/Grafana monitoring and tested worker drain/resume and outage recovery.

Describe the system as a local learning lab. Do not claim production HPC administration, cloud infrastructure, NFS, physical-node scaling, speedup, or automatic task recovery from this project.

## Decisions to explain

- **Containers first:** quick, repeatable Linux processes on Windows; shared kernel and host mean this cannot establish physical cluster performance.
- **One result file per shard:** avoids concurrent writers corrupting an aggregate file. The collector checks completeness and provenance before aggregation.
- **Stable per-shard random seeds:** scheduling order does not alter results. Shard count is part of the experiment definition.
- **Shared Docker storage:** permits scheduler-mediated workers to exchange artifacts without implementing network storage. NFS requires a separate VM/storage milestone.
- **Docker limits rather than job cgroups:** outer quotas constrain the lab's host usage, while Slurm resource requests only govern scheduling in this configuration.
- **FIFO priority:** simple local scheduling without an association/accounting database. Fair-share scheduling and historical accounting require additional infrastructure.
- **Separate readiness signals:** exporter scrape health, daemon liveness, scheduler node state and successful job execution are different checks.
- **Recovery scope:** a restarted worker can register and accept work again. An interrupted research task is not checkpointed or automatically reconstructed.

To demonstrate it live: start the lab, submit a job, show the checksum and hostnames, open the dashboard, drain a worker and explain the pending reason. Run the full acceptance script separately when the lab is otherwise idle.

Next skills to practice are reading squeue reasons and node logs, explaining the cgroup tradeoff, and adding a genuine VM/NFS milestone with separate evidence.
