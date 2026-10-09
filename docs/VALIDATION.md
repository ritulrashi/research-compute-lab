# Validation and implementation evidence

Tested on 2026-10-08 using Windows, Docker Desktop's Linux engine and WSL 2. This report describes actual local execution, not physical cluster performance.

## Environment

- Docker Engine 28.1.1; Compose v2.35.1-desktop.1.
- Ubuntu 26.04 base image, resolved during build to sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7.
- Slurm 25.11.2 from Ubuntu packages; Python 3.14.4; Ansible core 2.20.1.
- Prometheus v3.2.1 image digest: sha256:6927e0919a144aa7616fd0137d4816816d42f6b816de3af269ab065250859a62.
- Grafana 11.6.0 image digest: sha256:62d2b9d20a19714ebfe48d1bb405086081bc602aa053e28cf6d73c7537640dfb.
- Three compute containers share one host/kernel. Two logical scheduled CPUs and 512 MiB of requested memory per worker; outer Docker quotas are two CPU equivalents and 1 GiB per compute container.
- The Ubuntu base is pinned by digest. Monitoring images use version tags, and apt repositories may change on a later rebuild; this is not a fully frozen package lock.

## Checks

Eleven unit tests passed on Windows Python 3.14 and inside the Linux lab image. Final Linux test run: 1.523 seconds. Tests cover worker-count invariance, reproducibility, shard accounting, invalid inputs, CLI output, serial/collected equivalence, and missing/duplicate/inconsistent/invalid shard rejection.

The end-to-end script exercises:

1. A two-node srun allocation that prints worker1 and worker2.
2. An unchanged second Ansible run reporting changed=0 on all three nodes.
3. One million samples across eight Slurm array tasks, compared with a serial reference.
4. Three live Prometheus exporters, two available scheduler workers and a provisioned Grafana dashboard with five panels.
5. Draining worker1, observing a job pinned to it remain PENDING, then resuming it and observing COMPLETED.
6. Stopping worker2, observing LabExporterDown in firing state, restarting the worker and observing successful recovery.

See the committed acceptance evidence for final outcomes and raw commands. Evidence includes scheduler wall time, which includes dispatch/polling overhead and serial verification; it must not be interpreted as pure CPU throughput or a scaling benchmark.

## Failures encountered and corrected

- Docker Desktop initially failed on a stale inference socket in its run directory. The stale runtime directory was preserved and a fresh runtime directory created. Docker's images and persistent volumes were not reset.
- Ubuntu's image already had UID 1000. The lab's researcher user now uses UID 2000 consistently across nodes.
- Slurmd initially attempted cgroup v2/systemd setup inside an unprivileged container and failed. Current upstream documentation's disabled plugin setting was also unsupported by the installed 23.11 build. A legacy cgroup/v1 setting allowed the initial prototype to run. The final Ubuntu 26.04/Slurm 25.11 build supports CgroupPlugin=disabled directly. Docker retains outer container limits.
- The Slurm 23.11 main scheduler reported InvalidAccount without an accounting database, although backfill completed tasks. FIFO priority alone did not remove that warning, so the final image upgrades Slurm to 25.11.2 and uses a fresh scheduler-state volume. Earlier state and evidence were preserved. The final lab explicitly uses priority/basic (FIFO).
- The earlier image logged optional PMIx library initialization errors. The final workers start cleanly for this non-MPI workload. Actual two-worker job execution remains the acceptance condition.

## What this proves

Reproducible scheduler-mediated task execution, strict result collection, repeatable configuration, shared-volume artifact exchange, observable node operations and recovery in an isolated local lab.

It does not prove physical network throughput, NFS operation, per-job cgroup resource enforcement, automatic recovery of interrupted computation, cloud deployment, MPI performance or production reliability.

## Final acceptance result

Status: **passed**. UTC start: 2026-10-09T00:08:27Z.

One million samples / eight shards / seed 42: `f3d55a77ed011477c4ffe1209b901321a1f655d75419b1b8b6d6737021bb728e`. The array executed on worker1, worker2. Source hash matches the published workload bytes.

[Raw acceptance evidence](evidence/acceptance.json) includes commands, scheduler results and the firing worker-outage alert.
