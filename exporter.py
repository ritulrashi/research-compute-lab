"""Small read-only Prometheus exporter; no Docker socket or privileged access."""
import os
from pathlib import Path
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def collect():
    lines = []
    def metric(name, value, labels=""):
        lines.append(f"{name}{labels} {value}")
    # cgroup v2 values describe this container, unlike shared /proc CPU counters.
    try:
        values = dict(row.split() for row in Path("/sys/fs/cgroup/cpu.stat").read_text().splitlines())
        metric("lab_container_cpu_seconds_total", int(values["usage_usec"]) / 1e6)
        metric("lab_container_memory_bytes", int(Path("/sys/fs/cgroup/memory.current").read_text()))
        metric("lab_cgroup_metrics_available", 1)
    except (OSError, ValueError, KeyError):
        metric("lab_cgroup_metrics_available", 0)
    if os.environ.get("LAB_ROLE") == "controller":
        try:
            nodes = subprocess.check_output(["sinfo", "-h", "-N", "-o", "%N|%T"], text=True, timeout=3)
            for row in nodes.splitlines():
                node, state = row.split("|")
                ready = state.lower() in ("idle", "allocated", "mixed")
                metric("lab_slurm_node_available", int(ready), '{node="' + node + '"}')
            jobs = subprocess.check_output(["squeue", "-h", "-o", "%T"], text=True, timeout=3)
            states = jobs.splitlines()
            for state in ("RUNNING", "PENDING", "COMPLETING"):
                metric("lab_slurm_jobs", states.count(state), '{state="' + state + '"}')
            metric("lab_slurm_query_success", 1)
        except (subprocess.SubprocessError, OSError, ValueError):
            metric("lab_slurm_query_success", 0)
    return "\n".join(lines) + "\n"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        data = collect().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9108), Handler).serve_forever()
