#!/usr/bin/env bash
set -euo pipefail
for attempt in $(seq 1 30); do
  if munge -n >/dev/null 2>&1; then break; fi
  sleep 1
done
munge -n >/dev/null
if [ "$LAB_ROLE" = controller ]; then
  exec /usr/sbin/slurmctld -D
else
  exec /usr/sbin/slurmd -D -N "$(hostname)"
fi
