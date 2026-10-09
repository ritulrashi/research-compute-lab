# Local lab operations

Run commands from the repository root. Commands affect the Compose project named research-compute-lab.

## Start, inspect and stop

```bash
python lab.py up
python lab.py status
python lab.py logs
python lab.py down
```

Startup runs Ansible before starting MUNGE, Slurm and the metrics exporter through Supervisor. Worker health requires slurmd running; confirm registration through sinfo as well. A daemon being alive alone does not prove jobs can execute.

## Queue and resource inspection

```bash
docker compose exec -T controller scontrol ping
docker compose exec -T controller sinfo -N -l
docker compose exec -T controller squeue -o "%.18i %.9T %.20R"
docker compose exec -T controller scontrol show nodes
docker compose exec -T controller srun --nodes=2 --ntasks=2 --mem=64M hostname
docker compose exec -T controller cat /var/lib/slurm/job-completions.log
```

For a specific job: `docker compose exec -T controller scontrol show job JOB_ID`.
The controller keeps completed in-memory jobs briefly; consult the file completion log after eviction. This lab does not provide sacct history through a database.

## Drain and resume

```bash
docker compose exec -T controller scontrol update NodeName=worker1 State=DRAIN Reason=maintenance
docker compose exec -T controller sinfo -N -l
docker compose exec -T controller scontrol update NodeName=worker1 State=RESUME
```

Draining prevents new jobs on the node. Existing jobs may finish. A job requiring only that node remains pending until it returns.

## Monitoring and outages

Grafana: http://localhost:13000/d/research-lab
Prometheus alerts: http://localhost:19090/alerts

- LabExporterDown: an exporter cannot be scraped for 10 seconds.
- SlurmWorkerUnavailable: the controller reports a worker unavailable for 10 seconds.
- SlurmControllerQueryFailed: the exporter cannot query scheduler state for 10 seconds.

These alerts are related but distinct. An exporter outage does not by itself prove the scheduler has marked a node down.

```bash
docker compose stop worker2
docker compose start worker2
docker compose logs --tail 100 worker2
docker compose exec -T worker2 supervisorctl status
```

ReturnToService allows a recovered node to register again. If the node remains down, inspect its reason and logs before using State=RESUME. An interrupted batch job may fail; submit a fresh workload after recovering the node. No application checkpoint recovery is implemented.

## Configuration

```bash
python lab.py configure
```

An unchanged second configuration run should show changed=0 on every node. To apply edited configuration, rebuild/recreate with `python lab.py up`; merely running Ansible does not automatically restart an existing Slurm daemon.

## Artifacts and storage

```bash
docker compose exec -T controller ls /shared/runs
docker compose cp controller:/shared/runs/RUN_ID ./runs/RUN_ID
```

All three nodes mount the same named storage volume. A separate controller-state volume holds scheduler state. `docker compose down` preserves these volumes. Do not delete volumes when preserving run evidence.

## Troubleshooting

- Docker Desktop stopped: start it and verify `docker info`.
- Initial setup still running: inspect `docker compose logs`; Ansible may take a minute on a busy host.
- MUNGE authentication failures: confirm all three containers use the same generated key, matching users, and clock.
- slurmd cgroup/systemd failures: confirm `/etc/slurm/cgroup.conf` contains `CgroupPlugin=disabled` in this container-only lab.
- Node CPU topology warnings: containers see host topology while this lab schedules a smaller logical resource count using config_overrides.
- Missing shards: inspect array logs and job state; the collector intentionally refuses partial results.
- Controller startup on a fresh state volume can log missing prior state files; verify that the controller subsequently runs and accepts jobs.
