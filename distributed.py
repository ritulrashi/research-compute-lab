"""Slurm array execution and strict collection for the deterministic workload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import socket
import subprocess
import time
import uuid
from workload import execute, sample_shard

def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)

def config(samples, shards, seed):
    if type(samples) is not int or type(shards) is not int or samples < shards or shards < 1:
        raise ValueError("require samples >= shards >= 1")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    return {"samples": samples, "shards": shards, "seed": seed}

def source_hash():
    return hashlib.sha256(Path(__file__).with_name("workload.py").read_bytes()).hexdigest()

def shard(directory, index):
    directory = Path(directory)
    manifest = json.loads((directory / "request.json").read_text())
    c = config(**manifest["config"])
    if not 0 <= index < c["shards"]:
        raise ValueError("shard index out of range")
    if manifest["source_sha256"] != source_hash():
        raise ValueError("workload source changed")
    base, extra = divmod(c["samples"], c["shards"])
    start = time.monotonic()
    result = sample_shard((index, base + (index < extra), c["seed"]))
    write_json(directory / f"shard-{index}.json", {
        "run_id": manifest["run_id"], "config": c, "source_sha256": source_hash(),
        "result": result, "host": socket.gethostname(), "python": platform.python_version(),
        "job_id": os.environ.get("SLURM_JOB_ID"), "elapsed_seconds": time.monotonic() - start})

def collect(directory):
    directory = Path(directory)
    request = json.loads((directory / "request.json").read_text())
    c = config(**request["config"])
    files = list(directory.glob("shard-*.json"))
    if len(files) != c["shards"]:
        raise ValueError("missing or extra shard files")
    results, hosts, seen = [], set(), set()
    base, extra = divmod(c["samples"], c["shards"])
    for path in files:
        value = json.loads(path.read_text())
        if any(value[key] != request[key] for key in ("run_id", "config", "source_sha256")):
            raise ValueError("inconsistent shard provenance")
        r = value["result"]
        i = r["shard_id"]
        if type(i) is not int or i in seen or not 0 <= i < c["shards"]:
            raise ValueError("duplicate or invalid shard ID")
        n, hits = r["samples"], r["inside_circle"]
        if type(n) is not int or n != base + (i < extra) or type(hits) is not int or not 0 <= hits <= n:
            raise ValueError("invalid shard accounting")
        seen.add(i)
        results.append(r)
        hosts.add(value["host"])
    results.sort(key=lambda r: r["shard_id"])
    result = {**c, "results": results,
              "pi_estimate": 4 * sum(r["inside_circle"] for r in results) / c["samples"]}
    checksum = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    output = {"schema_version": 1, "result": result, "result_sha256": checksum,
              "execution": {"hosts": sorted(hosts), "source_sha256": request["source_sha256"],
                            "run_id": request["run_id"]}}
    write_json(directory / "result.json", output)
    return output

def submit(samples, shards, seed):
    c = config(samples, shards, seed)
    run_id = uuid.uuid4().hex
    directory = Path("/shared/runs") / run_id
    directory.mkdir()
    write_json(directory / "request.json", {"run_id": run_id, "config": c, "source_sha256": source_hash()})
    command = f"python3 /opt/lab/distributed.py shard {shlex.quote(str(directory))}"
    start = time.monotonic()
    job = subprocess.check_output(["sbatch", "--parsable", "--wait", f"--array=0-{shards-1}",
        "--cpus-per-task=1", "--mem=64M", "--time=00:02:00",
        f"--output={directory}/%A_%a.log", "--wrap", command], text=True).strip()
    output = collect(directory)
    reference = execute(samples, shards, seed, 1)
    if output["result_sha256"] != reference["result_sha256"]:
        raise ValueError("distributed result differs from serial reference")
    output["execution"].update(job_id=job, elapsed_seconds=time.monotonic()-start,
                               serial_reference_matches=True)
    write_json(directory / "result.json", output)
    print(json.dumps({"directory": str(directory), **output}))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--samples", type=int, default=1000000)
    s.add_argument("--shards", type=int, default=8)
    s.add_argument("--seed", type=int, default=42)
    for command in ("shard", "collect"):
        sub.add_parser(command).add_argument("directory", type=Path)
    a = p.parse_args()
    if a.command == "submit":
        submit(a.samples, a.shards, a.seed)
    elif a.command == "shard":
        shard(a.directory, int(os.environ["SLURM_ARRAY_TASK_ID"]))
    else:
        print(json.dumps(collect(a.directory)))
if __name__ == "__main__":
    main()
