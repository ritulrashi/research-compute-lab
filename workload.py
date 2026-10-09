"""Deterministic, shardable Monte Carlo CPU workload. Python standard library only."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import random
import time


def sample_shard(task):
    shard_id, samples, seed = task
    derived = int.from_bytes(hashlib.sha256(f"{seed}:{shard_id}".encode()).digest(), "big")
    rng = random.Random(derived)
    hits = 0
    for _ in range(samples):
        x, y = rng.random(), rng.random()
        hits += x*x + y*y <= 1.0
    return {"shard_id": shard_id, "samples": samples, "inside_circle": hits}


def execute(samples=100000, shards=8, seed=42, workers=1):
    if any(type(v) is not int or v <= 0 for v in (samples, shards, workers)):
        raise ValueError("samples, shards, and workers must be positive integers")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if shards > samples:
        raise ValueError("shards cannot exceed samples")
    base, remainder = divmod(samples, shards)
    tasks = [(i, base + (i < remainder), seed) for i in range(shards)]
    start = time.perf_counter()
    if workers == 1:
        results = list(map(sample_shard, tasks))
    else:
        with ProcessPoolExecutor(max_workers=min(workers, shards),
                                 mp_context=multiprocessing.get_context("spawn")) as pool:
            results = list(pool.map(sample_shard, tasks))
    elapsed = time.perf_counter() - start
    result = {"samples": samples, "shards": shards, "seed": seed, "results": results,
              "pi_estimate": 4 * sum(x["inside_circle"] for x in results) / samples}
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    return {"schema_version": 1, "result": result,
            "result_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "execution": {"workers_requested": workers, "workers_used": min(workers, shards),
                          "elapsed_seconds": elapsed, "samples_per_second": samples / elapsed,
                          "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                          "python": platform.python_version(), "platform": platform.platform(),
                          "logical_cpus": os.cpu_count(),
                          "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=100000)
    parser.add_argument("--shards", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("runs/latest.json"))
    args = parser.parse_args()
    try:
        manifest = execute(args.samples, args.shards, args.seed, args.workers)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "result_sha256": manifest["result_sha256"],
                      "elapsed_seconds": manifest["execution"]["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
